"""Review extracted observations against cached SEC evidence.

The review layer deliberately separates three states:

* ``extracted_pending_review``: present in an extractor CSV;
* ``source_reconciled_pending_approval``: the CSV row matches its cached JSON
  fact, but a human has not approved it for comparison;
* ``approved``: explicitly approved by a reviewer after source and duplicate
  review.

No state is inferred from a successful download. Missing attachments and
missing concepts remain missing.
"""

from hashlib import sha256
import json
from pathlib import Path

import pandas as pd

from .ingestion import FIELDS, validate_observations

REVIEW_FIELDS = FIELDS + [
    "review_status",
    "review_reason",
    "evidence_file",
]
APPROVED_FIELDS = REVIEW_FIELDS


def _as_rows(frame):
    """Convert a CSV frame while preserving empty period starts as strings."""
    result = []
    for row in frame.to_dict(orient="records"):
        for key in ("period_start", "source_url", "source_document_url"):
            if pd.isna(row.get(key)):
                row[key] = ""
        if "value" in row:
            row["value"] = float(row["value"])
        if "fiscal_year" in row:
            row["fiscal_year"] = int(row["fiscal_year"])
        result.append(row)
    return result


def _find_fact(payload, row):
    """Return the exact SEC fact represented by a normalized observation."""
    concept = str(row["concept"])
    if ":" not in concept:
        return None
    namespace, tag = concept.split(":", 1)
    units = payload.get("facts", {}).get(namespace, {}).get(tag, {}).get("units", {})
    expected = row["value"] * 1_000_000
    for facts in units.values():
        for fact in facts:
            if (
                fact.get("accn") == row["accession"]
                and fact.get("end") == row["period_end"]
                and fact.get("start", "") == row["period_start"]
                and abs(float(fact.get("val")) - expected) < 0.0001
            ):
                return fact
    return None


def reconcile_observation(row, evidence_dir):
    """Reconcile one CSV row to its hashed SEC JSON evidence."""
    evidence_file = Path(evidence_dir) / f"{row['evidence_sha256']}.json"
    if not evidence_file.exists():
        return "unreconciled", "Cached evidence JSON is unavailable", evidence_file.name
    raw = evidence_file.read_bytes()
    if sha256(raw).hexdigest() != row["evidence_sha256"]:
        return "unreconciled", "Cached evidence hash does not match row", evidence_file.name
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return "unreconciled", "Cached evidence is not valid JSON", evidence_file.name
    expected_cik = str(payload.get("cik", "")).zfill(10)
    if f"CIK{expected_cik}.json" not in row["source_url"]:
        return "unreconciled", "Evidence issuer does not match source URL", evidence_file.name
    if _find_fact(payload, row) is None:
        return "unreconciled", "No exact concept, accession, period and value match", evidence_file.name
    return "source_reconciled_pending_approval", "Exact SEC fact and evidence hash match", evidence_file.name


def review_extracted_directory(directory):
    """Review all extractor CSVs without dropping duplicate filings."""
    directory = Path(directory)
    evidence_dir = directory / "evidence"
    rows = []
    input_files = sorted(p for p in directory.glob("*.csv") if p.name not in {"review_observations.csv", "approved_financial_observations.csv"})
    for path in input_files:
        frame = pd.read_csv(path)
        if frame.empty:
            continue
        candidate_rows = _as_rows(frame)
        validate_observations(candidate_rows)
        for row in candidate_rows:
            status, reason, evidence_file = reconcile_observation(row, evidence_dir)
            row.update(review_status=status, review_reason=reason, evidence_file=evidence_file)
            rows.append(row)
    if not rows:
        return pd.DataFrame(columns=REVIEW_FIELDS)
    result = pd.DataFrame(rows, columns=REVIEW_FIELDS)
    period_key = ["company", "metric", "period_start", "period_end", "period_type", "currency"]
    counts = result.groupby(period_key, dropna=False)["accession"].transform("nunique")
    for key, group in result.groupby(period_key, dropna=False, sort=False):
        if len(group) <= 1:
            continue
        values = group["value"].nunique()
        indices = group.index
        if values == 1:
            result.loc[indices, "review_status"] = "repeated_historical_pending_approval"
            result.loc[indices, "review_reason"] = "Same period/value appears in multiple filings; amendment/restatement review required"
        else:
            result.loc[indices, "review_status"] = "duplicate_period_unresolved"
            result.loc[indices, "review_reason"] = "Multiple filing values exist for one period; do not choose latest automatically"
    return result


def approved_observations(reviewed):
    """Return only explicit, reconciled approvals with no duplicate ambiguity."""
    if reviewed is None or reviewed.empty:
        return pd.DataFrame(columns=APPROVED_FIELDS)
    frame = reviewed.copy()
    allowed = frame["review_status"].eq("approved")
    allowed &= frame["verification_status"].eq("reviewed")
    allowed &= frame["review_reason"].str.contains("approved", case=False, na=False)
    allowed &= frame["review_status"].ne("duplicate_period_unresolved")
    candidate = frame.loc[allowed].copy()
    period_key = ["company", "metric", "period_start", "period_end", "period_type", "currency"]
    ambiguous = candidate.duplicated(period_key, keep=False)
    # Keep every unresolved candidate in review artifacts; approve none of an
    # ambiguous period so a restatement is never discarded by this function.
    candidate = candidate.loc[~ambiguous]
    return candidate[APPROVED_FIELDS].reset_index(drop=True)


def freshness_status(status_file):
    """Read refresh metadata for the dashboard without claiming data freshness."""
    path = Path(status_file)
    if not path.exists():
        return {"status": "unavailable", "message": "No extraction status file found"}
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {"status": "unavailable", "message": "Extraction status is unreadable"}
    companies = payload.get("companies", {})
    successful = [name for name, item in companies.items() if item.get("status") == "extracted_pending_review"]
    return {
        "status": "available" if successful else "unavailable",
        "attempted_at": payload.get("attempted_at"),
        "successful_companies": successful,
        "message": "Extraction completed; values still require review" if successful else "No successful extraction is recorded",
    }

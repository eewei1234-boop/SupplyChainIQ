"""Review extracted CSVs against cached evidence and write review artifacts.

The command never approves a row automatically. A reviewer may edit a copy of
``review_observations.csv`` after reconciling source documents, set
``review_status=approved`` and include ``approved after source reconciliation``
in ``review_reason``. The command never overwrites the separately maintained
approved dataset.
"""

from pathlib import Path

import pandas as pd

from supplychainiq.review import APPROVED_FIELDS, review_extracted_directory


def run_review(root):
    root = Path(root)
    directory = root / "data" / "ingestion"
    review = review_extracted_directory(directory)
    review.to_csv(directory / "review_observations.csv", index=False)
    approved_path = root / "data" / "approved_financial_observations.csv"
    # Approved data is a human-owned artifact. Never regenerate or overwrite it
    # during extraction/review; this protects manual approvals and restatement
    # decisions. Create only the empty schema when it does not exist yet.
    if not approved_path.exists():
        pd.DataFrame(columns=APPROVED_FIELDS).to_csv(approved_path, index=False)
    try:
        approved_count = int(pd.read_csv(approved_path).shape[0])
    except (OSError, pd.errors.EmptyDataError):
        approved_count = 0
    status = {
        "input_archive_present": any(
            path.name not in {"review_observations.csv", "approved_financial_observations.csv"}
            for path in directory.glob("*.csv")
        ),
        "observation_count": int(len(review)),
        "source_reconciled_pending_approval": int((review.review_status == "source_reconciled_pending_approval").sum()) if not review.empty else 0,
        "exact_source_matches": int((review.reconciliation_status == "source_reconciled_pending_approval").sum()) if not review.empty else 0,
        "unreconciled": int((review.reconciliation_status == "unreconciled").sum()) if not review.empty else 0,
        "repeated_historical_pending_approval": int((review.review_status == "repeated_historical_pending_approval").sum()) if not review.empty else 0,
        "duplicate_period_unresolved": int((review.review_status == "duplicate_period_unresolved").sum()) if not review.empty else 0,
        "approved_count": approved_count,
        "note": (
            "No observations are approved automatically; review duplicates and filing context before approval."
            if len(review)
            else "No observations are approved automatically. Missing ZIP/CSV evidence remains empty."
        ),
    }
    pd.Series(status).to_json(directory / "review_summary.json", indent=2)
    return status


def main():
    status = run_review(Path(__file__).resolve().parents[1])
    print(pd.Series(status).to_string())


if __name__ == "__main__":
    main()

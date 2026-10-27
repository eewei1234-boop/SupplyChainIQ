import json
from hashlib import sha256

import pandas as pd
import pytest

from supplychainiq.ingestion import FIELDS, extract_sec
from supplychainiq.data_loading import load_approved_data
from supplychainiq.review import approved_observations, reconcile_observation, review_extracted_directory


def sec_fixture():
    facts = {}
    for tag, value in [("Revenues", 100_000_000), ("InventoryNet", 20_000_000), ("GrossProfit", 40_000_000), ("CostOfRevenue", 60_000_000), ("OperatingIncomeLoss", -1_000_000)]:
        fact = {"end": "2023-12-31", "val": value, "accn": "0001097864-24-000001", "filed": "2024-02-01", "form": "10-K"}
        if tag != "InventoryNet":
            fact["start"] = "2023-01-01"
        facts[tag] = {"units": {"USD": [fact]}}
    return {"cik": 1097864, "facts": {"us-gaap": facts}}


def write_extract(tmp_path, payload=None):
    payload = payload or sec_fixture()
    raw = json.dumps(payload).encode()
    digest = sha256(raw).hexdigest()
    evidence = tmp_path / "evidence"
    evidence.mkdir(parents=True)
    (evidence / f"{digest}.json").write_bytes(raw)
    rows = extract_sec(payload, "onsemi", digest=digest, retrieved_at="2026-10-27T00:00:00+00:00")
    pd.DataFrame(rows, columns=FIELDS).to_csv(tmp_path / "onsemi.csv", index=False)
    return rows, digest


def test_exact_source_reconciliation_and_pending_approval(tmp_path):
    rows, _ = write_extract(tmp_path)
    reviewed = review_extracted_directory(tmp_path)
    assert len(reviewed) == len(rows)
    assert set(reviewed.review_status) == {"source_reconciled_pending_approval"}
    assert approved_observations(reviewed).empty
    assert reconcile_observation(rows[0], tmp_path / "evidence")[0] == "source_reconciled_pending_approval"


def test_missing_or_tampered_evidence_is_not_reconciled(tmp_path):
    rows, digest = write_extract(tmp_path)
    (tmp_path / "evidence" / f"{digest}.json").write_text("tampered")
    reviewed = review_extracted_directory(tmp_path)
    assert set(reviewed.review_status) == {"unreconciled"}
    assert "hash" in reviewed.iloc[0].review_reason


def test_repeated_value_and_conflicting_periods_are_retained(tmp_path):
    payload = sec_fixture()
    duplicate = json.loads(json.dumps(payload))
    for facts in duplicate["facts"]["us-gaap"].values():
        for unit_facts in facts["units"].values():
            for fact in unit_facts:
                fact["accn"] = "0001097864-24-000002"
    for tag, facts in duplicate["facts"]["us-gaap"].items():
        for unit, values in facts["units"].items():
            payload["facts"]["us-gaap"][tag]["units"][unit].extend(values)
    rows, digest = write_extract(tmp_path, payload)
    reviewed = review_extracted_directory(tmp_path)
    assert len(reviewed) == len(rows)
    assert "repeated_historical_pending_approval" in set(reviewed.review_status)

    changed = json.loads(json.dumps(sec_fixture()))
    changed["facts"]["us-gaap"]["Revenues"]["units"]["USD"][0]["accn"] = "0001097864-24-000003"
    changed["facts"]["us-gaap"]["Revenues"]["units"]["USD"][0]["val"] = 101_000_000
    raw = json.dumps(changed).encode()
    new_digest = sha256(raw).hexdigest()
    (tmp_path / "evidence" / f"{new_digest}.json").write_bytes(raw)
    changed_rows = extract_sec(changed, "onsemi", digest=new_digest, retrieved_at="2026-10-27T00:00:00+00:00")
    changed_revenue = [row for row in changed_rows if row["metric"] == "revenue"]
    pd.DataFrame(rows + changed_revenue, columns=FIELDS).to_csv(tmp_path / "onsemi.csv", index=False)
    reviewed = review_extracted_directory(tmp_path)
    assert "duplicate_period_unresolved" in set(reviewed.review_status)
    assert len(reviewed) > len(rows)


def test_only_explicit_reconciled_approval_enters_approved_dataset(tmp_path):
    rows, _ = write_extract(tmp_path)
    reviewed = review_extracted_directory(tmp_path)
    reviewed.loc[0, "review_status"] = "approved"
    reviewed.loc[0, "verification_status"] = "reviewed"
    reviewed.loc[0, "review_reason"] = "approved after source reconciliation"
    result = approved_observations(reviewed)
    assert len(result) == 1
    reviewed.loc[0, "verification_status"] = "extracted_pending_review"
    assert approved_observations(reviewed).empty


def test_approval_does_not_silently_choose_between_duplicate_periods(tmp_path):
    rows, _ = write_extract(tmp_path)
    reviewed = review_extracted_directory(tmp_path)
    reviewed["review_status"] = "approved"
    reviewed["verification_status"] = "reviewed"
    reviewed["review_reason"] = "approved after source reconciliation"
    duplicate = reviewed.iloc[[0]].copy()
    duplicate["accession"] = "0001097864-24-000099"
    candidates = pd.concat([reviewed.iloc[[0]], duplicate], ignore_index=True)
    assert approved_observations(candidates).empty


def test_dashboard_reads_approved_file_from_data_directory(tmp_path, monkeypatch):
    rows, _ = write_extract(tmp_path / "ingestion")
    approved = pd.DataFrame(rows)
    approved["verification_status"] = "reviewed"
    approved["reconciliation_status"] = "source_reconciled_pending_approval"
    approved["reconciliation_reason"] = "Exact SEC fact and evidence hash match"
    approved["review_status"] = "approved"
    approved["review_reason"] = "approved after source reconciliation"
    approved["evidence_file"] = approved["evidence_sha256"] + ".json"
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    approved.to_csv(data_dir / "approved_financial_observations.csv", index=False)
    monkeypatch.setattr("supplychainiq.data_loading.DATA_DIR", data_dir)
    result = load_approved_data()
    assert len(result) == 1
    assert result.iloc[0].company == "onsemi"
    assert result.iloc[0].data_type == "public"


def test_review_run_never_overwrites_existing_approved_records(tmp_path):
    from scripts.review_financial_data import run_review

    write_extract(tmp_path / "data" / "ingestion")
    approved_path = tmp_path / "data" / "approved_financial_observations.csv"
    approved_path.parent.mkdir(exist_ok=True)
    original = "manually approved record,keep this exact file\n"
    approved_path.write_text(original)
    status = run_review(tmp_path)
    assert status["observation_count"] == 5
    assert approved_path.read_text() == original

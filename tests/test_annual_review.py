import pandas as pd
import pytest

from supplychainiq.annual_review import build_annual_review
from supplychainiq.analysis import analyze


def observations():
    rows = []
    for year, revenue, cost, operating, inventory in [(2024, 100, 60, 10, 20), (2025, 120, 72, 12, 18)]:
        accession = f"0000000000-{year}-000001"
        common = dict(
            company="onsemi", fiscal_year=year, currency="USD", unit="millions",
            publication_date=f"{year + 1}-02-01", source_url="https://data.sec.gov/api/xbrl/companyfacts/CIK0001097864.json",
            source_document_url=f"https://www.sec.gov/Archives/edgar/data/1097864/{year}/", accession=accession,
            retrieved_at="2026-10-27T00:00:00+00:00", evidence_sha256="a" * 64,
            verification_status="extracted_pending_review", reconciliation_status="source_reconciled_pending_approval",
            reconciliation_reason="Exact SEC fact and evidence hash match", review_status="source_reconciled_pending_approval",
            review_reason="Exact SEC fact and evidence hash match", evidence_file="a" * 64 + ".json",
        )
        for metric, value in [("revenue", revenue), ("cost_of_revenue", cost), ("operating_income", operating)]:
            rows.append(dict(common, metric=metric, period_start=f"{year}-01-01", period_end=f"{year}-12-31", period_type="annual", value=value))
        rows.append(dict(common, metric="inventory", period_start="", period_end=f"{year}-12-31", period_type="instant", value=inventory))
        # An earlier instant balance must not be mistaken for year-end inventory.
        rows.append(dict(common, metric="inventory", period_start="", period_end=f"{year}-09-30", period_type="instant", value=inventory + 2))
    return pd.DataFrame(rows)


def test_annual_review_keeps_year_end_inventory_and_all_source_contexts():
    review = build_annual_review(observations())
    assert len(review) == 8
    assert set(review.approval_status) == {"pending_human_filing_review"}
    assert not review.independently_verified.any()
    assert review.json_reconciled.all()
    inventory = review[review.metric == "inventory"]
    assert set(inventory.period_end) == {"2024-12-31", "2025-12-31"}
    assert inventory.iloc[0].value in {18.0, 20.0}
    assert inventory.iloc[0].candidate_accessions == "0000000000-2024-000001"


def test_annual_review_marks_conflicting_values_without_choosing_one():
    frame = observations()
    conflict = frame[(frame.fiscal_year == 2025) & (frame.metric == "revenue")].iloc[[0]].copy()
    conflict["value"] = 121
    conflict["accession"] = "0000000000-2025-000099"
    result = build_annual_review(pd.concat([frame, conflict], ignore_index=True))
    row = result[(result.fiscal_year == 2025) & (result.metric == "revenue")].iloc[0]
    assert pd.isna(row.value)
    assert row.approval_status == "conflicting_values_pending_reconciliation"
    assert "0000000000-2025-000099" in row.candidate_accessions


def test_approved_annual_metrics_calculate_from_native_currency_records():
    frame = observations()
    annual = frame[frame.period_type.isin(["annual", "instant"])].copy()
    # Select the intended year-end inventory observations for this calculation fixture.
    annual = annual[(annual.metric != "inventory") | annual.period_end.str.endswith("12-31")]
    annual["data_type"] = "public"
    annual["period_start"] = annual.period_start.replace("", pd.NA).fillna("")
    # Convert the observation fixture into the Phase 1 annual schema.
    rows = []
    for (year,), group in annual.groupby(["fiscal_year"]):
        values = group.set_index("metric").value
        rows.append({
            "company": "onsemi", "fiscal_year": year, "period_start": f"{year}-01-01", "period_end": f"{year}-12-31",
            "publication_date": f"{year + 1}-02-01", "currency": "USD", "revenue": values.revenue,
            "operating_income": values.operating_income, "inventory": values.inventory, "cost_of_revenue": values.cost_of_revenue,
            "source_url": "https://www.sec.gov/Archives/edgar/data/1097864/", "source_note": "Reviewed fixture source", "data_type": "public",
        })
    result = analyze(pd.DataFrame(rows))
    assert result.iloc[0].gross_margin_pct == 40
    assert result.iloc[1].revenue_growth_pct == pytest.approx(20)
    assert result.iloc[1].inventory_to_revenue_pct == pytest.approx(15)

"""Regression checks for the FY2024/FY2025 audited filing approval proposal."""
from pathlib import Path

import pandas as pd
import pytest

from supplychainiq.data_loading import load_approved_data
from supplychainiq.review import reconcile_observation

ROOT = Path(__file__).resolve().parents[1]
APPROVED = ROOT / "data" / "approved_financial_observations.csv"
EVIDENCE = ROOT / "data" / "ingestion" / "evidence"
ACCESSIONS = {
    "onsemi": "0001097864-26-000006",
    "STMicroelectronics": "0000932787-26-000009",
}
EXPECTED = {
    ("onsemi", 2024): {"revenue": 7082.3, "cost_of_revenue": 3866.2, "operating_income": 1767.7, "inventory": 2242.0},
    ("onsemi", 2025): {"revenue": 5995.4, "cost_of_revenue": 4011.5, "operating_income": 84.2, "inventory": 1989.6},
    ("STMicroelectronics", 2024): {"revenue": 13269.0, "cost_of_revenue": 8049.0, "operating_income": 1676.0, "inventory": 2794.0},
    ("STMicroelectronics", 2025): {"revenue": 11800.0, "cost_of_revenue": 7801.0, "operating_income": 175.0, "inventory": 3136.0},
}


def test_approved_observations_reconcile_to_original_cached_sec_evidence():
    rows = pd.read_csv(APPROVED).fillna("")
    assert len(rows) == 16
    assert set(rows.company) == set(ACCESSIONS)
    assert set(rows.fiscal_year) == {2024, 2025}
    assert set(rows.review_status) == {"approved"}
    assert set(rows.verification_status) == {"reviewed"}
    assert set(rows.reconciliation_status) == {"source_reconciled_pending_approval"}
    assert rows.review_reason.str.contains("approved after source reconciliation").all()
    assert not rows.duplicated(["company", "metric", "period_start", "period_end", "period_type", "currency"]).any()

    for (company, year), expected in EXPECTED.items():
        subset = rows[(rows.company == company) & (rows.fiscal_year == year)]
        assert len(subset) == 4
        assert set(subset.metric) == set(expected)
        assert set(subset.accession) == {ACCESSIONS[company]}
        assert set(subset.period_end) == {f"{year}-12-31"}
        assert set(subset.currency) == {"USD"}
        assert set(subset.unit) == {"millions"}
        for row in subset.to_dict(orient="records"):
            assert row["value"] == pytest.approx(expected[row["metric"]])
            assert row["period_type"] == ("instant" if row["metric"] == "inventory" else "annual")
            status, _, _ = reconcile_observation(row, EVIDENCE)
            assert status == "source_reconciled_pending_approval"


def test_approved_observations_render_as_four_complete_annual_dashboard_rows():
    dashboard = load_approved_data()
    assert len(dashboard) == 4
    assert not (dashboard.data_type == "synthetic").any()
    assert not dashboard.duplicated(["company", "fiscal_year"]).any()
    for (company, year), expected in EXPECTED.items():
        row = dashboard[(dashboard.company == company) & (dashboard.fiscal_year == year)].iloc[0]
        assert row["source_url"].startswith("https://www.sec.gov/Archives/edgar/data/")
        assert row["period_end"] == f"{year}-12-31"
        for metric, value in expected.items():
            assert row[metric] == pytest.approx(value)
        assert 0 <= (row.revenue - row.cost_of_revenue) / row.revenue <= 1
        assert row.inventory / row.cost_of_revenue * 365 > 0

import pandas as pd
import pytest

from supplychainiq.risk import RiskConfig, screen_risk


def frame(values):
    rows = []
    for year, revenue, cost, operating, inventory in values:
        rows.append({
            "company": "onsemi", "fiscal_year": year, "period_start": f"{year}-01-01", "period_end": f"{year}-12-31",
            "publication_date": f"{year + 1}-02-01", "currency": "USD", "revenue": revenue,
            "operating_income": operating, "inventory": inventory, "cost_of_revenue": cost,
            "source_url": "https://example.com/sec", "source_note": "Reviewed test fixture", "data_type": "public",
        })
    columns = ["company", "fiscal_year", "period_start", "period_end", "publication_date", "currency", "revenue", "operating_income", "inventory", "cost_of_revenue", "source_url", "source_note", "data_type"]
    return pd.DataFrame(rows, columns=columns)


def test_first_year_has_no_invented_change_and_next_year_explains_signals():
    signals, summary, _ = screen_risk(frame([(2024, 100, 60, 20, 20), (2025, 80, 60, 4, 30)]))
    first = summary[summary.fiscal_year == 2024].iloc[0]
    second = summary[summary.fiscal_year == 2025].iloc[0]
    assert first.risk_level == "Not assessed"
    assert first.comparison_status == "insufficient_history"
    assert "no consecutive" in first.explanation.lower()
    assert second.risk_level == "Elevated"
    assert second.signal_count >= 3
    assert (signals.signal_type == "Demand").any()
    assert (signals.signal_type == "Inventory").any()
    assert all("planner" in text.lower() for text in signals.recommendation)
    assert all("not confirmation" not in text.lower() for text in signals.explanation)


def test_thresholds_are_configurable_and_deterministic():
    data = frame([(2024, 100, 60, 20, 20), (2025, 96, 60, 19, 21)])
    _, default_summary, _ = screen_risk(data)
    _, relaxed_summary, _ = screen_risk(data, RiskConfig(revenue_decline_moderate_pct=-10, revenue_decline_elevated_pct=-20, inventory_growth_moderate_pct=10, inventory_growth_elevated_pct=20, inventory_mix_moderate_pp=10, inventory_mix_elevated_pp=20, gross_margin_decline_moderate_pp=-10, gross_margin_decline_elevated_pp=-20, operating_margin_decline_moderate_pp=-10, operating_margin_decline_elevated_pp=-20))
    assert default_summary.iloc[1].risk_level == "Moderate"
    assert relaxed_summary.iloc[1].risk_level == "Low"


def test_missing_year_and_currency_gap_does_not_trigger_change_signal():
    data = frame([(2024, 100, 60, 20, 20), (2026, 80, 60, 4, 30)])
    _, summary, _ = screen_risk(data)
    assert summary.iloc[1].risk_level == "Not assessed"
    assert summary.iloc[1].comparison_status == "insufficient_history"
    assert "no consecutive" in summary.iloc[1].explanation.lower()
    data = frame([(2024, 100, 60, 20, 20), (2025, 80, 60, 4, 30)])
    data.loc[1, "currency"] = "EUR"
    _, summary, _ = screen_risk(data)
    assert summary.iloc[1].risk_level == "Not assessed"


def test_low_screening_when_changes_are_below_thresholds():
    signals, summary, _ = screen_risk(frame([(2024, 100, 60, 20, 20), (2025, 101, 60.5, 20.2, 20.1)]))
    assert summary.iloc[1].risk_level == "Low"
    assert signals.empty


def test_empty_and_short_inputs_are_supported():
    empty = frame([])
    signals, summary, metrics = screen_risk(empty)
    assert signals.empty and summary.empty and metrics.empty


def test_elevated_thresholds_must_be_more_severe_than_moderate():
    with pytest.raises(ValueError, match="Elevated must be more severe"):
        RiskConfig(revenue_decline_moderate_pct=-15, revenue_decline_elevated_pct=-5)
    with pytest.raises(ValueError, match="Elevated must be more severe"):
        RiskConfig(inventory_growth_moderate_pct=15, inventory_growth_elevated_pct=5)


def test_streamlit_warns_and_uses_defaults_for_invalid_thresholds():
    from pathlib import Path
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run(timeout=30)
    # Revenue moderate is the first control and revenue elevated the second.
    app.sidebar.number_input[0].set_value(-15.0)
    app.sidebar.number_input[1].set_value(-5.0)
    app = app.run(timeout=30)
    assert not app.exception
    assert any("Invalid screening thresholds" in warning.value for warning in app.sidebar.warning)


def test_real_screening_uses_approved_companies_only():
    from supplychainiq.data_loading import load_approved_data

    approved = load_approved_data()
    assert set(approved.company) == {"onsemi", "STMicroelectronics"}
    signals, summary, _ = screen_risk(approved)
    assert set(summary.company) == {"onsemi", "STMicroelectronics"}
    assert "Infineon Technologies" not in set(signals.company)
    assert signals.source_url.str.startswith("https://").all()


def test_eur_and_usd_companies_are_screened_within_company_only():
    usd = frame([(2024, 100, 60, 20, 20), (2025, 80, 60, 4, 30)])
    eur = usd.copy()
    eur["company"] = "Infineon Technologies"
    eur["currency"] = "EUR"
    _, summary, _ = screen_risk(pd.concat([usd, eur], ignore_index=True))
    assert set(summary.company) == {"onsemi", "Infineon Technologies"}
    assert set(summary[summary.fiscal_year == 2025].risk_level) == {"Elevated"}

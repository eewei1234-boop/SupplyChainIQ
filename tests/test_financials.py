import pytest
from streamlit.testing.v1 import AppTest
from supplychainiq.data_loading import load_data
from supplychainiq.validation import validate_data, DataValidationError
from supplychainiq.analysis import analyze


def test_public_data_has_no_fabricated_figures():
    assert load_data().empty


def test_demo_is_explicit_and_complete():
    df = load_data(demo=True)
    assert len(df) == 9
    assert set(df.data_type) == {'synthetic'}
    assert df.company.nunique() == 3


def test_known_financial_ratios():
    df = load_data(demo=True).iloc[:2].copy()
    df.loc[df.index[0], ['revenue', 'operating_income', 'inventory', 'cost_of_revenue']] = [100, -10, 20, 80]
    df.loc[df.index[1], 'revenue'] = 120
    result = analyze(df)
    assert result.iloc[0].gross_margin_pct == pytest.approx(20)
    assert result.iloc[0].operating_margin_pct == -10
    assert result.iloc[0].inventory_days_proxy == pytest.approx(91.25)
    assert result.iloc[1].revenue_growth_pct == pytest.approx(20)
    assert result.iloc[:1].revenue_growth_pct.isna().all()


def test_growth_does_not_bridge_missing_year_or_currency_change():
    df = load_data(demo=True).iloc[:2].copy()
    df.loc[df.index[1], 'fiscal_year'] += 1
    assert analyze(df).revenue_growth_pct.isna().all()
    df.loc[df.index[1], 'fiscal_year'] -= 1
    df.loc[df.index[1], 'currency'] = 'USD'
    assert analyze(df).revenue_growth_pct.isna().all()


@pytest.mark.parametrize('column,value', [('revenue', 0), ('inventory', -1), ('cost_of_revenue', 0), ('revenue', float('inf')), ('company', 'Unknown'), ('currency', 'XYZ'), ('fiscal_year', 2024.5), ('period_end', 'invalid'), ('data_type', 'verified'), ('source_note', ''), ('period_start', '2023-09-01'), ('currency', 'USD')])
def test_reject_invalid_records(column, value):
    df = load_data(demo=True).iloc[:1].copy()
    df[column] = value
    with pytest.raises(DataValidationError):
        validate_data(df)


def test_reject_duplicate_and_missing_columns():
    df = load_data(demo=True)
    import pandas as pd
    with pytest.raises(DataValidationError):
        validate_data(pd.concat([df, df.iloc[:1]]))
    with pytest.raises(DataValidationError):
        validate_data(df.drop(columns=['revenue']))


def test_public_url_required_and_synthetic_import_rejected():
    from io import StringIO
    df = load_data(demo=True).iloc[:1].copy()
    with pytest.raises(DataValidationError):
        load_data(StringIO(df.to_csv(index=False)))
    df['data_type'] = 'public'
    df['publication_date'] = '2024-02-01'
    with pytest.raises(DataValidationError):
        validate_data(df)
    df['source_url'] = 'https://example.com/disclosure'
    assert len(validate_data(df)) == 1


def test_dashboard_public_demo_filter_and_empty_states():
    app = AppTest.from_file(str(__import__('pathlib').Path(__file__).resolve().parents[1] / 'app.py')).run(timeout=30)
    assert not app.exception
    assert 'No verified' in app.warning[0].value
    app.sidebar.toggle[0].set_value(True).run()
    assert not app.exception
    assert len(app.metric) == 3
    assert 'SYNTHETIC' in app.warning[0].value
    app.sidebar.multiselect[0].set_value(['onsemi']).run()
    assert len(app.metric) == 1
    app.sidebar.multiselect[0].set_value([]).run()
    assert not app.exception
    assert any('Select at least' in item.value for item in app.info)


def test_public_csv_import_and_publication_date_validation():
    from io import StringIO
    df = load_data(demo=True).iloc[:1].copy()
    df['data_type'] = 'public'
    df['source_url'] = 'https://example.com/test-disclosure'
    df['source_note'] = 'Test fixture only; not a real financial disclosure'
    df['publication_date'] = '2023-11-01'
    assert len(load_data(StringIO(df.to_csv(index=False)))) == 1
    df['publication_date'] = '2023-01-01'
    with pytest.raises(DataValidationError):
        validate_data(df)


def test_all_dashboard_metrics_render():
    from pathlib import Path
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run()
    app.sidebar.toggle[0].set_value(True).run()
    for metric in app.selectbox[0].options:
        # The UI displays formatted labels; select using underlying metric keys.
        key = metric.lower().replace(' ', '_')
        app.selectbox[0].set_value(key).run()
        assert not app.exception

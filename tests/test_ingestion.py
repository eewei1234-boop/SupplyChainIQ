"""All numbers here are test fixtures, never company data."""
import copy
import pytest
from supplychainiq.ingestion import extract_sec, validate_observations, annual_dashboard_rows
from supplychainiq.official_reports import import_report_observations


def fixture():
    facts = {}
    for tag, val in [('Revenues', 100000000), ('InventoryNet', 20000000), ('OperatingIncomeLoss', -1000000), ('CostOfRevenue', 60000000)]:
        f = dict(end='2023-12-31', val=val, accn='0001097864-24-000001', filed='2024-02-01', form='10-K')
        if tag != 'InventoryNet':
            f['start'] = '2023-01-01'
        facts[tag] = {'units': {'USD': [f]}}
    return {'cik': 1097864, 'facts': {'us-gaap': facts}}


def extract(payload=None):
    return extract_sec(payload or fixture(), 'onsemi', digest='a'*64, retrieved_at='2026-10-27T00:00:00+00:00')


def test_extract_units_periods_and_no_automatic_verification():
    rows = extract()
    assert len(rows) == 4
    assert next(r for r in rows if r['metric'] == 'revenue')['value'] == 100
    assert {r['verification_status'] for r in rows} == {'extracted_pending_review'}
    assert annual_dashboard_rows(rows).empty
    for row in rows:
        row['verification_status'] = 'reviewed'
    annual = annual_dashboard_rows(rows)
    assert annual.iloc[0].revenue == 100
    assert annual.iloc[0].operating_income == -1


def test_quarter_ytd_and_instant_not_combined_as_annual():
    payload = fixture()
    f = payload['facts']['us-gaap']['Revenues']['units']['USD'][0]
    f.update(start='2023-10-01')
    rows = extract(payload)
    assert next(r for r in rows if r['metric'] == 'revenue')['period_type'] == 'quarter'
    f['start'] = '2023-04-01'
    assert next(r for r in extract(payload) if r['metric'] == 'revenue')['period_type'] == 'ytd'


def test_wrong_issuer_missing_concept_wrong_unit_and_conflict():
    payload = fixture()
    payload['cik'] = 1
    with pytest.raises(ValueError):
        extract(payload)
    payload = fixture()
    payload['facts']['us-gaap']['Revenues']['units'] = {'EUR': []}
    assert not any(r['metric'] == 'revenue' for r in extract(payload))
    payload = fixture()
    other = copy.deepcopy(payload['facts']['us-gaap']['Revenues'])
    other['units']['USD'][0]['val'] = 1
    payload['facts']['us-gaap']['SalesRevenueNet'] = other
    with pytest.raises(ValueError, match='Conflicting'):
        extract(payload)


@pytest.mark.parametrize('field,value', [('value', float('nan')), ('unit', 'thousands'), ('currency', 'EUR'), ('period_start', '2023-12-01'), ('publication_date', '2022-01-01'), ('verification_status', 'verified'), ('evidence_sha256', '')])
def test_validation(field, value):
    rows = [r for r in extract() if r['metric'] == 'revenue']
    rows[0][field] = value
    with pytest.raises(ValueError):
        validate_observations(rows)


def test_duplicates_and_missing_fields():
    rows = extract()
    with pytest.raises(ValueError, match='Duplicate'):
        validate_observations(rows + [rows[0]])
    del rows[0]['publication_date']
    with pytest.raises(ValueError):
        validate_observations(rows)


def test_ir_import_cannot_mark_itself_reviewed():
    rows = extract()
    for r in rows:
        r['source_document_url'] = 'https://investors.onsemi.com/test-fixture'
        r['verification_status'] = 'reviewed'
    result = import_report_observations(rows, b'TEST FIXTURE ONLY')
    assert all(r['verification_status'] == 'extracted_pending_review' for r in result)
    rows[0]['source_document_url'] = 'https://example.com/not-official'
    with pytest.raises(ValueError):
        import_report_observations(rows, b'TEST FIXTURE ONLY')


def test_refresh_failure_preserves_existing_file(tmp_path, monkeypatch):
    from scripts import refresh_data
    root = tmp_path / 'project'
    script = root / 'scripts' / 'refresh_data.py'
    target = root / 'data' / 'ingestion'
    target.mkdir(parents=True)
    old = target / 'onsemi.csv'
    old.write_text('previous reviewed candidate snapshot')
    monkeypatch.setattr(refresh_data, '__file__', str(script))
    monkeypatch.setattr('sys.argv', ['refresh_data', '--require-success'])
    def fail(*args):
        raise OSError('403 Forbidden')
    monkeypatch.setattr(refresh_data, 'fetch_sec', fail)
    monkeypatch.setattr(refresh_data.time, 'sleep', lambda _: None)
    with pytest.raises(SystemExit) as exc:
        refresh_data.main()
    assert exc.value.code == 1
    assert old.read_text() == 'previous reviewed candidate snapshot'
    assert '403 Forbidden' in (target / 'refresh_status.json').read_text()

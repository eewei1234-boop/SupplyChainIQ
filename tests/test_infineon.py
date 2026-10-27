import pytest

from supplychainiq.infineon import evidence_metadata, validate_report_record


def record(**overrides):
    base = {
        "company": "Infineon Technologies",
        "fiscal_year": 2024,
        "period_start": "2023-10-01",
        "period_end": "2024-09-30",
        "currency": "EUR",
        "unit": "millions",
        "metric": "revenue",
        "source_document_url": "https://www.infineon.com/report.pdf",
        "accounting_standard": "IFRS",
        "consolidation_scope": "consolidated",
        "page": 120,
        "reported_metric": "Revenue",
        "verification_status": "extracted_pending_review",
        "source_note": "IFRS consolidated statement, EUR millions, page 120",
    }
    base.update(overrides)
    return base


def test_infineon_requires_september_fiscal_year_and_eur_scope():
    assert validate_report_record(record())["period_end"] == "2024-09-30"
    with pytest.raises(ValueError, match="October 1 through September 30"):
        validate_report_record(record(period_end="2024-12-31"))
    with pytest.raises(ValueError, match="EUR millions"):
        validate_report_record(record(currency="USD"))


def test_segment_result_cannot_be_called_operating_income():
    with pytest.raises(ValueError, match="Segment Result"):
        validate_report_record(record(metric="operating_income", reported_metric="Segment Result"))
    assert validate_report_record(record(metric="operating_income", reported_metric="Operating income"))["metric"] == "operating_income"


def test_report_requires_page_scope_standard_and_official_source():
    with pytest.raises(ValueError, match="page"):
        validate_report_record(record(page=0))
    with pytest.raises(ValueError, match="official HTTPS"):
        validate_report_record(record(source_document_url="https://example.com/report.pdf"))
    with pytest.raises(ValueError, match="IFRS consolidated"):
        validate_report_record(record(accounting_standard="US GAAP"))


def test_evidence_hash_is_reproducible_and_requires_official_url():
    metadata = evidence_metadata(b"fixture report", "https://www.infineon.com/report.pdf", "2026-10-27T00:00:00+00:00")
    assert metadata["evidence_bytes"] == len(b"fixture report")
    assert len(metadata["evidence_sha256"]) == 64
    with pytest.raises(ValueError, match="official"):
        evidence_metadata(b"fixture report", "https://example.com/report.pdf", "2026-10-27T00:00:00+00:00")

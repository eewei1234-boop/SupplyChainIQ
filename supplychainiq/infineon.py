"""Validation helpers for manually transcribed Infineon annual reports.

Infineon's fiscal year ends on September 30. This module validates report
metadata and accounting definitions before a record can enter the shared
observation schema. It does not parse PDFs or treat Segment Result as
consolidated operating income.
"""

from datetime import date
from hashlib import sha256
from urllib.parse import urlsplit


INFINEON_IR_URL = "https://www.infineon.com/cms/en/about-infineon/investor/reports-and-presentations/"
INFINEON_HOSTS = {"infineon.com", "www.infineon.com"}
INFINEON_METRICS = {"revenue", "cost_of_revenue", "operating_income", "inventory"}


def validate_report_record(record):
    """Validate a manually transcribed report observation's evidence metadata."""
    if record.get("company") != "Infineon Technologies":
        raise ValueError("Infineon report records must use the canonical company name")
    year = int(record.get("fiscal_year", 0))
    if year not in {2024, 2025}:
        raise ValueError("Only FY2024 and FY2025 Infineon records are supported")
    if record.get("period_start") != f"{year - 1}-10-01" or record.get("period_end") != f"{year}-09-30":
        raise ValueError("Infineon annual periods must run October 1 through September 30")
    if record.get("currency") != "EUR" or record.get("unit") != "millions":
        raise ValueError("Infineon records must preserve EUR millions")
    if record.get("metric") not in INFINEON_METRICS:
        raise ValueError("Unsupported Infineon metric")
    url = urlsplit(str(record.get("source_document_url", "")))
    if url.scheme != "https" or url.hostname not in INFINEON_HOSTS:
        raise ValueError("Infineon evidence must use an official HTTPS source URL")
    if record.get("accounting_standard") != "IFRS" or record.get("consolidation_scope") != "consolidated":
        raise ValueError("Infineon records require IFRS consolidated-scope metadata")
    if not isinstance(record.get("page"), int) or record["page"] <= 0:
        raise ValueError("Infineon records require a positive report page number")
    if record["metric"] == "operating_income" and record.get("reported_metric") in {"Segment Result", "segment_result"}:
        raise ValueError("Segment Result cannot be substituted for consolidated operating income")
    if record.get("verification_status") not in {"extracted_pending_review", "reviewed"}:
        raise ValueError("Unknown Infineon verification status")
    if not record.get("source_note") or not all(token in record["source_note"] for token in ("IFRS", "consolidated", "EUR millions")):
        raise ValueError("Source note must preserve IFRS, consolidated scope and EUR millions")
    return record


def evidence_metadata(document, source_url, retrieved_at):
    """Return immutable report evidence metadata for a downloaded PDF."""
    if not document:
        raise ValueError("Original Infineon report bytes are required")
    host = urlsplit(source_url).hostname
    if urlsplit(source_url).scheme != "https" or host not in INFINEON_HOSTS:
        raise ValueError("Report URL must be an official Infineon HTTPS URL")
    return {
        "source_document_url": source_url,
        "retrieved_at": retrieved_at,
        "evidence_sha256": sha256(document).hexdigest(),
        "evidence_bytes": len(document),
    }

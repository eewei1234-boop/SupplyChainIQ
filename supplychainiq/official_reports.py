"""Import manually transcribed IR observations alongside their original document.

This does not extract tables from PDFs or certify transcription accuracy.
"""
from hashlib import sha256
from datetime import datetime, timezone
from urllib.parse import urlsplit
from .ingestion import validate_observations

HOSTS = {
    'Infineon Technologies': {'www.infineon.com', 'infineon.com'},
    'onsemi': {'investors.onsemi.com', 'www.onsemi.com'},
    'STMicroelectronics': {'investors.st.com', 'www.st.com'},
}


def import_report_observations(records, document):
    if not document:
        raise ValueError('Original report bytes required')
    result = []
    for record in records:
        row = dict(record)
        host = urlsplit(row['source_document_url']).hostname
        if host not in HOSTS.get(row['company'], set()):
            raise ValueError('Expected an official company report URL')
        row['evidence_sha256'] = sha256(document).hexdigest()
        row['retrieved_at'] = datetime.now(timezone.utc).isoformat()
        row['verification_status'] = 'extracted_pending_review'
        result.append(row)
    return validate_observations(result)

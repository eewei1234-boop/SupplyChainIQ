"""Evidence-preserving SEC extraction. Extraction is not financial verification."""
from datetime import date, datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
from urllib.request import Request, urlopen
import pandas as pd

ISSUERS = {'onsemi': 1097864, 'STMicroelectronics': 932787}
CURRENCIES = {'onsemi': 'USD', 'STMicroelectronics': 'USD', 'Infineon Technologies': 'EUR'}
# Explicit consolidated concepts only; do not guess extensions or adjusted metrics.
CONCEPTS = {
    'revenue': [('us-gaap', 'RevenueFromContractWithCustomerExcludingAssessedTax'), ('us-gaap', 'Revenues'), ('us-gaap', 'SalesRevenueNet'), ('ifrs-full', 'Revenue')],
    'inventory': [('us-gaap', 'InventoryNet'), ('ifrs-full', 'Inventories')],
    'gross_profit': [('us-gaap', 'GrossProfit'), ('ifrs-full', 'GrossProfit')],
    'cost_of_revenue': [('us-gaap', 'CostOfRevenue'), ('us-gaap', 'CostOfGoodsAndServicesSold'), ('ifrs-full', 'CostOfSales')],
    'operating_income': [('us-gaap', 'OperatingIncomeLoss'), ('ifrs-full', 'ProfitLossFromOperatingActivities')],
}
FIELDS = ['company', 'metric', 'fiscal_year', 'period_start', 'period_end', 'period_type', 'currency', 'unit', 'value', 'publication_date', 'source_url', 'source_document_url', 'accession', 'form', 'concept', 'retrieved_at', 'evidence_sha256', 'verification_status']


def validate_observations(rows):
    """Missing observations are omitted, never filled with zeros."""
    seen = set()
    for r in rows:
        if set(FIELDS) - set(r):
            raise ValueError('Missing observation metadata')
        if r['company'] not in CURRENCIES or r['currency'] != CURRENCIES[r['company']]:
            raise ValueError('Inconsistent company currency')
        if r['metric'] not in CONCEPTS or r['unit'] != 'millions':
            raise ValueError('Unknown metric or inconsistent units')
        if isinstance(r['value'], bool) or not isinstance(r['value'], (int, float)) or not math.isfinite(r['value']):
            raise ValueError('Missing or nonfinite value')
        if r['metric'] != 'operating_income' and r['value'] < 0:
            raise ValueError('Negative balance or sales')
        end = date.fromisoformat(r['period_end'])
        if not 2023 <= end.year <= 2026 or r['fiscal_year'] != end.year:
            raise ValueError('Unsupported fiscal year')
        if date.fromisoformat(r['publication_date']) < end:
            raise ValueError('Publication precedes period end')
        if r['metric'] == 'inventory':
            if r['period_type'] != 'instant' or r['period_start'] != '':
                raise ValueError('Inventory must be a period-end balance')
        else:
            days = (end - date.fromisoformat(r['period_start'])).days + 1
            valid = {'annual': (350, 380), 'quarter': (70, 110), 'ytd': (150, 300)}
            limits = valid.get(r['period_type'])
            if not limits or not limits[0] <= days <= limits[1]:
                raise ValueError('Mismatched reporting period')
        if r['verification_status'] not in ['extracted_pending_review', 'reviewed']:
            raise ValueError('Unknown verification status')
        if len(r['evidence_sha256']) != 64 or any(c not in '0123456789abcdef' for c in r['evidence_sha256']):
            raise ValueError('Invalid evidence hash')
        from urllib.parse import urlsplit
        for key in ['source_url', 'source_document_url']:
            u = urlsplit(r[key])
            if u.scheme != 'https' or not u.hostname or u.username or u.password:
                raise ValueError('Invalid source URL')
        identity = tuple(r[k] for k in ['company', 'metric', 'period_start', 'period_end', 'accession'])
        if identity in seen:
            raise ValueError('Duplicate observation')
        seen.add(identity)
    return rows


def extract_sec(payload, company, *, digest, retrieved_at):
    """Keep separate filing versions; never blend restatements or YTD and quarters."""
    cik = ISSUERS[company]
    if int(payload.get('cik', 0)) != cik:
        raise ValueError('SEC issuer identity mismatch')
    rows = []
    used = set()
    for metric, concepts in CONCEPTS.items():
        for namespace, concept in concepts:
            units = payload.get('facts', {}).get(namespace, {}).get(concept, {}).get('units', {})
            for fact in units.get(CURRENCIES[company], []):
                end = date.fromisoformat(fact['end'])
                if not 2023 <= end.year <= 2026 or fact.get('form') not in ['10-K', '10-Q', '20-F', '10-K/A', '10-Q/A', '20-F/A', '6-K']:
                    continue
                start = fact.get('start', '')
                if metric == 'inventory':
                    if start:
                        continue
                    kind = 'instant'
                else:
                    if not start:
                        continue
                    days = (end - date.fromisoformat(start)).days + 1
                    kind = 'annual' if 350 <= days <= 380 else 'quarter' if 70 <= days <= 110 else 'ytd' if 150 <= days <= 300 else None
                    if kind is None:
                        continue
                accession = fact['accn']
                import re
                if not re.fullmatch(r'\d{10}-\d{2}-\d{6}', accession):
                    raise ValueError('Invalid SEC accession')
                identity = (metric, start, fact['end'], accession)
                value = fact['val'] / 1_000_000
                if identity in used:
                    previous = next(r for r in rows if (r['metric'], r['period_start'], r['period_end'], r['accession']) == identity)
                    if previous['value'] != value:
                        raise ValueError(f'Conflicting concepts for {identity}; manual reconciliation required')
                    continue
                used.add(identity)
                rows.append(dict(zip(FIELDS, [company, metric, end.year, start, fact['end'], kind, CURRENCIES[company], 'millions', value, fact['filed'], f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json', f'https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace("-", "")}/', accession, fact['form'], f'{namespace}:{concept}', retrieved_at, digest, 'extracted_pending_review'])))
    return validate_observations(rows)


def fetch_sec(company, cache, user_agent):
    if not user_agent or '@' not in user_agent:
        raise ValueError('Set SEC_USER_AGENT to an application name and real contact email per SEC fair-access guidance')
    url = f'https://data.sec.gov/api/xbrl/companyfacts/CIK{ISSUERS[company]:010d}.json'
    request = Request(url, headers={'User-Agent': user_agent, 'Accept': 'application/json'})
    with urlopen(request, timeout=45) as response:
        raw = response.read()
    payload = json.loads(raw)
    digest = sha256(raw).hexdigest()
    retrieved = datetime.now(timezone.utc).isoformat()
    rows = extract_sec(payload, company, digest=digest, retrieved_at=retrieved)
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    (cache / f'{digest}.json').write_bytes(raw)
    return rows


def annual_dashboard_rows(observations):
    """Only explicitly reviewed, complete annual contexts enter the legacy view."""
    from .validation import COLUMNS, validate_data
    records = []
    validate_observations(observations)
    groups = {}
    for row in observations:
        if row['verification_status'] == 'reviewed':
            groups.setdefault((row['company'], row['period_end'], row['accession']), []).append(row)
    for (company, end, accession), rows in groups.items():
        annual = [r for r in rows if r['period_type'] == 'annual']
        starts = set(r['period_start'] for r in annual)
        if len(starts) != 1:
            continue
        metrics = {r['metric']: r for r in annual + [r for r in rows if r['metric'] == 'inventory']}
        required = ['revenue', 'inventory', 'operating_income', 'cost_of_revenue']
        if not all(k in metrics for k in required):
            continue
        r = metrics['revenue']
        record = dict(company=company, fiscal_year=r['fiscal_year'], period_start=r['period_start'], period_end=end, publication_date=r['publication_date'], currency=r['currency'], source_url=r['source_document_url'], source_note=f'Reviewed SEC filing {accession}; original observations retain concept and evidence hash', data_type='public')
        record.update({k: metrics[k]['value'] for k in required})
        records.append(record)
    # Multiple filing versions require explicit reconciliation, never a silent latest-wins merge.
    return validate_data(pd.DataFrame(records, columns=COLUMNS))

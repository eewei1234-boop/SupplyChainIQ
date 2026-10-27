"""Run from repository root: python -m scripts.refresh_data [--require-success]."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
from supplychainiq.ingestion import ISSUERS, fetch_sec, FIELDS
import pandas as pd


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-success', action='store_true')
    args = parser.parse_args()
    target = Path(__file__).resolve().parents[1] / 'data' / 'ingestion'
    target.mkdir(parents=True, exist_ok=True)
    report = {'attempted_at': datetime.now(timezone.utc).isoformat(), 'companies': {}}
    failed = False
    for company in ISSUERS:
        path = target / f'{company}.csv'
        try:
            rows = fetch_sec(company, target / 'evidence', os.environ.get('SEC_USER_AGENT', ''))
            if not rows:
                raise ValueError('No supported facts found; existing observations preserved')
            temporary = path.with_suffix('.tmp')
            pd.DataFrame(rows, columns=FIELDS).to_csv(temporary, index=False)
            temporary.replace(path)
            report['companies'][company] = {'status': 'extracted_pending_review', 'observations': len(rows)}
        except Exception as exc:
            failed = True
            report['companies'][company] = {'status': 'unavailable', 'error': str(exc), 'existing_data_preserved': True}
        time.sleep(.2)  # Below SEC fair-access rate, sequential requests.
    report['companies']['Infineon Technologies'] = {'status': 'unavailable', 'reason': 'Official report extraction requires manual source reconciliation; no figures populated'}
    (target / 'refresh_status.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    if args.require_success and failed:
        raise SystemExit(1)

if __name__ == '__main__':
    main()

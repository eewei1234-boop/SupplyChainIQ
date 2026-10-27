"""Attempt configured Infineon report downloads and preserve evidence metadata.

Report URLs must be supplied explicitly in ``data/review/infineon_report_sources.json``.
The script never guesses a PDF URL and never writes financial values.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.request import Request, urlopen

from supplychainiq.infineon import evidence_metadata


def main():
    root = Path(__file__).resolve().parents[1]
    manifest_path = root / "data" / "review" / "infineon_report_sources.json"
    manifest = json.loads(manifest_path.read_text())
    evidence_dir = root / "data" / "ingestion" / "infineon" / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    attempted = datetime.now(timezone.utc).isoformat()
    for report in manifest["reports"]:
        report["attempted_at"] = attempted
        url = report.get("report_url")
        if not url:
            report["status"] = "report_url_required"
            report["error"] = "No direct official PDF URL was supplied; no URL was guessed."
            continue
        try:
            request = Request(url, headers={"User-Agent": "SupplyChainIQ research"})
            with urlopen(request, timeout=45) as response:
                document = response.read()
            metadata = evidence_metadata(document, url, attempted)
            target = evidence_dir / f"FY{report['fiscal_year']}.pdf"
            target.write_bytes(document)
            report.update(metadata, status="retrieved", evidence_path=str(target.relative_to(root)))
        except Exception as exc:
            report["status"] = "unavailable"
            report["error"] = str(exc)
    manifest["last_attempted_at"] = attempted
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

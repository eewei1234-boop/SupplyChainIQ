# SupplyChainIQ

AI-Powered Semiconductor Market Intelligence & Supply Chain Risk Control Tower

## Project Overview
An independent portfolio project analyzing public financial and industry data from Infineon Technologies, onsemi, and STMicroelectronics.

## Objectives
- Monitor semiconductor industry performance
- Compare company financial and inventory trends
- Identify potential supply chain risks
- Automate market intelligence reporting
- Develop demand and inventory planning simulations

## Technologies
Python, Streamlit, Pandas, Plotly, GitHub Actions, and AI automation.

## Data Policy
Public company disclosures will be distinguished from synthetic demonstration data.

## Status
Phase 1: Project foundation and dashboard development.

## Run Phase 1

Requires Python 3.12 (tested). From the repository folder:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -q
streamlit run app.py --server.address 0.0.0.0
```

The dashboard includes company/year filters, gross and operating margins, revenue growth,
revenue charts grouped by currency, inventory ratios, source notes, and CSV export.
Enable **Use synthetic demonstration data** in the sidebar to explore all three
companies. Every demo number is fictional. Public mode starts empty: official
investor sites were blocked by the setup environment's network policy, so no
unverified company figures have been included. This is a functional project
foundation; populated, verified public financial comparisons remain outstanding.

### Import real disclosures

Download the CSV template in the dashboard. Add one annual record per company
and fiscal year. Required columns are shown in `data/public_financials.csv`.
Amounts are in millions of native currency (EUR or USD). Use reported operating
income, year-end inventory and annual cost of revenue from the same consolidated
report; do not mix adjusted segment profit with reported operating income.
`period_start` and `period_end` are ISO dates defining a full annual period;
`publication_date` is the actual disclosure publication date (not retrieval date); `source_url` must be an HTTPS disclosure link;
`source_note` should include report title, page/table, units and accounting basis;
`data_type` is `public`. Upload the CSV, or maintain reviewed records in
`data/public_financials.csv`. Never relabel synthetic records as public.

Validation checks structure and plausibility, **not authenticity**. A human must
check each figure against its source. Missing required amounts must be researched;
do not fill them with zeros. File uploads are session-local and are not saved.
Revenue growth requires consecutive fiscal years and the same currency. Charts
do not convert currencies. Inventory days use year-end inventory / annual cost
of revenue × 365, not average inventory. Fiscal calendars and accounting bases
differ; these indicators alone do not prove supply chain risk.

## Preview using only an iPad

You do not need Python on your iPad. Publish the repository changes first, then:

1. In Safari, open **https://share.streamlit.io/** and sign in using GitHub.
2. Select **Create app**, choose `eewei1234-boop/SupplyChainIQ`, branch `main`,
   and main file `app.py`. Under advanced settings choose Python 3.12 if offered.
3. Select **Deploy**. Streamlit installs `requirements.txt` and starts the app.
4. Open the HTTPS app address Streamlit supplies in Safari. Enable demo mode
   in the sidebar to explore it. Use Safari's **Request Desktop Website** if
   deployment controls are hard to find. On a narrow screen, open the sidebar
   with the top-left arrow.

Community Cloud requires access to the GitHub repository and a supported account.
Do not upload confidential records to a publicly shared app. No API keys are
needed for the bundled demo. Cloud deployment is a separate step and has not
been performed by this coding session. The onboarding interface itself cannot
preview this machine's local server; a localhost address will not open this
cloud application from an iPad.

## Project layout

- `app.py`: Streamlit dashboard.
- `supplychainiq/data_loading.py`: CSV loading, with separate public/demo modes.
- `supplychainiq/validation.py`: schema and numerical validation.
- `supplychainiq/analysis.py`: financial ratio calculations.
- `data/`: empty public template and explicitly synthetic demonstration records.
- `tests/`: financial calculations, invalid input and interactive dashboard tests.
- `.github/workflows/tests.yml`: automated checks on pushes and pull requests.

The original detailed specification was not present in this session. This
implementation follows the README and the Phase 1 request. Forecasting, live
scraping, AI reports and inventory planning simulations are future work.

## Phase 2: evidence-preserving ingestion (feature branch)

Phase 1's demo, CSV import, charts and annual analysis are preserved. A separate
observation layer now retains individual metrics, rather than forcing partial or
quarterly reports into complete annual rows. Open **Phase 2 · Ingestion evidence
and availability** in the dashboard to inspect refresh status and extracted CSVs.

### Sources and refresh

- onsemi: SEC CIK **1097864**, Company Facts structured XBRL.
- STMicroelectronics: SEC CIK **932787**, Company Facts structured XBRL.
- Infineon: official investor reports; `official_reports.py` accepts manually
  transcribed observations alongside the downloaded original document. It does
  not parse PDFs or claim the transcription is verified.
- Company Facts endpoints: `https://data.sec.gov/api/xbrl/companyfacts/CIK0001097864.json`
  and `https://data.sec.gov/api/xbrl/companyfacts/CIK0000932787.json`.

Set `SEC_USER_AGENT` to an application name and your real contact email (required
by our client for SEC fair access), then run from the repository root:

```bash
source .venv/bin/activate
python -m scripts.refresh_data --require-success
python -m pytest -q
```

No API key is needed. The script caches original JSON by SHA-256, preserves
existing files on failed retrieval, records a timestamped availability report,
and writes extracted observations separately under `data/ingestion/`. Strict mode
exits unsuccessfully if either SEC issuer cannot be extracted. It never replaces
`data/public_financials.csv` or the synthetic dataset. The manual GitHub Actions
workflow runs the tests and refresh, then uploads review artifacts; it never
commits results. Configure repository variable `SEC_USER_AGENT` before running it.
Scheduling is intentionally not enabled yet.

### Evidence and verification

Each observation records company, metric, original period dates, period type,
fiscal-year label, currency, normalized unit (millions), value, filing date,
source endpoint, filing archive URL, accession, form, XBRL concept, retrieval time,
evidence hash and verification status. Filing date is used as the regulatory
publication date, not an earlier earnings-release date. Original units and values
remain in the cached JSON. Filing URLs point to accession directories; exact
primary-document identification and table/page reconciliation remain review work.

All automatic and manual imports start as **extracted_pending_review**. Neither
HTTPS, a checksum nor schema validation establishes financial accuracy. Review
original documents, consolidated scope, fiscal calendar, units, concept mapping
and amendments before explicitly setting observations to `reviewed`.
`annual_dashboard_rows` can validate and convert reviewed, complete, same-filing
annual observations into the Phase 1 schema. It refuses duplicate annual versions;
a reviewer must choose the appropriate restatement before saving a public CSV.
No automatic promotion to the public comparison is performed.

SEC extraction supports explicit GAAP/IFRS concepts for revenue, inventory, gross
profit, cost of revenue and operating income for period ends in 2023–2026. Unknown
extensions and missing concepts remain absent. Conflicting concept values stop
that issuer's extraction. Instant inventory balances, annual flows, discrete
quarters and YTD flows remain distinct; quarters are never invented by subtraction.
The current annual display retains its existing growth and inventory ratios;
quarterly observations are available as evidence, not mixed into annual charts.
Do not annualize inventory ratios using quarterly sales without a new methodology.

### Current availability and limitations

Live checks in this environment returned proxy **403 Forbidden** for both SEC
Company Facts URLs and Infineon's official reports site. No historical figures
have been retrieved or verified here: revenue, inventory, gross profit/margin and
operating income for all three companies across 2023–2026 remain unavailable.
The refresh command also requires a real SEC contact user-agent, which is not
currently configured. Add network access for `data.sec.gov`, `www.sec.gov` and the
needed company report hosts in your environment settings, then rerun refresh.
Do not assume all 2026 annual reports have been published.

Company Facts may omit foreign-issuer interim facts and use issuer extensions.
This initial module has offline fixture coverage, but live payload compatibility
cannot be confirmed until access works. Fiscal-year labels currently follow the
period-end year; near-January 52/53-week onsemi periods require fiscal-calendar
review before promotion. No currency conversion is performed. Infineon's September
fiscal year remains distinct from peer calendar years. Original period dates must
always accompany comparisons.

These Phase 2 commands supersede the Phase 1 note that no live API client exists.
Automated PDF extraction, industry ingestion and AI features remain future work.

## Phase 2.5: review and approval workflow

The repository includes a review layer for the financial-observations-for-review
archive produced by the extraction workflow. Place the archive contents under
`data/ingestion/`: company CSV files at that level and the original SEC JSON
files under `data/ingestion/evidence/`. Then run:

```bash
python -m scripts.review_financial_data
```

The command writes `data/ingestion/review_observations.csv` and a summary. It
rechecks each row's evidence SHA-256 digest and exact SEC issuer, concept,
accession, period and value. It labels repeated same-value periods across
filings separately from conflicting duplicate periods. It never drops either
filing and never chooses the newest filing automatically.

The approved comparison file is
`data/approved_financial_observations.csv`. It is intentionally empty until a
human has reconciled the original filing and explicitly sets both
`verification_status=reviewed`, `review_status=approved`, and a review reason
containing `approved after source reconciliation`. The dashboard's real-data
mode reads only that approved file. Extracted, unreconciled, duplicate and
synthetic rows cannot appear in the real comparison.

The review command never overwrites `data/approved_financial_observations.csv`.
To approve the first record, copy a reconciled row from
`data/ingestion/review_observations.csv` into that separate file, check the
original SEC filing and duplicate-period context, then set
`verification_status` to `reviewed`, `review_status` to `approved`, and add
`approved after source reconciliation` to `review_reason`. Keep one filing
context per metric and period. Run the review command again to refresh review
output; your approved file will be preserved, and the dashboard will read it
from `data/approved_financial_observations.csv`.

The Phase 2.5 review archive currently contains 172 onsemi observations, 29
STMicroelectronics observations and two SEC Company Facts JSON files. The review
matches all 201 rows to their issuer, concept, accession, period, value and
evidence hash. It identifies 161 same-value historical repeats across filings
and 40 observations with a single current filing context. There are no
conflicting values in this archive. Repeated values still require a reviewer to
choose the filing context; they are retained rather than silently discarded.
Infineon remains awaiting official-report verification. No values were marked
approved or verified automatically. Inspect every `review_reason` before
approving any row.

The dashboard shows a last extraction attempt from `refresh_status.json`, but
this is a freshness indicator for the extraction process, not proof that values
are current. Approved observations retain source URLs, periods, filing dates and
approval status in the review artifacts. Native currencies and fiscal periods
remain separate; comparisons should use compatible period types and period-end
dates. Gross margin is calculated only when reviewed revenue and cost of revenue
are both present. Missing metrics remain missing.

For Infineon, use `supplychainiq.official_reports.import_report_observations` with
the downloaded official annual or quarterly report bytes and its official HTTPS
URL. The helper hashes the source document and starts the rows as pending review;
it does not parse PDFs or certify a transcription. Record the report's table/page,
publication date, fiscal calendar and units in the observation note before human
approval. Do not bypass website restrictions or use figures from search snippets.

## Phase 2.6: FY2024/FY2025 annual candidate review

`python -m scripts.build_annual_review` creates concise candidate tables at
`data/review/onsemi_annual_fy2024_fy2025.csv` and
`data/review/STMicroelectronics_annual_fy2024_fy2025.csv`. Each table contains
revenue, cost of revenue, operating income and the latest year-end inventory
balance for FY2024 and FY2025. It preserves all candidate accession numbers and
filing URLs. Earlier quarterly inventory balances stay in the 201-row source
archive and are not confused with year-end inventory.

The cached SEC Company Facts values reconcile exactly, but the SEC filing pages
returned `403 Forbidden` in this environment. Therefore every candidate has
`independently_verified=false` and `approval_status=pending_human_filing_review`.
The approved dataset remains empty. Before approving, open each listed filing,
confirm consolidated company scope, statement/table, reported units, fiscal
period and whether a later filing is an amendment or a comparative repeat. For
onsemi FY2024 and ST FY2024, multiple filings report the same values; do not
choose a filing just because it is newest. Onsemi FY2024 year-end inventory is
2,242.0 USD millions; onsemi FY2025 is 1,989.6. ST FY2024 is 2,794.0 and ST
FY2025 is 3,136.0, all pending filing review.

## Phase 3: Supply Chain Risk Intelligence

The dashboard now includes a deterministic risk-screening section. It reads the
approved dataset in real-data mode and the explicitly labelled demo dataset only
when the synthetic toggle is enabled. Infineon remains visible as unavailable
until approved figures are added.

The rules compare consecutive annual periods in the same native currency:

- Demand: revenue decline.
- Inventory: year-end inventory growth, inventory-to-revenue change, and the
  combination of rising inventory with falling revenue.
- Profitability: gross-margin and operating-margin declines.

Default Moderate/Elevated thresholds are configurable in the sidebar. Each
signal shows its observed change, threshold, explanation, source URL and a
practical demand-planning or supply-planning recommendation. The screening
levels are Low, Moderate and Elevated indicators only. They do not confirm an
operational disruption, identify a root cause or forecast demand.

The first available year for a company has `comparison_status=insufficient_history`
and risk level `Not assessed`; no year-over-year change is invented. Missing
periods, currency changes and fiscal-year gaps also suppress change signals.
Elevated thresholds must be more severe than their Moderate counterparts; invalid
sidebar settings show a warning and use safe defaults. Use the source references
below the dashboard to investigate approved financial records before acting on a
signal. The deterministic engine is implemented in `supplychainiq/risk.py` and
does not require a paid AI API.

## Phase 3.5: Infineon official-report integration

Infineon uses an October 1–September 30 fiscal year. The integration helpers
therefore require FY2024 `2023-10-01` through `2024-09-30` and FY2025
`2024-10-01` through `2025-09-30`, preserve EUR millions, require IFRS
consolidated scope and require an exact report page. `Segment Result` is rejected
as a substitute for consolidated operating income; it is a segment measure and
must not be silently relabelled.

`data/review/infineon_report_sources.json` records the official investor-relations
index and the retrieval status for both reports. Run
`python -m scripts.fetch_infineon_reports` only after supplying direct official
PDF URLs. The script preserves downloaded PDFs under
`data/ingestion/infineon/evidence/`, records retrieval timestamps and SHA-256
hashes, and never extracts or approves figures automatically.

During this phase the Infineon investor-relations site returned proxy
`403 Forbidden`, and no direct PDF URL was available in the repository. No
Infineon report bytes or financial values were added, and the dashboard continues
to show Infineon as awaiting verification. To complete the integration, provide
the official FY2024 and FY2025 PDF URLs, inspect the consolidated IFRS income
statement and balance sheet pages, record revenue, cost of sales, consolidated
operating income (or document the exact equivalent), and inventories in EUR
millions, then run the existing review and approval workflow. The risk engine
keeps Infineon's EUR history separate from the USD peer histories.

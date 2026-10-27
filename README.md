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

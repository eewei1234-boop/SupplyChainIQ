# Future collection boundary (not implemented in Phase 1)

Keep future collectors separate from analysis and UI. A collector should return
records matching `validation.COLUMNS`, then pass through `validate_data` and
human source review before entering `data/public_financials.csv`.

Company financial reports are the primary evidence. A later SEC EDGAR adapter
should respect SEC identification and fair-access policies and preserve filing
accession numbers, original concept names, units and fiscal periods. An industry
adapter for WSTS or SIA should preserve licensing, attribution and methodology;
industry series must not be inserted into company financial records.

Retain original documents and extraction metadata outside the UI, including
retrieval time, publication date, report URL, page/table and accounting basis.
Never overwrite reviewed records silently. Reject duplicates and quarterly data
in this annual schema. Check fiscal calendars, consolidated/segment scope,
restatements and native currencies before comparing companies.

No scheduled scraping, live API calls, AI risk scoring or forecasts are included.

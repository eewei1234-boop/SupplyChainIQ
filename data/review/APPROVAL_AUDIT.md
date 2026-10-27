# Annual financial observation approval audit — FY2024 and FY2025

**Status:** Proposed approval on feature branch. The repository owner should review this pull request before merging it into the public dashboard.

## Scope and methodology

Sixteen SEC Company Facts observations (four metrics × two years × two issuers) were copied **without changing amounts, dates, accession numbers, original XBRL concepts, evidence SHA-256 hashes, or retrieval timestamps** from `data/ingestion/review_observations.csv` into `data/approved_financial_observations.csv`. Each source observation had `reconciliation_status=source_reconciled_pending_approval` based on an exact cached SEC JSON fact and matching evidence hash.

A separate, independent check was performed against the companies' **audited FY2025 annual filings**, which include FY2024 comparative columns. The filings' original statements, not web search snippets or the cached JSON alone, were used to verify all four metrics. All figures are in **USD millions**, with positive cost-of-revenue amounts stored as expenses for the dashboard. Revenue refers to total reported consolidated revenue / ST *net revenues* (not ST *net sales*). Inventory is a **December 31 balance**, not an annual flow. Both companies report December 31 fiscal year ends in these observations.

### onsemi — Form 10-K, FY2025

- SEC accession: `0001097864-26-000006`
- Filing: https://www.sec.gov/Archives/edgar/data/1097864/000109786426000006/on-20251231.htm
- Source: audited consolidated statements of operations and balance sheets; management's comparison of FY2025 and FY2024 in the same filing. The SEC HTML filing contains the figures below.

| Metric (USD millions) | FY2024 | FY2025 |
|---|---:|---:|
| Revenue | 7,082.3 | 5,995.4 |
| Cost of revenue | 3,866.2 | 4,011.5 |
| Operating income | 1,767.7 | 84.2 |
| Year-end inventory | 2,242.0 | 1,989.6 |

FY2024 amounts are the comparative figures in the FY2025 10-K, not a mixture of accession contexts. Inventory figures also reconcile to the balance sheet and inventory note.

### STMicroelectronics — Form 20-F, FY2025

- SEC accession: `0000932787-26-000009`
- SEC filing: https://www.sec.gov/Archives/edgar/data/932787/000093278726000009/stm-20251231.htm
- Issuer-hosted original PDF: https://investors.st.com/static-files/e4d9410f-f7ef-4df7-9325-f5fc4cafba8d
- Audited consolidated statements of income: report page **F-4** (PDF page 176, zero-index page 175).
- Audited consolidated balance sheets: report page **F-6** (PDF page 178, zero-index page 177).
- The same FY2025 Form 20-F reports FY2024 comparative figures; its statements use U.S. GAAP.

| Metric (USD millions) | FY2024 | FY2025 |
|---|---:|---:|
| Net revenues | 13,269 | 11,800 |
| Cost of sales (expense magnitude) | 8,049 | 7,801 |
| Operating income | 1,676 | 175 |
| Year-end inventory | 2,794 | 3,136 |

**ST revenue definition:** Net revenues include other revenues (FY2024: 52; FY2025: 46). Net sales alone are lower (FY2024: 13,217; FY2025: 11,754). The dashboard uses net revenues to match the SEC XBRL concept.

## Filing version, provenance and caveats

- Each company-year uses **one filing accession** for all four metrics. FY2024 values are comparative figures from the respective FY2025 audited filing, so the original FY2024 filings are not silently blended with the FY2025 version.
- Repeated historical records in the 201-observation review archive remain intact; this approval set selects a single coherent accession for each company.
- The dashboard's inventory-days indicator uses **year-end inventory / annual cost of revenue × 365**. This is a proxy, **not average-inventory days inventory outstanding**.
- The numbers do not establish actual company-specific supply chain disruption, SKU-level demand or warehouse stock levels.
- Infineon is not included because its official-report observations remain unavailable/unapproved.
- This approval applies only to FY2024–FY2025 annual records. Other years and quarterly/YTD records remain unapproved.
- The independent filing check was performed for this proposed change. **Merging the pull request is the repository owner's publication decision.** The approval fields on the branch are not an instruction to merge without review.

## Reproducibility checks

Run `python -m pytest -q`. Tests verify that all 16 approved observations still match cached SEC evidence, have no duplicate filing-period keys, use one accession per company-year, and load into exactly four annual dashboard rows. Extraction and review scripts do not overwrite the approved dataset.

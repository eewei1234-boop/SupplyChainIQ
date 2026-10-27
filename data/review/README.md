# Annual candidate review

The CSV files in this directory are proposed FY2024/FY2025 observations. They
are not the dashboard's approved dataset. Each row preserves every candidate SEC
accession and source URL for that company, metric and period.

`json_reconciled=true` means the normalized CSV value matches a cached SEC
Company Facts JSON fact. `independently_verified=false` means a reviewer still
needs to open the original filing and check consolidated scope, table, unit,
fiscal period and any amendment/restatement context. Do not copy a row into
`data/approved_financial_observations.csv` until that check is complete.

`Infineon_annual_fy2024_fy2025.csv` is a missing-data checklist, not a financial
dataset. Its values are intentionally blank until official reports are retrieved
and checked. Infineon annual periods end on September 30 and amounts must remain
EUR millions. Segment Result cannot populate the operating-income field.

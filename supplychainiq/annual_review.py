"""Build a human-review table for annual SEC observations.

This module never promotes candidates to the approved dataset. It collects all
filing contexts for a period so an inaccessible filing cannot be silently
replaced by a later amendment or a repeated fact.
"""

from pathlib import Path

import pandas as pd

METRICS = ("revenue", "cost_of_revenue", "operating_income", "inventory")
YEARS = (2024, 2025)


def build_annual_review(observations, *, years=YEARS):
    """Return one candidate row per company/year/metric with all accessions."""
    columns = [
        "company", "fiscal_year", "metric", "value", "currency", "unit",
        "period_start", "period_end", "candidate_accessions", "source_urls",
        "json_reconciled", "independently_verified", "approval_status", "review_note",
    ]
    if observations is None or observations.empty:
        return pd.DataFrame(columns=columns)
    frame = observations.copy()
    frame = frame[frame.fiscal_year.isin(years) & frame.metric.isin(METRICS)].copy()
    annual = frame[frame.period_type == "annual"]
    inventory = frame[(frame.metric == "inventory") & (frame.period_type == "instant")].copy()
    if not inventory.empty:
        # Year-end inventory means the latest instant balance in the fiscal
        # year. Earlier quarter-end balances remain in the source observations.
        inventory["_end"] = pd.to_datetime(inventory.period_end)
        inventory = inventory[inventory["_end"] == inventory.groupby(["company", "fiscal_year"])["_end"].transform("max")]
    frame = pd.concat([annual, inventory], ignore_index=True)
    result = []
    for (company, fiscal_year, metric, period_start, period_end), group in frame.groupby(
        ["company", "fiscal_year", "metric", "period_start", "period_end"], dropna=False, sort=True
    ):
        values = group.value.dropna().unique()
        accessions = sorted(group.accession.dropna().astype(str).unique())
        urls = sorted(group.source_document_url.dropna().astype(str).unique())
        if len(values) != 1:
            status = "conflicting_values_pending_reconciliation"
            note = "Multiple values exist for this period; do not select a filing automatically."
        else:
            status = "pending_human_filing_review"
            note = (
                "Cached SEC JSON facts match; filing page is required to verify consolidated scope, units, "
                "fiscal period and amendment context."
            )
        result.append({
            "company": company,
            "fiscal_year": int(fiscal_year),
            "metric": metric,
            "value": float(values[0]) if len(values) == 1 else None,
            "currency": group.currency.iloc[0],
            "unit": group.unit.iloc[0],
            "period_start": "" if pd.isna(period_start) else period_start,
            "period_end": period_end,
            "candidate_accessions": ";".join(accessions),
            "source_urls": ";".join(urls),
            "json_reconciled": bool((group.reconciliation_status == "source_reconciled_pending_approval").all()),
            "independently_verified": False,
            "approval_status": status,
            "review_note": note,
        })
    return pd.DataFrame(result, columns=columns)


def write_annual_review(observation_csv, output_csv):
    observations = pd.read_csv(observation_csv)
    review = build_annual_review(observations)
    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    review.to_csv(output_csv, index=False)
    return review

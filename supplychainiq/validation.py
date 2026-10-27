"""Strict schema checks; validation does not authenticate a disclosure."""
from urllib.parse import urlparse
import pandas as pd

COMPANIES = ("Infineon Technologies", "onsemi", "STMicroelectronics")
COLUMNS = ["company", "fiscal_year", "period_start", "period_end", "publication_date", "currency", "revenue", "operating_income", "inventory", "cost_of_revenue", "source_url", "source_note", "data_type"]
NUMERIC = ["revenue", "operating_income", "inventory", "cost_of_revenue"]

class DataValidationError(ValueError):
    pass

def validate_data(frame):
    missing = set(COLUMNS) - set(frame.columns)
    if missing:
        raise DataValidationError("Missing columns: " + ", ".join(sorted(missing)))
    df = frame[COLUMNS].copy()
    if df.empty:
        return df
    if df.isna().any().any():
        raise DataValidationError("Every field is required; do not substitute zero for missing data.")
    if not df.company.isin(COMPANIES).all():
        raise DataValidationError("Unsupported company name.")
    if not df.currency.isin(["EUR", "USD"]).all():
        raise DataValidationError("Currency must be EUR or USD; values must be in millions.")
    for col in ["fiscal_year", *NUMERIC]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        if df[col].isna().any() or not df[col].map(lambda x: float('-inf') < x < float('inf')).all():
            raise DataValidationError(f"{col} must contain finite numbers.")
    if ((df.fiscal_year % 1 != 0) | ~df.fiscal_year.between(2000, 2100)).any():
        raise DataValidationError("Fiscal years must be integers between 2000 and 2100.")
    df["fiscal_year"] = df.fiscal_year.astype(int)
    for col in ["revenue", "cost_of_revenue"]:
        if (df[col] <= 0).any():
            raise DataValidationError(f"{col} must be positive.")
    if (df.inventory < 0).any():
        raise DataValidationError("Inventory cannot be negative.")
    expected_currency = df.company.map({"Infineon Technologies": "EUR", "onsemi": "USD", "STMicroelectronics": "USD"})
    if (df.currency != expected_currency).any():
        raise DataValidationError("Inconsistent native currency: Infineon requires EUR; onsemi and ST require USD.")
    dates = pd.to_datetime(df.period_end, format="%Y-%m-%d", errors="coerce")
    if dates.isna().any() or (dates.dt.year != df.fiscal_year).any():
        raise DataValidationError("period_end must be YYYY-MM-DD in the fiscal year.")
    starts = pd.to_datetime(df.period_start, format="%Y-%m-%d", errors="coerce")
    duration = (dates - starts).dt.days + 1
    if starts.isna().any() or not duration.between(350, 380).all():
        raise DataValidationError("Mismatched reporting periods: only full annual periods of 350–380 days are supported.")
    public = df.data_type == "public"
    published = pd.to_datetime(df.loc[public, "publication_date"], format="%Y-%m-%d", errors="coerce")
    if published.isna().any() or (published < dates[public]).any():
        raise DataValidationError("Public publication_date must be an ISO date on or after period_end.")
    if df.duplicated(["company", "fiscal_year"]).any():
        raise DataValidationError("Duplicate company/fiscal year rows.")
    if not df.data_type.isin(["public", "synthetic"]).all():
        raise DataValidationError("data_type must be public or synthetic.")
    for row in df.itertuples():
        if not str(row.source_note).strip():
            raise DataValidationError("Source notes must identify the disclosure and accounting basis.")
        u = urlparse(str(row.source_url))
        if row.data_type == "public" and (u.scheme != "https" or not u.hostname):
            raise DataValidationError("Public rows require an HTTPS disclosure URL.")
    return df.sort_values(["company", "fiscal_year"]).reset_index(drop=True)

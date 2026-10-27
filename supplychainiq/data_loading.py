"""Load local or uploaded CSV data without fetching untrusted URLs."""
from pathlib import Path
import pandas as pd
from .validation import COLUMNS, validate_data, DataValidationError

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

def load_data(source=None, *, demo=False):
    if source is None:
        source = DATA_DIR / ("demo_financials.csv" if demo else "public_financials.csv")
    try:
        frame = pd.read_csv(source)
    except (ValueError, UnicodeError, pd.errors.ParserError) as exc:
        raise DataValidationError(f"Cannot read CSV: {exc}") from exc
    result = validate_data(frame)
    if not demo and (result.data_type == "synthetic").any():
        raise DataValidationError("Synthetic data is permitted only in demo mode.")
    return result


def load_approved_data(source=None):
    """Load only the human-approved observation set into the Phase 1 schema."""
    from .ingestion import annual_dashboard_rows, validate_observations

    source = source or DATA_DIR.parent / "approved_financial_observations.csv"
    source = Path(source)
    if not source.exists() or source.stat().st_size == 0:
        return pd.DataFrame(columns=COLUMNS)
    frame = pd.read_csv(source)
    if frame.empty:
        return pd.DataFrame(columns=COLUMNS)
    required_review = {"review_status", "review_reason"}
    if not required_review.issubset(frame.columns):
        raise DataValidationError("Approved data is missing review metadata.")
    frame = frame[frame.review_status == "approved"].copy()
    if frame.empty:
        return pd.DataFrame(columns=COLUMNS)
    rows = frame.to_dict(orient="records")
    for row in rows:
        for key in ("period_start", "source_url", "source_document_url"):
            if pd.isna(row.get(key)):
                row[key] = ""
        row["value"] = float(row["value"])
        row["fiscal_year"] = int(row["fiscal_year"])
        row["verification_status"] = "reviewed"
    validate_observations(rows)
    result = annual_dashboard_rows(rows)
    if not result.empty:
        result["data_type"] = "public"
    return result


def load_approved_observations(source=None):
    """Return approved observation metadata for source and status display."""
    source = source or DATA_DIR.parent / "approved_financial_observations.csv"
    source = Path(source)
    if not source.exists() or source.stat().st_size == 0:
        return pd.DataFrame()
    frame = pd.read_csv(source)
    if "review_status" not in frame.columns:
        return pd.DataFrame()
    return frame[frame.review_status == "approved"].copy()

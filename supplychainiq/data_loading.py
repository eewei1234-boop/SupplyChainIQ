"""Load local or uploaded CSV data without fetching untrusted URLs."""
from pathlib import Path
import pandas as pd
from .validation import validate_data, DataValidationError

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

"""Review extracted CSVs against cached evidence and write review artifacts.

The command never approves a row automatically. A reviewer may edit a copy of
``review_observations.csv`` after reconciling source documents, set
``review_status=approved`` and include ``approved after source reconciliation``
in ``review_reason``. Run this command again to produce the approved dataset.
"""

from pathlib import Path

import pandas as pd

from supplychainiq.review import APPROVED_FIELDS, REVIEW_FIELDS, approved_observations, review_extracted_directory


def main():
    root = Path(__file__).resolve().parents[1]
    directory = root / "data" / "ingestion"
    review = review_extracted_directory(directory)
    review.to_csv(directory / "review_observations.csv", index=False)
    approved = approved_observations(review)
    approved.to_csv(root / "data" / "approved_financial_observations.csv", index=False, columns=APPROVED_FIELDS)
    status = {
        "input_archive_present": any(
            path.name not in {"review_observations.csv", "approved_financial_observations.csv"}
            for path in directory.glob("*.csv")
        ),
        "observation_count": int(len(review)),
        "source_reconciled_pending_approval": int((review.review_status == "source_reconciled_pending_approval").sum()) if not review.empty else 0,
        "exact_source_matches": int((review.reconciliation_status == "source_reconciled_pending_approval").sum()) if not review.empty else 0,
        "unreconciled": int((review.reconciliation_status == "unreconciled").sum()) if not review.empty else 0,
        "repeated_historical_pending_approval": int((review.review_status == "repeated_historical_pending_approval").sum()) if not review.empty else 0,
        "duplicate_period_unresolved": int((review.review_status == "duplicate_period_unresolved").sum()) if not review.empty else 0,
        "approved_count": int(len(approved)),
        "note": (
            "No observations are approved automatically; review duplicates and filing context before approval."
            if len(review)
            else "No observations are approved automatically. Missing ZIP/CSV evidence remains empty."
        ),
    }
    pd.Series(status).to_json(directory / "review_summary.json", indent=2)
    print(pd.Series(status).to_string())


if __name__ == "__main__":
    main()

"""Create the FY2024/FY2025 candidate table without approving values."""

from pathlib import Path

import pandas as pd

from supplychainiq.annual_review import build_annual_review


def main():
    root = Path(__file__).resolve().parents[1]
    outputs = []
    source = root / "data" / "ingestion" / "review_observations.csv"
    if source.exists():
        observations = pd.read_csv(source)
    else:
        observations = pd.DataFrame()
    for company in ("onsemi", "STMicroelectronics"):
        output = root / "data" / "review" / f"{company}_annual_fy2024_fy2025.csv"
        company_observations = observations[observations.company == company] if not observations.empty else observations
        if not company_observations.empty:
            review = build_annual_review(company_observations)
            output.parent.mkdir(parents=True, exist_ok=True)
            review.to_csv(output, index=False)
            outputs.append(f"{company}: {len(review)} proposed rows written to {output}")
        else:
            outputs.append(f"{company}: source CSV unavailable")
    print("\n".join(outputs))


if __name__ == "__main__":
    main()

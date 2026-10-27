"""Metrics retain native currency and distinguish GAAP operating margin."""
import pandas as pd

def analyze(frame):
    df = frame.sort_values(["company", "fiscal_year"]).copy()
    df["gross_margin_pct"] = (df.revenue - df.cost_of_revenue) / df.revenue * 100
    df["operating_margin_pct"] = df.operating_income / df.revenue * 100
    df["inventory_to_revenue_pct"] = df.inventory / df.revenue * 100
    # A year-end proxy, not average-inventory DIO or an audited risk score.
    df["inventory_days_proxy"] = df.inventory / df.cost_of_revenue * 365
    groups = df.groupby("company")
    previous_revenue = groups.revenue.shift()
    comparable = (df.fiscal_year - groups.fiscal_year.shift() == 1) & (df.currency == groups.currency.shift())
    df["revenue_growth_pct"] = ((df.revenue / previous_revenue - 1) * 100).where(comparable)
    return df

"""Deterministic, explainable supply-chain risk screening rules.

These rules identify financial warning signals for research and planning
conversation. They do not establish an operational disruption, root cause or
forecast. All changes require consecutive comparable annual periods.
"""

from dataclasses import dataclass

import pandas as pd

from .analysis import analyze


@dataclass(frozen=True)
class RiskConfig:
    revenue_decline_moderate_pct: float = -5.0
    revenue_decline_elevated_pct: float = -15.0
    inventory_growth_moderate_pct: float = 5.0
    inventory_growth_elevated_pct: float = 15.0
    inventory_mix_moderate_pp: float = 3.0
    inventory_mix_elevated_pp: float = 8.0
    gross_margin_decline_moderate_pp: float = -2.0
    gross_margin_decline_elevated_pp: float = -5.0
    operating_margin_decline_moderate_pp: float = -3.0
    operating_margin_decline_elevated_pp: float = -8.0


LEVEL_ORDER = {"Low": 0, "Moderate": 1, "Elevated": 2}


def _severity(value, moderate, elevated, direction="lower"):
    if pd.isna(value):
        return None
    if direction == "lower":
        if value <= elevated:
            return "Elevated"
        if value <= moderate:
            return "Moderate"
    else:
        if value >= elevated:
            return "Elevated"
        if value >= moderate:
            return "Moderate"
    return None


def _recommendation(signal_type):
    return {
        "Demand": "Demand planner: validate bookings and demand assumptions, then run a downside scenario before changing the plan.",
        "Inventory": "Supply planner: review inventory targets, open orders and lead times; consider rebalancing or deferring supply commitments.",
        "Profitability": "Demand and supply planners: review product mix, cost and capacity assumptions before using margin movement in a plan.",
    }[signal_type]


def screen_risk(frame, config=None):
    """Return signal-level and company-period screening tables.

    ``frame`` should contain approved annual records or clearly labelled demo
    records. The function never fills missing history and never crosses a
    fiscal-year gap or currency change.
    """
    config = config or RiskConfig()
    metrics = analyze(frame)
    signal_rows = []
    summary_rows = []
    for company, group in metrics.groupby("company", sort=True):
        group = group.sort_values("fiscal_year").reset_index(drop=True)
        previous = None
        for row in group.itertuples(index=False):
            current = row._asdict()
            comparable = previous is not None and row.fiscal_year - previous["fiscal_year"] == 1 and row.currency == previous["currency"]
            changes = {
                "revenue_growth_pct": row.revenue_growth_pct if comparable else None,
                "inventory_growth_pct": ((row.inventory / previous["inventory"] - 1) * 100) if comparable and previous["inventory"] > 0 else None,
                "inventory_mix_change_pp": (row.inventory_to_revenue_pct - previous["inventory_to_revenue_pct"]) if comparable else None,
                "gross_margin_change_pp": (row.gross_margin_pct - previous["gross_margin_pct"]) if comparable else None,
                "operating_margin_change_pp": (row.operating_margin_pct - previous["operating_margin_pct"]) if comparable else None,
            }
            signals = []

            def add(signal_type, metric, change, level, explanation, threshold):
                if level:
                    signals.append(level)
                    signal_rows.append({
                        "company": company,
                        "fiscal_year": row.fiscal_year,
                        "period_end": row.period_end,
                        "source_url": getattr(row, "source_url", ""),
                        "signal_type": signal_type,
                        "metric": metric,
                        "observed_change": change,
                        "threshold": threshold,
                        "risk_level": level,
                        "explanation": explanation,
                        "recommendation": _recommendation(signal_type),
                    })

            revenue = changes["revenue_growth_pct"]
            revenue_level = _severity(revenue, config.revenue_decline_moderate_pct, config.revenue_decline_elevated_pct)
            add("Demand", "revenue_growth_pct", revenue, revenue_level,
                f"Revenue decreased {abs(revenue):.1f}% year over year." if revenue is not None else "",
                config.revenue_decline_moderate_pct)

            inventory_growth = changes["inventory_growth_pct"]
            inventory_level = _severity(inventory_growth, config.inventory_growth_moderate_pct, config.inventory_growth_elevated_pct, "higher")
            add("Inventory", "inventory_growth_pct", inventory_growth, inventory_level,
                f"Year-end inventory increased {inventory_growth:.1f}% year over year." if inventory_growth is not None else "",
                config.inventory_growth_moderate_pct)

            inventory_mix = changes["inventory_mix_change_pp"]
            mix_level = _severity(inventory_mix, config.inventory_mix_moderate_pp, config.inventory_mix_elevated_pp, "higher")
            add("Inventory", "inventory_to_revenue_change_pp", inventory_mix, mix_level,
                f"Inventory as a share of revenue increased {inventory_mix:.1f} percentage points." if inventory_mix is not None else "",
                config.inventory_mix_moderate_pp)

            gross = changes["gross_margin_change_pp"]
            gross_level = _severity(gross, config.gross_margin_decline_moderate_pp, config.gross_margin_decline_elevated_pp)
            add("Profitability", "gross_margin_change_pp", gross, gross_level,
                f"Gross margin decreased {abs(gross):.1f} percentage points." if gross is not None else "",
                config.gross_margin_decline_moderate_pp)

            operating = changes["operating_margin_change_pp"]
            operating_level = _severity(operating, config.operating_margin_decline_moderate_pp, config.operating_margin_decline_elevated_pp)
            add("Profitability", "operating_margin_change_pp", operating, operating_level,
                f"Operating margin decreased {abs(operating):.1f} percentage points." if operating is not None else "",
                config.operating_margin_decline_moderate_pp)

            if comparable and inventory_growth is not None and revenue is not None and inventory_growth >= config.inventory_growth_moderate_pct and revenue <= config.revenue_decline_moderate_pct:
                combo_level = "Elevated" if inventory_growth >= config.inventory_growth_elevated_pct or revenue <= config.revenue_decline_elevated_pct else "Moderate"
                add("Inventory", "inventory_growth_pct_vs_revenue_growth_pct", inventory_growth, combo_level,
                    f"Inventory increased {inventory_growth:.1f}% while revenue declined {abs(revenue):.1f}% year over year.", config.inventory_growth_moderate_pct)

            if signals:
                level = max(signals, key=lambda item: LEVEL_ORDER[item])
                explanation = f"{len(signals)} rule-based signal(s) triggered; highest screening level is {level}."
            elif comparable:
                level = "Low"
                explanation = "No configured warning thresholds were crossed."
            else:
                level = "Low"
                explanation = "No consecutive comparable prior fiscal year is available; change-based screening is unavailable."
            summary_rows.append({
                "company": company,
                "fiscal_year": row.fiscal_year,
                "period_end": row.period_end,
                "comparison_status": "comparable_yoy" if comparable else "insufficient_history",
                "risk_level": level,
                "signal_count": len(signals),
                "explanation": explanation,
                "screening_note": "Screening indicator only; not confirmation of an operational disruption.",
            })
            previous = current
    signal_columns = ["company", "fiscal_year", "period_end", "source_url", "signal_type", "metric", "observed_change", "threshold", "risk_level", "explanation", "recommendation"]
    summary_columns = ["company", "fiscal_year", "period_end", "comparison_status", "risk_level", "signal_count", "explanation", "screening_note"]
    return pd.DataFrame(signal_rows, columns=signal_columns), pd.DataFrame(summary_rows, columns=summary_columns), metrics

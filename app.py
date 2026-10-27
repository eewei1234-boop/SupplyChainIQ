"""Run with: streamlit run app.py"""
import plotly.express as px
import pandas as pd
import streamlit as st
from supplychainiq.data_loading import load_approved_data, load_data
from supplychainiq.validation import DataValidationError, COMPANIES
from supplychainiq.analysis import analyze
from supplychainiq.review import freshness_status
from supplychainiq.risk import RiskConfig, screen_risk

st.set_page_config(page_title="SupplyChainIQ", page_icon="📊", layout="wide")
st.title("SupplyChainIQ")
st.markdown("**Semiconductor market intelligence** · Infineon Technologies case study with peer comparisons")
st.caption("Phase 1 · Semiconductor financial and inventory intelligence")
demo = st.sidebar.toggle("Use synthetic demonstration data", value=False)
st.sidebar.caption("Demo figures are invented examples, never company disclosures.")
upload = st.sidebar.file_uploader("Import sourced financial CSV", type="csv", disabled=demo)
if demo:
    st.warning("SYNTHETIC DEMO — All figures below are fictional and must not be used as company financial data.")
else:
    st.info("Real-data mode. Only human-approved observations are shown. Uploading a CSV validates its structure but does not verify its financial accuracy.")
try:
    if demo:
        raw = load_data(demo=True)
    elif upload is not None:
        raw = load_data(upload)
    else:
        raw = load_approved_data()
except (DataValidationError, OSError) as exc:
    st.error(str(exc))
    st.stop()
with st.expander("Data sources and comparison rules", expanded=raw.empty):
    st.markdown("""Use annual company disclosures. Enter amounts in **millions of native currency**, with reported operating income rather than adjusted segment profit. Infineon's fiscal year normally ends in September; onsemi and ST use calendar or near-calendar years. Fiscal-year labels therefore cover different periods.

Revenue is charted separately by currency, without currency conversion. Margins permit a directional comparison but accounting bases and business mix differ. Inventory days = year-end inventory ÷ annual cost of revenue × 365. This is a **proxy**, not average-inventory DIO or a prediction of supply disruption.

Official source starting points: [Infineon](https://www.infineon.com/about/investor/reports-and-presentations), [onsemi](https://investors.onsemi.com/financials/annual-reports-and-proxy), [STMicroelectronics](https://investors.st.com/financial-information/annual-and-semi-annual-reports). Verify exact disclosure URLs, periods, units, and notes before importing.""")
    st.download_button("Download CSV template", load_data().to_csv(index=False), "financial_template.csv", "text/csv")
with st.expander("Phase 2 · Ingestion evidence and availability"):
    import json
    from pathlib import Path
    evidence_dir = Path(__file__).resolve().parent / "data" / "ingestion"
    status_file = evidence_dir / "refresh_status.json"
    freshness = freshness_status(status_file)
    if freshness.get("attempted_at"):
        st.caption(f"Last extraction attempt: {freshness['attempted_at']} · {freshness['message']}")
    else:
        st.caption(freshness["message"])
    st.caption("Extracted observations show source reconciliation separately from approval. They do not automatically enter the annual comparison. Quarterly and year-to-date records remain separate.")
    if status_file.exists():
        st.json(json.loads(status_file.read_text()))
    for observation_file in sorted(evidence_dir.glob("*.csv")):
        if observation_file.name == "review_observations.csv":
            continue
        observations = pd.read_csv(observation_file)
        st.write(observation_file.stem)
        st.dataframe(observations, hide_index=True)
        st.download_button(f"Download {observation_file.stem} observations", observations.to_csv(index=False), observation_file.name)
if raw.empty:
    st.warning("No verified or approved real financial figures are available. Infineon is awaiting official-report verification; onsemi and ST observations have matched SEC evidence but still require human approval. Upload a sourced annual CSV or enable synthetic demonstration data in the sidebar.")
    availability = pd.DataFrame({"Company": list(COMPANIES), "Dashboard status": ["Awaiting official-report verification", "Source reconciled; approval pending", "Source reconciled; approval pending"]})
    st.dataframe(availability, hide_index=True, width="stretch")
    st.stop()

if not demo:
    dashboard_status = []
    for company in COMPANIES:
        if company == "Infineon Technologies":
            status = "Awaiting official-report verification"
        elif company in set(raw.company):
            status = "Approved and available"
        else:
            status = "Pending source reconciliation"
        dashboard_status.append({"Company": company, "Dashboard status": status})
    with st.expander("Company data availability"):
        st.dataframe(pd.DataFrame(dashboard_status), hide_index=True, width="stretch")

with st.sidebar.expander("Risk screening thresholds", expanded=False):
    st.caption("Rules screen financial warning signals; they do not confirm an operational disruption.")
    revenue_decline_moderate = st.number_input("Revenue decline: moderate (%)", value=-5.0, step=1.0)
    revenue_decline_elevated = st.number_input("Revenue decline: elevated (%)", value=-15.0, step=1.0)
    inventory_growth_moderate = st.number_input("Inventory growth: moderate (%)", value=5.0, step=1.0)
    inventory_growth_elevated = st.number_input("Inventory growth: elevated (%)", value=15.0, step=1.0)
    inventory_mix_moderate = st.number_input("Inventory/revenue increase: moderate (pp)", value=3.0, step=1.0)
    inventory_mix_elevated = st.number_input("Inventory/revenue increase: elevated (pp)", value=8.0, step=1.0)
    gross_margin_moderate = st.number_input("Gross margin decline: moderate (pp)", value=-2.0, step=1.0)
    gross_margin_elevated = st.number_input("Gross margin decline: elevated (pp)", value=-5.0, step=1.0)
    operating_margin_moderate = st.number_input("Operating margin decline: moderate (pp)", value=-3.0, step=1.0)
    operating_margin_elevated = st.number_input("Operating margin decline: elevated (pp)", value=-8.0, step=1.0)
try:
    config = RiskConfig(
        revenue_decline_moderate_pct=revenue_decline_moderate,
        revenue_decline_elevated_pct=revenue_decline_elevated,
        inventory_growth_moderate_pct=inventory_growth_moderate,
        inventory_growth_elevated_pct=inventory_growth_elevated,
        inventory_mix_moderate_pp=inventory_mix_moderate,
        inventory_mix_elevated_pp=inventory_mix_elevated,
        gross_margin_decline_moderate_pp=gross_margin_moderate,
        gross_margin_decline_elevated_pp=gross_margin_elevated,
        operating_margin_decline_moderate_pp=operating_margin_moderate,
        operating_margin_decline_elevated_pp=operating_margin_elevated,
    )
except ValueError as exc:
    st.sidebar.warning(f"Invalid screening thresholds: {exc} Using the default thresholds.")
    config = RiskConfig()
companies = st.sidebar.multiselect("Companies", COMPANIES, default=list(COMPANIES))
years = sorted(raw.fiscal_year.unique().tolist())
selected_years = st.sidebar.multiselect("Fiscal years", years, default=years)
# Calculate growth before filtering so a selected year retains its prior-year comparison.
risk_signals, risk_summary, analyzed = screen_risk(raw, config)
df = analyzed
df = df[df.company.isin(companies) & df.fiscal_year.isin(selected_years)]
if df.empty:
    st.info("Select at least one company and an available fiscal year.")
    st.stop()
latest = df.sort_values("fiscal_year").groupby("company").tail(1)
cols = st.columns(len(latest))
for col, row in zip(cols, latest.itertuples()):
    col.metric(row.company, f"{row.operating_margin_pct:.1f}%", help=f"Reported operating margin, FY{row.fiscal_year}; period ends {row.period_end}")
metric = st.selectbox("Compare metric", ["gross_margin_pct", "operating_margin_pct", "inventory_days_proxy", "inventory_to_revenue_pct", "revenue_growth_pct", "revenue", "inventory"], format_func=lambda s: s.replace("_", " ").title())
labels = {"fiscal_year": "Fiscal year", "company": "Company", metric: metric.replace("_", " ").title()}
if metric in ["revenue", "inventory"]:
    labels[metric] = metric.title() + " (millions of native currency)"
    chart = px.line(df, x="fiscal_year", y=metric, color="company", facet_col="currency", markers=True, labels=labels)
else:
    chart = px.line(df, x="fiscal_year", y=metric, color="company", markers=True, labels=labels)
st.plotly_chart(chart, width="stretch")
st.subheader("Revenue by native currency")
st.plotly_chart(px.bar(df, x="fiscal_year", y="revenue", color="company", barmode="group", facet_col="currency", labels={"revenue": "Revenue (millions)", "fiscal_year": "Fiscal year"}), width="stretch")
st.subheader("Company comparison")
st.caption("Latest selected fiscal year per company; check period ends before comparing.")
st.dataframe(latest[["company", "fiscal_year", "period_end", "currency", "revenue", "inventory", "gross_margin_pct", "revenue_growth_pct"]], hide_index=True, width="stretch")

st.header("Phase 3 · Supply Chain Risk Intelligence")
st.caption("Deterministic financial screening for planning conversations. Low, Moderate and Elevated levels are warning indicators, not confirmed operational disruptions.")
selected_risk = risk_summary[risk_summary.company.isin(companies) & risk_summary.fiscal_year.isin(selected_years)].copy()
selected_signals = risk_signals[risk_signals.company.isin(companies) & risk_signals.fiscal_year.isin(selected_years)].copy()
if selected_risk.empty:
    st.info("No comparable annual risk periods are available for the selected filters.")
else:
    level_values = {"Not assessed": -1, "Low": 0, "Moderate": 1, "Elevated": 2}
    chart_data = selected_risk.copy()
    chart_data["risk_score"] = chart_data.risk_level.map(level_values)
    st.plotly_chart(px.bar(chart_data, x="fiscal_year", y="risk_score", color="risk_level", facet_col="company", range_y=[-1, 2], labels={"risk_score": "Screening level (-1 Not assessed · 0 Low · 2 Elevated)"}), width="stretch")
    st.subheader("Risk screening by company and year")
    st.dataframe(selected_risk, hide_index=True, width="stretch")
    if selected_signals.empty:
        st.success("No configured financial warning rules were triggered for the selected periods.")
    else:
        st.subheader("Triggered warning signals and recommendations")
        st.dataframe(selected_signals, hide_index=True, width="stretch")
        st.download_button("Download risk signals", selected_signals.to_csv(index=False), "supplychainiq_risk_signals.csv", "text/csv")
st.subheader("Source references")
if demo:
    st.caption("Synthetic records have no original financial report or publication date.")
    source_status = "synthetic_demo"
elif upload is not None:
    st.caption("Uploaded records are structurally validated but remain user-supplied and unverified.")
    source_status = "user_supplied_pending_verification"
else:
    st.caption("Every row in this view comes from the approved observation set. Approval requires source reconciliation and human review.")
    source_status = "approved_after_source_reconciliation"
source_references = df[["company", "fiscal_year", "period_start", "period_end", "publication_date", "source_url", "source_note", "data_type"]].copy()
source_references["verification_status"] = source_status
st.dataframe(source_references, hide_index=True, width="stretch")
st.subheader("Financial records and source notes")
st.dataframe(df, hide_index=True, width="stretch")
st.download_button("Download filtered analysis", df.to_csv(index=False), "supplychainiq_analysis.csv", "text/csv")
st.caption("Research and learning tool. Ratios are descriptive; they do not establish supply chain risk or investment recommendations.")

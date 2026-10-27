"""Run with: streamlit run app.py"""
import plotly.express as px
import streamlit as st
from supplychainiq.data_loading import load_data
from supplychainiq.validation import DataValidationError, COMPANIES
from supplychainiq.analysis import analyze

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
    st.info("Public-data mode. Imported figures are user supplied; schema validation does not verify their accuracy.")
try:
    raw = load_data(upload, demo=demo)
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
    import pandas as pd
    evidence_dir = Path(__file__).resolve().parent / "data" / "ingestion"
    status_file = evidence_dir / "refresh_status.json"
    st.caption("Extracted observations are pending review. They do not automatically enter the annual comparison. Quarterly and year-to-date records remain separate.")
    if status_file.exists():
        st.json(json.loads(status_file.read_text()))
    for observation_file in sorted(evidence_dir.glob("*.csv")):
        observations = pd.read_csv(observation_file)
        st.write(observation_file.stem)
        st.dataframe(observations, hide_index=True)
        st.download_button(f"Download {observation_file.stem} observations", observations.to_csv(index=False), observation_file.name)
if raw.empty:
    st.warning("No verified public financial figures are bundled. Company websites were inaccessible during setup. Upload a sourced CSV or enable synthetic demonstration data in the sidebar.")
    st.stop()
companies = st.sidebar.multiselect("Companies", COMPANIES, default=list(COMPANIES))
years = sorted(raw.fiscal_year.unique().tolist())
selected_years = st.sidebar.multiselect("Fiscal years", years, default=years)
# Calculate growth before filtering so a selected year retains its prior-year comparison.
df = analyze(raw)
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
st.subheader("Source references")
if demo:
    st.caption("Synthetic records have no original financial report or publication date.")
st.dataframe(df[["company", "fiscal_year", "period_start", "period_end", "publication_date", "source_url", "source_note", "data_type"]], hide_index=True, width="stretch")
st.subheader("Financial records and source notes")
st.dataframe(df, hide_index=True, width="stretch")
st.download_button("Download filtered analysis", df.to_csv(index=False), "supplychainiq_analysis.csv", "text/csv")
st.caption("Research and learning tool. Ratios are descriptive; they do not establish supply chain risk or investment recommendations.")

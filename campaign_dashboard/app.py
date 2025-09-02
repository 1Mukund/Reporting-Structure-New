# app.py

import streamlit as st
import pandas as pd
import gspread
import re
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- Setup ---
st.set_page_config(page_title="Campaign Dashboard", layout="wide")
st.title("📊 Automated Campaign Dashboard")

# --- Google Sheets Auth ---
@st.cache_resource
def load_sheet(sheet_url):
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']

    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        dict(st.secrets["google_service_account"]), scope)
    client = gspread.authorize(creds)

    sheet_id = re.findall(r"/d/([a-zA-Z0-9-_]+)", sheet_url)[0]
    return client.open_by_key(sheet_id)

# --- Data Fetch ---
@st.cache_data
def fetch_data():
    try:
        sheet = load_sheet(st.secrets["GOOGLE_SHEET_URL"])
        churn_df = pd.DataFrame(sheet.worksheet("Daily report - Churn").get_all_records())
        cs_df = pd.DataFrame(sheet.worksheet("CS").get_all_records())
        node_def = pd.DataFrame(sheet.worksheet("Node_def").get_all_records())
        cta_def = pd.DataFrame(sheet.worksheet("CTA_Def").get_all_records())

        return churn_df, cs_df, node_def, cta_def
    except Exception as e:
        st.error(f"❌ Failed to load data:\n\n{e}")
        st.stop()

# --- Preprocessing & Summary ---
def prepare_summary(churn_df, cs_df):
    churn_df.columns = churn_df.columns.str.strip()
    cs_df.columns = cs_df.columns.str.strip()

    # Rename for consistent merge key
    if "Campaign ID" in churn_df.columns:
        churn_df.rename(columns={"Campaign ID": "Camp_ID"}, inplace=True)

    if "Project" in churn_df.columns and "Project Name" not in churn_df.columns:
        churn_df.rename(columns={"Project": "Project Name"}, inplace=True)

    # Ensure merge columns exist
    if "Camp_ID" not in churn_df.columns or "Camp_ID" not in cs_df.columns:
        st.error("❌ 'Camp_ID' column missing in one of the sheets.")
        st.write("Churn columns:", list(churn_df.columns))
        st.write("CS columns:", list(cs_df.columns))
        st.stop()

    df = churn_df.merge(cs_df, on="Camp_ID", how="left")

    # Handle date column
    date_col = "Date"
    if "Date" not in df.columns:
        possible_dates = [col for col in df.columns if "Date" in col]
        if possible_dates:
            df.rename(columns={possible_dates[0]: "Date"}, inplace=True)
        else:
            st.error("❌ 'Date' column not found after merge.")
            st.write("Merged Columns:", list(df.columns))
            st.stop()

    df['Date'] = pd.to_datetime(df['Date'], errors="coerce")

    # Required groupby columns
    group_cols = ["Date", "Camp_ID", "Project Name", "Audience_ID", "Objectives"]
    missing = [col for col in group_cols if col not in df.columns]
    if missing:
        st.error(f"❌ Missing columns for summary: {missing}")
        st.write("Available columns:", list(df.columns))
        st.stop()

    agg_dict = {
        "Sent": "sum",
        "Delivered": "sum",
        "Read": "sum",
        "Lead Count": "sum"
    }

    summary = df.groupby(group_cols).agg(agg_dict).reset_index()

    if "Replied" in df.columns:
        reply_counts = df.groupby(group_cols)["Replied"].sum().reset_index()["Replied"]
        summary["Replied"] = reply_counts
        summary["Reply %"] = (summary["Replied"] / summary["Sent"] * 100).round(2)

    summary["Delivery %"] = (summary["Delivered"] / summary["Sent"] * 100).round(2)
    return summary

# --- Load & Process ---
with st.spinner("Loading data..."):
    churn_df, cs_df, node_def, cta_def = fetch_data()
    summary_df = prepare_summary(churn_df, cs_df)

# --- Sidebar Filters ---
st.sidebar.header("🔍 Filters")

# Optional Date Range Filter
use_date_filter = st.sidebar.checkbox("Enable Date Range Filter")
if use_date_filter:
    date_range = st.sidebar.date_input("Select Date Range", value=(datetime.today(), datetime.today()))
else:
    date_range = None

filtered_df = summary_df.copy()

# Apply date range filter
if date_range and len(date_range) == 2:
    start_date, end_date = date_range
    filtered_df = filtered_df[
        (filtered_df['Date'].dt.date >= start_date) &
        (filtered_df['Date'].dt.date <= end_date)
    ]

# Campaign/Project Filters after date
campaign_filter = st.sidebar.multiselect("Campaign ID", options=filtered_df["Camp_ID"].unique())
project_filter = st.sidebar.multiselect("Project Name", options=filtered_df["Project Name"].unique())

if campaign_filter:
    filtered_df = filtered_df[filtered_df["Camp_ID"].isin(campaign_filter)]
if project_filter:
    filtered_df = filtered_df[filtered_df["Project Name"].isin(project_filter)]

# --- Output ---
st.subheader("📋 Filtered Campaign Summary")
st.dataframe(filtered_df, use_container_width=True)

st.subheader("📈 KPIs")
kpi_chart = (
    filtered_df.set_index("Camp_ID")[["Reply %", "Delivery %"]]
    if "Reply %" in filtered_df
    else filtered_df.set_index("Camp_ID")[["Delivery %"]]
)
if not kpi_chart.empty:
    st.bar_chart(kpi_chart)
else:
    st.info("No KPI data for selected filters.")

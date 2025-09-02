# app.py

import streamlit as st
import pandas as pd
import gspread
import re
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ------------------ Streamlit Setup ------------------
st.set_page_config(page_title="Campaign Dashboard", layout="wide")
st.title("📊 Automated Campaign Dashboard")

# ------------------ Google Sheets Auth ------------------
@st.cache_resource
def load_sheet(sheet_url):
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        dict(st.secrets["google_service_account"]), scope)
    client = gspread.authorize(creds)

    sheet_id = re.findall(r"/d/([a-zA-Z0-9-_]+)", sheet_url)[0]
    return client.open_by_key(sheet_id)

# ------------------ Fetch Data ------------------
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

# ------------------ Prepare Summary ------------------
def prepare_summary(churn_df, cs_df):
    churn_df.columns = churn_df.columns.str.strip()
    cs_df.columns = cs_df.columns.str.strip()

    # Fix merge key
    if "Campaign ID" in churn_df.columns:
        churn_df.rename(columns={"Campaign ID": "Camp_ID"}, inplace=True)
    if "Project" in churn_df.columns and "Project Name" not in churn_df.columns:
        churn_df.rename(columns={"Project": "Project Name"}, inplace=True)

    df = churn_df.merge(cs_df, on="Camp_ID", how="left")

    # Fix merged columns
    if "Date_x" in df.columns:
        df.rename(columns={"Date_x": "Date"}, inplace=True)
    elif "Date" not in df.columns:
        st.error("❌ 'Date' column not found after merge.")
        st.dataframe(df.columns.tolist())
        st.stop()

    if "Project Name_x" in df.columns:
        df.rename(columns={"Project Name_x": "Project Name"}, inplace=True)

    df['Date'] = pd.to_datetime(df['Date'], errors="coerce")

    group_cols = ["Date", "Camp_ID", "Project Name"]
    if "Audience_ID" in df.columns:
        group_cols.append("Audience_ID")
    if "Objectives" in df.columns:
        group_cols.append("Objectives")

    agg_dict = {
        "Sent": "sum",
        "Delivered": "sum",
        "Read": "sum"
    }
    if "Lead Count" in df.columns:
        agg_dict["Lead Count"] = "sum"
    if "Replied" in df.columns:
        agg_dict["Replied"] = "sum"

    summary = df.groupby(group_cols).agg(agg_dict).reset_index()

    if "Replied" in summary.columns:
        summary["Reply %"] = (summary["Replied"] / summary["Sent"] * 100).round(2)
    summary["Delivery %"] = (summary["Delivered"] / summary["Sent"] * 100).round(2)

    return summary

# ------------------ Load & Process ------------------
with st.spinner("📦 Loading and processing data..."):
    churn_df, cs_df, node_def, cta_def = fetch_data()
    summary_df = prepare_summary(churn_df, cs_df)

# ------------------ Sidebar Filters ------------------
st.sidebar.header("🔍 Filters")
date_filter = st.sidebar.date_input("Filter by Date", value=datetime.today())
campaign_filter = st.sidebar.multiselect("Filter by Campaign ID", options=summary_df["Camp_ID"].unique())
project_filter = st.sidebar.multiselect("Filter by Project", options=summary_df["Project Name"].unique())

# ------------------ Apply Filters ------------------
filtered_df = summary_df.copy()
if date_filter:
    filtered_df = filtered_df[filtered_df['Date'].dt.date == date_filter]
if campaign_filter:
    filtered_df = filtered_df[filtered_df['Camp_ID'].isin(campaign_filter)]
if project_filter:
    filtered_df = filtered_df[filtered_df['Project Name'].isin(project_filter)]

# ------------------ Display Output ------------------
st.subheader("📋 Filtered Campaign Summary")
st.dataframe(filtered_df, use_container_width=True)

st.subheader("📈 KPI Chart")
if "Reply %" in filtered_df.columns:
    kpi_chart = filtered_df.set_index("Camp_ID")[["Reply %", "Delivery %"]]
else:
    kpi_chart = filtered_df.set_index("Camp_ID")[["Delivery %"]]

if not kpi_chart.empty:
    st.bar_chart(kpi_chart)
else:
    st.info("No data available for selected filters.")

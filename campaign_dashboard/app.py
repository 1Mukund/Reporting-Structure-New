# campaign_dashboard/app.py

import pandas as pd
import streamlit as st
import gspread
import json
import re
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- Google Sheets Auth ---
@st.cache_resource
def load_sheet(sheet_url):
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']

    # Load from [google_service_account] directly from secrets.toml
    key_dict = dict(st.secrets["google_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)

    client = gspread.authorize(creds)

    # Extract Sheet ID from URL and load
    sheet_id = re.findall(r"/d/([a-zA-Z0-9-_]+)", sheet_url)[0]
    sheet = client.open_by_key(sheet_id)
    return sheet

# --- Fetch Data ---
def fetch_data():
    sheet_url = st.secrets["GOOGLE_SHEET_URL"]
    sheet = load_sheet(sheet_url)
    churn_df = pd.DataFrame(sheet.worksheet("Daily report - Churn").get_all_records())
    cs_df = pd.DataFrame(sheet.worksheet("CS").get_all_records())
    node_def = pd.DataFrame(sheet.worksheet("Node_def").get_all_records())
    cta_def = pd.DataFrame(sheet.worksheet("CTA_Def").get_all_records())
    return churn_df, cs_df, node_def, cta_def

# --- Process Data ---
def prepare_summary(churn_df, cs_df):
    # Strip column spaces
    churn_df.columns = churn_df.columns.str.strip()
    cs_df.columns = cs_df.columns.str.strip()

    # Rename mismatched columns
    if "Campaign ID" in churn_df.columns:
        churn_df.rename(columns={"Campaign ID": "Camp_ID"}, inplace=True)

    # Debug outputs
    st.write("Churn DF columns:", churn_df.columns.tolist())
    st.write("CS DF columns:", cs_df.columns.tolist())

    # Merge and compute summary
    df = churn_df.merge(cs_df, on="Camp_ID", how="left")
    df['Date'] = pd.to_datetime(df['Date'])

    summary = df.groupby(["Date", "Camp_ID", "Project Name", "Audience_ID", "Objectives"]).agg({
        "Sent": "sum",
        "Delivered": "sum",
        "Read": "sum",
        "Replied": "sum" if "Replied" in df.columns else "Read",  # fallback
        "Lead Count": "sum"
    }).reset_index()

    summary["Reply %"] = (summary["Replied"] / summary["Sent"] * 100).round(2)
    summary["Delivery %"] = (summary["Delivered"] / summary["Sent"] * 100).round(2)
    return summary



# --- Streamlit UI ---
st.set_page_config(page_title="Campaign LMS Dashboard", layout="wide")
st.title("📊 Automated Campaign Dashboard")

with st.spinner("Fetching and preparing data..."):
    churn_df, cs_df, node_def, cta_def = fetch_data()
    summary_df = prepare_summary(churn_df, cs_df)

# --- Sidebar Filters ---
st.sidebar.header("Filters")
date_filter = st.sidebar.date_input("Filter by Date", value=datetime.today())
campaign_filter = st.sidebar.multiselect("Filter by Campaign ID", options=summary_df["Camp_ID"].unique())
project_filter = st.sidebar.multiselect("Filter by Project", options=summary_df["Project Name"].unique())

# --- Apply Filters ---
filtered_df = summary_df.copy()
if date_filter:
    filtered_df = filtered_df[filtered_df['Date'].dt.date == date_filter]
if campaign_filter:
    filtered_df = filtered_df[filtered_df['Camp_ID'].isin(campaign_filter)]
if project_filter:
    filtered_df = filtered_df[filtered_df['Project Name'].isin(project_filter)]

# --- Display Output ---
st.subheader("📅 Campaign Summary Table")
st.dataframe(filtered_df, use_container_width=True)

# --- KPI Charts ---
st.subheader("📊 KPI Visualizations")
kpi_chart = filtered_df.set_index("Camp_ID")[["Reply %", "Delivery %"]]
if not kpi_chart.empty:
    st.bar_chart(kpi_chart)
else:
    st.info("No data available for selected filters.")

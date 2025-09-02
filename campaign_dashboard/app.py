# campaign_dashboard/app.py

import pandas as pd
import streamlit as st
import gspread
import json
import base64
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- Google Sheets Auth ---
@st.cache_resource
def load_sheet(sheet_url):
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']

    # Load key from secret instead of file
    base64_key = st.secrets["GOOGLE_SERVICE_ACCOUNT"]
    key_dict = json.loads(base64.b64decode(base64_key).decode("utf-8"))
    creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)

    client = gspread.authorize(creds)
    sheet = client.open_by_url(sheet_url)
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
    df = churn_df.merge(cs_df, left_on="Camp_ID", right_on="Camp_ID", how="left")
    df['Date'] = pd.to_datetime(df['Date'])
    summary = df.groupby(["Date", "Camp_ID", "Project Name", "Audience_ID", "Objectives"]).agg({
        "Sent": "sum",
        "Delivered": "sum",
        "Read": "sum",
        "Replied": "sum",
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

# --- Filters ---
st.sidebar.header("Filters")
date_filter = st.sidebar.date_input("Date", value=datetime.today())
campaign_filter = st.sidebar.multiselect("Campaign ID", options=summary_df["Camp_ID"].unique())

filtered_df = summary_df.copy()
if date_filter:
    filtered_df = filtered_df[filtered_df['Date'].dt.date == date_filter]
if campaign_filter:
    filtered_df = filtered_df[filtered_df['Camp_ID'].isin(campaign_filter)]

# --- Display ---
st.subheader("📅 Summary Table")
st.dataframe(filtered_df)

# --- KPI Charts ---
st.subheader("📈 Reply & Delivery Rates")
st.bar_chart(filtered_df.set_index("Camp_ID")[["Reply %", "Delivery %"]])

import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# Function to load the sheet using service account credentials
@st.cache_data(show_spinner="Loading Google Sheet...")
def load_sheet():
    # Define required scopes
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    # Load service account info from Streamlit secrets
    creds = Credentials.from_service_account_info(
        st.secrets["google_service_account"], scopes=scope
    )

    client = gspread.authorize(creds)

    # Use hardcoded Google Sheet URL
    sheet_url = "https://docs.google.com/spreadsheets/d/1rl0AdLpgsYtzIfTWrdPmdiG1biQlstvXAqKP_qbPojY/edit?usp=sharing"
    sheet = client.open_by_url(sheet_url)

    return sheet

# Load data from specific tabs
def fetch_data():
    sheet = load_sheet()

    churn_df = pd.DataFrame(sheet.worksheet("Daily report - Churn").get_all_records())
    cs_df    = pd.DataFrame(sheet.worksheet("CS").get_all_records())
    node_def = pd.DataFrame(sheet.worksheet("Node_def").get_all_records())
    cta_def  = pd.DataFrame(sheet.worksheet("CTA_Def").get_all_records())

    return churn_df, cs_df, node_def, cta_def

# Streamlit UI
st.set_page_config(page_title="Automated Campaign Dashboard", layout="wide")
st.title("📊 Automated Campaign Dashboard")

try:
    churn_df, cs_df, node_def, cta_def = fetch_data()

    with st.expander("📌 Churn Report"):
        st.dataframe(churn_df)

    with st.expander("📄 Cost Sheet"):
        st.dataframe(cs_df)

    with st.expander("🔁 Node Definitions"):
        st.dataframe(node_def)

    with st.expander("✅ CTA Definitions"):
        st.dataframe(cta_def)

except Exception as e:
    st.error(f"❌ Failed to load data: {e}")

import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from urllib.parse import urlparse

# Get sheet URL from user or use default
sheet_url = "https://docs.google.com/spreadsheets/d/1HqdMofrH250DFnbuVKMxboJc0w0AlaVAF1aFYBNCYQQ/edit?usp=sharing"

@st.cache_resource
def load_sheet(sheet_url):
    # Extract sheet ID
    sheet_id = sheet_url.split("/d/")[1].split("/")[0]

    # Load credentials from secrets
    creds_dict = st.secrets["google_service_account"]
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    
    client = gspread.authorize(creds)
    sheet = client.open_by_key(sheet_id)
    return sheet

def fetch_data():
    try:
        sheet = load_sheet(sheet_url)
        churn_df = pd.DataFrame(sheet.worksheet("churn").get_all_records())
        cs_df = pd.DataFrame(sheet.worksheet("costsheet").get_all_records())
        node_def = pd.DataFrame(sheet.worksheet("nodes_def").get_all_records())
        cta_def = pd.DataFrame(sheet.worksheet("ctas_def").get_all_records())
        return churn_df, cs_df, node_def, cta_def
    except Exception as e:
        st.error("❌ Failed to load data:")
        st.exception(e)
        return None, None, None, None

# Load data
st.title("Campaign Dashboard")
churn_df, cs_df, node_def, cta_def = fetch_data()

if churn_df is not None:
    st.subheader("Churn Data")
    st.dataframe(churn_df)

    st.subheader("Cost Sheet Data")
    st.dataframe(cs_df)

    st.subheader("Node Definitions")
    st.dataframe(node_def)

    st.subheader("CTA Definitions")
    st.dataframe(cta_def)

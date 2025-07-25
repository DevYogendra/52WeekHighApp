import streamlit as st
from pathlib import Path
import importlib

st.set_page_config(page_title="52-Week High Tracker", layout="wide")

# Sidebar navigation
st.sidebar.title("📊 Navigation")
page_options = {
    "📈 Within 5% of 52W High": "daily_viewer",
    "📉 5–50% from 52W High": "fivetofiftyclub_viewer",    
    "📉 Big Dippers (50%+ Down)": "downfromhigh_viewer",        
    "📊 Trend Shift Analyzer": "trend_shift",
    "🔥 Emerging Winners": "emerging_winners",
    "📈 Trend Analyzer": "trend_analyzer",
    "🌪️ Industry Tailwinds": "industry_tailwinds",
    "📈 Momentum Summary": "momentum_summary",
}

page_selection = st.sidebar.radio("Go to", list(page_options.keys()))

# Dynamically import and run selected view
selected_module_name = page_options[page_selection]
module = importlib.import_module(f"views.{selected_module_name}")
if hasattr(module, "main"):
    module.main()
else:
    st.error(f"Module `{selected_module_name}` does not have a `main()` function.")

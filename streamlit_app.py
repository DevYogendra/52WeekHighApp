import importlib

import streamlit as st

st.set_page_config(page_title="52-Week High Tracker", layout="wide")

# Sidebar navigation
st.sidebar.title("Navigation")
page_options = {
    "Start Here": "start_here_view",
    "Trend Analyzer": "trend_analyzer_view",
    "Trend Shift Analyzer": "trend_shift_view",
    "Industry Tailwinds": "industry_tailwinds_view",
    "Emerging Winners": "emerging_winners_view",
    "Momentum Summary": "momentum_summary_view",
    "Multi-Bagger Hunt": "multi_bagger_hunt_view",
    "Within 5% of 52W High": "near_52w_high_view",
    "5-50% from 52W High": "pullback_candidates_view",
    "Big Dippers (50%+ Down)": "deep_dippers_view",
}

page_selection = st.sidebar.radio("Go to", list(page_options.keys()))

# Dynamically import and run selected view
selected_module_name = page_options[page_selection]
module = importlib.import_module(f"views.{selected_module_name}")
if hasattr(module, "main"):
    module.main()
else:
    st.error(f"Module `{selected_module_name}` does not have a `main()` function.")

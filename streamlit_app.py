import importlib

import streamlit as st

st.set_page_config(page_title="52-Week High Tracker", layout="wide")

PAGE_OPTIONS = {
    "Start Here": "start_here_view",
    "Momentum Rankings": "momentum_view",
    "Price Position": "price_position_view",
    "Industry Tailwinds": "industry_tailwinds_view",
    "Valuation Calculator": "valuation_calculator_view",
    "Bank & NBFC Valuation": "bank_nbfc_valuation_view",
}

st.sidebar.title("52-Week High Tracker")
page_selection = st.sidebar.radio(
    "Go to",
    list(PAGE_OPTIONS.keys()),
    key="page_radio",
    label_visibility="collapsed",
)

try:
    module = importlib.import_module(f"views.{PAGE_OPTIONS[page_selection]}")
    if hasattr(module, "main"):
        module.main()
    else:
        st.error(f"Module `{PAGE_OPTIONS[page_selection]}` has no main() function.")
except Exception as exc:
    st.error(f"Error loading view: {exc}")

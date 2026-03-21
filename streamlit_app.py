import importlib
from pathlib import Path

import streamlit as st

from docs.html_integration import DocumentationHelper

st.set_page_config(page_title="52-Week High Tracker", layout="wide")

DOCS_DIR = Path(__file__).resolve().parent / "docs"
docs_helper = DocumentationHelper(docs_dir=DOCS_DIR)

if "current_page" not in st.session_state:
    st.session_state.current_page = "Start Here"
if "current_doc" not in st.session_state:
    st.session_state.current_doc = None

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

doc_options = {
    "Help Hub": "Documentation Hub",
    "Quick Start": "Quick Start",
    "How to Read": "Interpretation Guide",
    "Glossary": "Financial Glossary",
}

st.sidebar.title("Navigation")
st.sidebar.subheader("Main Views", divider="gray")

page_selection = st.sidebar.radio(
    "Go to",
    list(page_options.keys()),
    key="page_radio",
    label_visibility="collapsed",
)

st.sidebar.divider()
st.sidebar.subheader("Help & Documentation", divider="gray")

doc_selection = st.sidebar.radio(
    "Documentation",
    ["None"] + list(doc_options.keys()),
    key="doc_radio",
    label_visibility="collapsed",
)

if doc_selection != "None":
    st.session_state.current_doc = doc_options[doc_selection]
    st.session_state.current_page = None
else:
    st.session_state.current_doc = None
    st.session_state.current_page = page_selection

if st.session_state.current_doc:
    docs_helper.add_main_help_page(initial_page=st.session_state.current_doc)
elif st.session_state.current_page:
    try:
        selected_module_name = page_options[st.session_state.current_page]
        module = importlib.import_module(f"views.{selected_module_name}")
        if hasattr(module, "main"):
            module.main()
        else:
            st.error(f"Module `{selected_module_name}` does not have a `main()` function.")
    except Exception as exc:
        st.error(f"Error loading view: {exc}")
else:
    st.info("Select a view from the sidebar to get started.")

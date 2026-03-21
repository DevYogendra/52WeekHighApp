import importlib
import os
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="52-Week High Tracker", layout="wide")

# Initialize session state for page navigation
if "current_page" not in st.session_state:
    st.session_state.current_page = "Start Here"
if "current_doc" not in st.session_state:
    st.session_state.current_doc = None

# Page configuration
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

doc_info = {
    "📚 Help Hub": "HTML_DOCUMENTATION_SUITE_README.md",
    "🚀 Quick Start": "QUICK_START.md",
    "📖 How to Read": "INTERPRETATION_GUIDE.md",
    "📚 Glossary": "GLOSSARY.md",
}

# Sidebar navigation
st.sidebar.title("Navigation")
st.sidebar.subheader("Help & Documentation", divider="gray")

doc_selection = st.sidebar.radio("Documentation", ["None"] + list(doc_info.keys()), key="doc_radio", label_visibility="collapsed")
if doc_selection != "None":
    st.session_state.current_doc = doc_info[doc_selection]
    st.session_state.current_page = None
else:
    st.session_state.current_doc = None

st.sidebar.divider()
st.sidebar.subheader("Main Views", divider="gray")

page_selection = st.sidebar.radio("Go to", list(page_options.keys()), key="page_radio", label_visibility="collapsed")
st.session_state.current_page = page_selection
st.session_state.current_doc = None

# Display content based on selection
if st.session_state.current_doc:
    # Load and display documentation
    doc_filename = st.session_state.current_doc
    doc_path = os.path.join(os.path.dirname(__file__), "docs", doc_filename)
    
    if os.path.exists(doc_path):
        with open(doc_path, "r", encoding="utf-8") as f:
            doc_content = f.read()
        st.markdown(doc_content)
    else:
        st.error(f"📄 Documentation file not found: {doc_filename}")
        st.info(f"Looking for file at: {doc_path}")

elif st.session_state.current_page:
    # Load and display main view
    try:
        selected_module_name = page_options[st.session_state.current_page]
        module = importlib.import_module(f"views.{selected_module_name}")
        if hasattr(module, "main"):
            module.main()
        else:
            st.error(f"Module `{selected_module_name}` does not have a `main()` function.")
    except Exception as e:
        st.error(f"Error loading view: {str(e)}")
else:
    st.info("👈 Select a view from the sidebar to get started.")

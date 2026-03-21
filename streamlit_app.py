import importlib
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

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

doc_pages = {
    "📚 Help Hub": "help_hub",
    "🚀 Quick Start": "help_quick_start",
    "📖 How to Read": "help_interpretation",
    "📚 Glossary": "help_glossary",
}

# Sidebar navigation
st.sidebar.title("Navigation")
st.sidebar.subheader("Help & Documentation", divider="gray")

doc_selection = st.sidebar.radio("Documentation", ["None"] + list(doc_pages.keys()), key="doc_radio", label_visibility="collapsed")
if doc_selection != "None":
    st.session_state.current_doc = doc_pages[doc_selection]
    st.session_state.current_page = None
else:
    st.session_state.current_doc = None

st.sidebar.divider()
st.sidebar.subheader("Main Views", divider="gray")

page_selection = st.sidebar.radio("Go to", list(page_options.keys()), key="page_radio", label_visibility="collapsed")
st.session_state.current_page = page_selection
st.session_state.current_doc = None

# Helper function to display HTML documentation
def display_help_page(page_type):
    """Display HTML documentation pages"""
    docs_dir = Path(__file__).parent / "docs"
    
    file_mapping = {
        "help_hub": docs_dir / "index.html",
        "help_quick_start": docs_dir / "quick-start.html",
        "help_interpretation": docs_dir / "interpretation-guide.html",
        "help_glossary": docs_dir / "glossary.html",
    }
    
    html_file = file_mapping.get(page_type)
    if html_file and html_file.exists():
        with open(html_file, "r", encoding="utf-8") as f:
            html_content = f.read()
        components.html(html_content, height=800, scrolling=True)
    else:
        st.error(f"Documentation file not found: {html_file}")

# Route to appropriate page
if st.session_state.current_doc:
    display_help_page(st.session_state.current_doc)
elif st.session_state.current_page:
    selected_module_name = page_options[st.session_state.current_page]
    module = importlib.import_module(f"views.{selected_module_name}")
    if hasattr(module, "main"):
        module.main()
    else:
        st.error(f"Module `{selected_module_name}` does not have a `main()` function.")

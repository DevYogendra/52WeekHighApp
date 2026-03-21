"""
HTML Documentation Helper Module
Provides easy integration of HTML documentation pages in Streamlit app
"""

import streamlit as st
from pathlib import Path
import webbrowser


class DocumentationHelper:
    """Helper class to integrate HTML documentation in Streamlit"""
    
    def __init__(self, docs_dir: str = "docs"):
        """Initialize documentation helper"""
        self.docs_dir = Path(docs_dir)
        self.pages = {
            "Quick Start": "quick-start.html",
            "Interpretation Guide": "interpretation-guide.html",
            "Financial Glossary": "glossary.html",
            "Documentation Hub": "index.html"
        }
    
    def add_sidebar_navigation(self):
        """Add documentation navigation to Streamlit sidebar"""
        with st.sidebar:
            st.divider()
            st.subheader("📚 Help & Reference")
            
            # Quick links in columns
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🚀 Quick Start", use_container_width=True, key="help_qs"):
                    self.open_help_page("Quick Start")
            
            with col2:
                if st.button("📖 How to Read", use_container_width=True, key="help_ig"):
                    self.open_help_page("Interpretation Guide")
            
            # Lower priority links
            if st.button("📚 Glossary", use_container_width=True, key="help_gl"):
                self.open_help_page("Financial Glossary")
            
            if st.button("🏠 All Docs", use_container_width=True, key="help_hub"):
                self.open_help_page("Documentation Hub")
    
    def add_main_help_page(self):
        """Create a dedicated Help page in main view"""
        st.set_page_config(page_title="Help Center", layout="wide")
        
        st.title("📚 Help Center")
        st.write("Complete documentation and reference guides for the 52-Week High Tracker app.")
        
        # Tabs for different sections
        tab1, tab2, tab3, tab4 = st.tabs([
            "Quick Start",
            "Interpretation",
            "Glossary",
            "Documentation Hub"
        ])
        
        with tab1:
            self._display_page_content("Quick Start")
        
        with tab2:
            self._display_page_content("Interpretation Guide")
        
        with tab3:
            self._display_page_content("Financial Glossary")
        
        with tab4:
            self._display_page_content("Documentation Hub")
    
    def _display_page_content(self, page_name: str):
        """Display HTML page content in Streamlit"""
        html_file = self.docs_dir / self.pages[page_name]
        
        if not html_file.exists():
            st.error(f"Documentation file not found: {html_file}")
            return
        
        try:
            with open(html_file, "r", encoding="utf-8") as f:
                html_content = f.read()
            
            # Extract body content (remove header/footer for embedding)
            # This is a simplified approach - you may need to adjust based on structure
            if "<body>" in html_content:
                body_start = html_content.find("<body>") + 6
                body_end = html_content.find("</body>")
                body_content = html_content[body_start:body_end]
            else:
                body_content = html_content
            
            # Display in Streamlit
            st.markdown(
                body_content,
                unsafe_allow_html=True
            )
            
        except Exception as e:
            st.error(f"Error loading documentation: {str(e)}")
    
    def open_help_page(self, page_name: str):
        """Open help page in browser or display options"""
        html_file = self.docs_dir / self.pages[page_name]
        
        if not html_file.exists():
            st.error(f"Documentation file not found: {html_file}")
            return
        
        # Get absolute path
        abs_path = html_file.absolute()
        file_url = abs_path.as_uri()  # Converts to file:// URL correctly on all OS
        
        st.info(f"""
            📖 **{page_name}**
            
            ✅ Click below to open in your browser:
            
            [{page_name}]({file_url})
            
            *Opening in a new tab provides the best experience with full formatting.*
        """)
    
    def get_documentation_path(self, page_name: str) -> Path:
        """Get path to a documentation page"""
        if page_name not in self.pages:
            raise ValueError(f"Unknown page: {page_name}")
        return self.docs_dir / self.pages[page_name]
    
    def list_available_pages(self) -> dict:
        """List all available documentation pages"""
        available = {}
        for name, filename in self.pages.items():
            path = self.docs_dir / filename
            if path.exists():
                available[name] = str(path)
        return available


class DocumentationViewer:
    """Alternative viewer using markdown conversion"""
    
    def __init__(self, docs_dir: str = "docs"):
        """Initialize documentation viewer"""
        self.docs_dir = Path(docs_dir)
        self.md_files = {
            "Quick Start": "QUICK_START.md",
            "Interpretation Guide": "INTERPRETATION_GUIDE.md",
            "Financial Glossary": "GLOSSARY.md",
        }
    
    def display_page(self, page_name: str):
        """Display markdown page in Streamlit"""
        if page_name not in self.md_files:
            st.error(f"Unknown page: {page_name}")
            return
        
        md_file = self.docs_dir / self.md_files[page_name]
        
        if not md_file.exists():
            st.error(f"Documentation file not found: {md_file}")
            return
        
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            st.markdown(content)
            
        except Exception as e:
            st.error(f"Error loading documentation: {str(e)}")
    
    def display_all_pages(self):
        """Display all documentation pages in tabs"""
        tabs = st.tabs(list(self.md_files.keys()))
        
        for tab, page_name in zip(tabs, self.md_files.keys()):
            with tab:
                self.display_page(page_name)


# ============================================================================
# QUICK START - Usage Examples
# ============================================================================

def example_1_add_sidebar_help():
    """Example 1: Add help navigation to sidebar"""
    docs = DocumentationHelper()
    docs.add_sidebar_navigation()


def example_2_add_help_page():
    """Example 2: Create dedicated Help page"""
    # In your main app, add this to page routing:
    # if selected_page == "Help":
    #     docs = DocumentationHelper()
    #     docs.add_main_help_page()
    pass


def example_3_open_help_in_browser():
    """Example 3: Simple button to open help"""
    docs = DocumentationHelper()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Quick Start"):
            docs.open_help_page("Quick Start")
    
    with col2:
        if st.button("Interpretation Guide"):
            docs.open_help_page("Interpretation Guide")
    
    with col3:
        if st.button("Glossary"):
            docs.open_help_page("Financial Glossary")


def example_4_markdown_viewer():
    """Example 4: Display markdown docs inline"""
    viewer = DocumentationViewer()
    
    page = st.sidebar.radio(
        "Documentation",
        ["Quick Start", "Interpretation Guide", "Financial Glossary"]
    )
    
    viewer.display_page(page)


# ============================================================================
# INTEGRATION INTO streamlit_app.py
# ============================================================================

"""
To integrate into your streamlit_app.py:

1. Import at the top:
   from docs.html_integration import DocumentationHelper

2. Add to sidebar navigation:
   docs = DocumentationHelper()
   docs.add_sidebar_navigation()

3. OR add a Help page option:
   
   PAGES = {
       "Start Here": start_here_view,
       "Trend Analyzer": trend_analyzer_view,
       # ... other views ...
       "Help": "help"
   }
   
   page_options = list(PAGES.keys())
   selected_page = st.sidebar.selectbox("Select a page", page_options)
   
   if selected_page == "Help":
       docs = DocumentationHelper()
       docs.add_main_help_page()
   else:
       # Import and call your view functions
       ...

Example minimal integration:

    import streamlit as st
    from docs.html_integration import DocumentationHelper
    
    st.set_page_config(page_title="52-Week High Tracker", layout="wide")
    
    docs = DocumentationHelper()  # Create once
    
    with st.sidebar:
        st.title("52-Week High Tracker")
        page = st.radio("Select View", [...your pages...])
        docs.add_sidebar_navigation()  # Add help links
    
    # ... rest of your app ...
"""

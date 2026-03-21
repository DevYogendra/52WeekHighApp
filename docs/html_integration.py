"""
HTML documentation integration helpers for the Streamlit app.
"""

from pathlib import Path

import streamlit as st


class DocumentationHelper:
    """Render bundled HTML documentation inside the app or as external links."""

    def __init__(self, docs_dir: str | Path = "docs"):
        self.docs_dir = Path(docs_dir)
        self.pages = {
            "Quick Start": "quick-start.html",
            "Interpretation Guide": "interpretation-guide.html",
            "Financial Glossary": "glossary.html",
            "Documentation Hub": "index.html",
        }
        self.markdown_pages = {
            "Quick Start": "QUICK_START.md",
            "Interpretation Guide": "INTERPRETATION_GUIDE.md",
            "Financial Glossary": "GLOSSARY.md",
            "Documentation Hub": "HTML_DOCUMENTATION_SUITE_README.md",
        }
        self.page_meta = {
            "Quick Start": {
                "label": "Quick Start",
                "summary": "Get oriented fast and start using the app with confidence.",
                "audience": "Best for first-time users",
                "cta": "Read Quick Start",
            },
            "Interpretation Guide": {
                "label": "How to Read the Signals",
                "summary": "Understand the tables, metrics, and what the signals are actually telling you.",
                "audience": "Best for deeper analysis",
                "cta": "Open Guide",
            },
            "Financial Glossary": {
                "label": "Glossary",
                "summary": "Look up investing and market terms without leaving the app.",
                "audience": "Best for quick reference",
                "cta": "Open Glossary",
            },
            "Documentation Hub": {
                "label": "All Help",
                "summary": "Browse everything and jump to the guide that matches what you are doing.",
                "audience": "Best for browsing",
                "cta": "Browse Help",
            },
        }

    def get_documentation_path(self, page_name: str) -> Path:
        if page_name not in self.pages:
            raise ValueError(f"Unknown page: {page_name}")
        return self.docs_dir / self.pages[page_name]

    def get_markdown_path(self, page_name: str) -> Path:
        if page_name not in self.markdown_pages:
            raise ValueError(f"Unknown page: {page_name}")
        return self.docs_dir / self.markdown_pages[page_name]

    def render_page(self, page_name: str) -> None:
        """Render the markdown documentation page natively in Streamlit."""
        markdown_file = self.get_markdown_path(page_name)
        if not markdown_file.exists():
            st.error(f"Documentation file not found: {markdown_file}")
            return

        st.markdown(markdown_file.read_text(encoding="utf-8"))

    def render_actions(self, page_name: str) -> None:
        """Provide reliable file actions instead of fragile file:// links."""
        html_file = self.get_documentation_path(page_name)
        markdown_file = self.get_markdown_path(page_name)

        if html_file.exists():
            st.download_button(
                "Download HTML",
                data=html_file.read_text(encoding="utf-8"),
                file_name=html_file.name,
                mime="text/html",
                use_container_width=True,
                key=f"download_html_{page_name}",
            )

        if markdown_file.exists():
            st.download_button(
                "Download Markdown",
                data=markdown_file.read_text(encoding="utf-8"),
                file_name=markdown_file.name,
                mime="text/markdown",
                use_container_width=True,
                key=f"download_md_{page_name}",
            )

        st.caption(f"Local HTML file: {html_file}")

    def _set_selected_page(self, page_name: str) -> None:
        st.session_state["help_selected_page"] = page_name

    def _render_guide_cards(self, selected_page: str) -> str:
        page_names = list(self.pages.keys())
        columns = st.columns(len(page_names))

        for column, page_name in zip(columns, page_names):
            meta = self.page_meta[page_name]
            is_selected = page_name == selected_page
            title = meta["label"]
            if is_selected:
                title = f"{title} *"

            with column:
                st.markdown(f"**{title}**")
                st.caption(meta["audience"])
                st.write(meta["summary"])
                if st.button(meta["cta"], key=f"help_card_{page_name}", use_container_width=True):
                    self._set_selected_page(page_name)
                    st.rerun()

        return st.session_state.get("help_selected_page", selected_page)

    def add_main_help_page(self, initial_page: str | None = None) -> None:
        """Render the in-app help center."""
        page_names = list(self.pages.keys())
        default_index = page_names.index(initial_page) if initial_page in page_names else 0
        if "help_selected_page" not in st.session_state:
            st.session_state["help_selected_page"] = page_names[default_index]

        st.title("Help Center")
        st.write("Pick the guide that matches your task, then read it right here in the app.")

        quick_col, detail_col = st.columns([1.1, 1.9])
        with quick_col:
            st.info(
                "New to the app: start with Quick Start.\n\n"
                "Want to understand a metric or signal: open How to Read the Signals.\n\n"
                "Need a term explained: use the Glossary."
            )
        with detail_col:
            st.caption("Suggested path")
            st.write("Quick Start -> How to Read the Signals -> Glossary when needed")

        selected_page = self._render_guide_cards(st.session_state["help_selected_page"])
        selected_page = st.segmented_control(
            "Select a guide",
            page_names,
            default=selected_page,
            key="help_selected_page",
        )

        source_path = self.get_documentation_path(selected_page)
        markdown_path = self.get_markdown_path(selected_page)
        meta = self.page_meta[selected_page]

        info_col, action_col = st.columns([2.2, 1])
        with info_col:
            st.subheader(meta["label"])
            st.write(meta["summary"])
            st.caption(f"Source files: {source_path.name} and {markdown_path.name}")
        with action_col:
            self.render_actions(selected_page)

        st.divider()
        self.render_page(selected_page)

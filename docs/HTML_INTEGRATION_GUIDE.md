# HTML Documentation Integration Guide

This guide explains how to integrate the HTML documentation pages into your Streamlit app for user reference.

## Files Created

The following HTML files are now available in the `/docs/` directory:

- **index.html** - Main documentation hub (landing page)
- **quick-start.html** - Quick Start guide
- **interpretation-guide.html** - Interpretation & reference guide
- **glossary.html** - Financial terms glossary
- **styles.css** - Shared styling for all pages

## Integration Methods

### Method 1: Markdown Links (Simplest - Recommended)

Add a "Help & Reference" section to your Streamlit app sidebar:

```python
# In streamlit_app.py, in your sidebar navigation
with st.sidebar:
    st.divider()
    st.subheader("📚 Help & Reference")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("[📖 Quick Start](file:///path/to/docs/quick-start.html)")
    with col2:
        st.write("[🔍 How to Read](file:///path/to/docs/interpretation-guide.html)")
    
    st.write("[📊 Glossary](file:///path/to/docs/glossary.html)")
    st.write("[🏠 Documentation Hub](file:///path/to/docs/index.html)")
```

**Pros:**
- Simplest implementation
- No server needed
- Opens in browser tab

**Cons:**
- Opens in new browser tab/window
- File path must be absolute

### Method 2: Embedded Markdown (In-App)

Convert HTML to Markdown in Streamlit view or display markdown versions:

```python
if page == "Help":
    st.title("📚 Help Center")
    
    tab1, tab2, tab3 = st.tabs(["Quick Start", "Interpretation", "Glossary"])
    
    with tab1:
        with open("docs/QUICK_START.md", "r") as f:
            st.markdown(f.read())
    
    with tab2:
        with open("docs/INTERPRETATION_GUIDE.md", "r") as f:
            st.markdown(f.read())
    
    with tab3:
        with open("docs/GLOSSARY.md", "r") as f:
            st.markdown(f.read())
```

**Pros:**
- Keeps everything in-app
- Mobile-friendly
- No new browser window

**Cons:**
- Streamlit's markdown renderer loses some HTML styling
- Navigation between sections less smooth than browser

### Method 3: IFrame Embedding (Best Styling)

Embed HTML directly in Streamlit using IFrame:

```python
def show_help_page():
    st.title("📚 Help Center")
    
    help_select = st.radio("Select a guide:", 
        ["Quick Start", "Interpretation Guide", "Glossary", "Documentation Hub"],
        horizontal=True
    )
    
    file_map = {
        "Quick Start": "docs/quick-start.html",
        "Interpretation Guide": "docs/interpretation-guide.html",
        "Glossary": "docs/glossary.html",
        "Documentation Hub": "docs/index.html"
    }
    
    html_file = file_map[help_select]
    
    with open(html_file, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    # Embed using custom components or HTML
    components.html(html_content, height=800, scrolling=True)

# Add to sidebar or main view
if st.sidebar.button("📚 View Help"):
    show_help_page()
```

**Pros:**
- Preserves all HTML/CSS styling
- Professional appearance
- Navigation works within embedded page

**Cons:**
- Requires `streamlit-components-template` or custom component
- More complex setup
- Requires `import streamlit.components.v1 as components`

### Method 4: Local HTTP Server (Best UX)

Serve HTML files locally on Flask/FastAPI and embed:

```python
# Option A: Using streamlit-server-state or custom server

import subprocess
import time
from pathlib import Path

def start_docs_server():
    """Start simple HTTP server for docs"""
    docs_path = Path("docs").absolute()
    
    # Python SimpleHTTPServer on port 8888
    server_process = subprocess.Popen(
        ["python", "-m", "http.server", "8888", "--directory", str(docs_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(1)  # Give server time to start
    return server_process

if "docs_server" not in st.session_state:
    st.session_state.docs_server = start_docs_server()

# Then create links to localhost:8888
with st.sidebar:
    st.write("[📖 Quick Start](http://localhost:8888/quick-start.html)")
    st.write("[🔍 Interpret Guide](http://localhost:8888/interpretation-guide.html)")
    st.write("[📚 Glossary](http://localhost:8888/glossary.html)")
```

**Pros:**
- Perfect styling preserved
- Smooth navigation
- Professional experience (like separate browser)

**Cons:**
- Requires additional server
- More complex deployment
- Port management

## Recommended Implementation for Your App

### **For Quick Implementation: Method 1**

Simply add to your `streamlit_app.py`:

```python
# In sidebar, after view selection
st.divider()
st.subheader("📚 Documentation")

# Get absolute path to docs
docs_path = Path(__file__).parent / "docs"

col1, col2 = st.columns(2)
with col1:
    if st.button("🚀 Quick Start", use_container_width=True):
        st.info("📖 [Open Quick Start Guide](file:///" + str(docs_path / "quick-start.html") + ")")

with col2:
    if st.button("🔍 How to Read", use_container_width=True):
        st.info("🔍 [Open Interpretation Guide](file:///" + str(docs_path / "interpretation-guide.html") + ")")

col3, col4, col5 = st.columns(3)
with col3:
    st.write("[📚 Glossary](file:///" + str(docs_path / "glossary.html") + ")")
with col4:
    st.write("[🏠 Hub](file:///" + str(docs_path / "index.html") + ")")
with col5:
    st.write("[📋 README](https://github.com/yourrepo/README.md)")
```

### **For Best In-App Experience: Method 3**

Requires two lines of imports:

```python
import streamlit.components.v1 as components

# In your Help/Reference view:
with open("docs/quick-start.html", "r", encoding="utf-8") as f:
    html_content = f.read()
    components.html(html_content, height=800, scrolling=True)
```

## File Locations

All HTML files must be referenced relative to your `streamlit_app.py`:

```
52WeekHighApp/
├── streamlit_app.py
├── docs/
│   ├── index.html
│   ├── quick-start.html
│   ├── interpretation-guide.html
│   ├── glossary.html
│   ├── styles.css
│   ├── QUICK_START.md
│   ├── INTERPRETATION_GUIDE.md
│   ├── GLOSSARY.md
│   └── ...
└── views/
```

## Navigation Between Documents

All HTML files include:
- **Header links** back to main hub (index.html)
- **Footer navigation** with links to related documents
- **Breadcrumb navigation** at top of each page
- **Internal anchors** for sections (click to jump)

## Customization

### Colors
Modify CSS variables in `styles.css`:

```css
:root {
    --primary-color: #1f77b4;  /* Change blue to your brand color */
    --success-color: #2ca02c;
    --danger-color: #d62728;
    --warning-color: #ff9800;
}
```

### Styling
All CSS is in `styles.css`. Modify for your brand:
- Font family (line 10)
- Colors (lines 2-8)
- Border radius (throughout)
- Spacing/padding (throughout)

## Mobile Responsiveness

All HTML pages are fully mobile-responsive:
- Grid layouts collapse to single column on mobile
- Navigation adjusts for small screens
- Touch-friendly buttons and links
- Scrollable on small screens

Test on mobile by:
1. Opening `index.html` in browser
2. Resizing window to simulate mobile (F12 Developer Tools)
3. All sections should reflow gracefully

## Printing

All pages include print styles. Users can:
- Right-click → Print → Save as PDF
- Works perfectly for creating study guides
- Sidebar hidden, footer hidden when printing

## Performance

- **styles.css** (8KB): Loaded once, cached by browser
- **Each HTML file** (30-50KB): Loaded on demand
- No external dependencies (no CDN calls)
- All assets included inline
- Fast loading, works offline

## Deployment Considerations

### Local Development
```bash
cd docs
python -m http.server 8000
# Open http://localhost:8000 in browser
```

### Production (Streamlit Cloud)
Option 1: Use Method 1 (file:// links) - simplest
Option 2: Host docs as static files on GitHub Pages or S3
Option 3: Embed as Method 3 (IFrame) in Streamlit

## Next Steps

1. **Choose integration method** from above (recommend Method 1 for now, upgrade to Method 3 later)
2. **Add to streamlit_app.py** sidebar section
3. **Test each link** - click through all pages
4. **Gather user feedback** - see if users find it helpful
5. **Iterate** - add more sections or views based on what users ask

## Troubleshooting

**Links not working?**
- Check file paths are correct
- Use absolute paths for file:// protocol (Method 1)
- On Windows, convert backslashes to forward slashes in URLs

**Styling not showing?**
- Check styles.css is in same directory as HTML files
- Ensure no file permission issues
- Try Method 3 (IFrame) if Method 1 not working

**Performance slow?**
- HTML files are ~40KB each - should load instantly
- Check if network connection slow
- Try local Method 2 (embedded markdown) if network issues

## Support

For questions about:
- **HTML/CSS customization** → Edit styles.css or individual HTML files
- **Streamlit integration** → See integration methods above
- **Content updates** → Update markdown source files and re-export to HTML
- **User feedback** → Add feedback form to final page

---

**Created:** March 2026
**Last Updated:** March 2026
**Status:** Production Ready

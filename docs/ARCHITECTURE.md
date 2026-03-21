# 🏗️ Architecture & System Design

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│                   STREAMLIT FRONTEND                     │
│                                                           │
│  streamlit_app.py (Navigation & Entry Point)            │
│           ↓                                              │
│  ┌──────────────────────────────────────────┐           │
│  │  View Selection (Sidebar Radio)          │           │
│  ├──────────────────────────────────────────┤           │
│  │ • Start Here                             │           │
│  │ • Trend Analyzer                         │           │
│  │ • Trend Shift Analyzer                   │           │
│  │ • Industry Tailwinds                     │           │
│  │ • Emerging Winners                       │           │
│  │ • Momentum Summary                       │           │
│  │ • Multi-Bagger Hunt                      │           │
│  │ • Within 5% of 52W High                  │           │
│  │ • 5–50% from 52W High                    │           │
│  │ • Big Dippers (50%+ Down)                │           │
│  └──────────────────────────────────────────┘           │
│           ↓                                              │
│  ┌──────────────────────────────────────────┐           │
│  │  Dynamically Imported View Module        │           │
│  │  (importlib.import_module)               │           │
│  └──────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────┘
         ↓              ↓                      ↓
    ┌────────────────────┐          ┌──────────────────────┐
    │  db_utils.py       │          │  plot_utils.py       │
    │  (Data Layer)      │          │  (Visualization)     │
    └────────────────────┘          └──────────────────────┘
         ↓                                    ↓
    ┌────────────────────┐          ┌──────────────────────┐
    │   config.py        │          │  grid_utils.py       │
    │ (Settings)         │          │  (Grid Rendering)    │
    └────────────────────┘          └──────────────────────┘
         ↓                                    ↓
    ┌────────────────────┐          ┌──────────────────────┐
    │  plot_utils.py +   │          │  st-aggrid +         │
    │  plotly/matplotlib │          │  JavaScript          │
    └────────────────────┘          └──────────────────────┘
         ↓
    ┌────────────────────────────────────┐
    │      SQLite Database               │
    │         (highs.db)                 │
    │  ┌────────────────────────────┐   │
    │  │ Tables:                    │   │
    │  │ • highs (main data)        │   │
    │  │ • fivetofiftyclub          │   │
    │  │ • downfromhigh             │   │
    │  └────────────────────────────┘   │
    └────────────────────────────────────┘
```

## Component Architecture

### 1. **Entry Point: streamlit_app.py**

**Responsibility:** Navigation and dynamic module loading

**Flow:**
```
1. Set page config (title, layout)
2. Display sidebar navigation (radio buttons)
3. Extract selected module name from navigation menu
4. Use importlib to dynamically import view module
5. Call main() function from imported module
6. Display module content (or error if no main() found)
```

**Key Patterns:**
- Dynamic imports for scalability (no hardcoded imports)
- Sidebar for consistent navigation across all views
- Error handling if view doesn't implement `main()`

---

### 2. **Data Layer: db_utils.py**

**Responsibility:** All database operations, caching, and data transformations

**Key Functions:**

#### Database Access (with error handling & context managers)
```python
get_fivetofiftyclub_dates()              # Returns list of dates
get_fivetofiftyclub_data_for_date(date)  # Returns DataFrame for date
get_downfromhigh_dates()                 # Similar for another table
get_downfromhigh_data_for_date(date)     # Similar for another table
```

#### Cached Data Functions (1-hour TTL)
```python
@st.cache_data(ttl=3600)
get_momentum_summary()         # Rolling hit counts + latest valuation
get_historical_market_cap()    # All historical data
get_all_dates()                # Distinct dates in database
get_data_for_date(date)        # Data for specific date
get_sparkline_data()           # Presence flag for sparkline charts
```

#### Data Transformation
```python
_apply_standard_types(df)      # Converts columns to correct types
add_screener_links(df)         # Generates HTML links for companies
compute_weekly_summary(df, start, end)  # Aggregates by week
```

**Features:**
- ✅ All connections use context managers (`with sqlite3.connect()`)
- ✅ Graceful error handling with `try-except` → `st.error()`
- ✅ 1-hour cache TTL prevents stale financial data
- ✅ Type consistency with `_apply_standard_types()`

---

### 3. **Visualization Layer: plot_utils.py**

**Responsibility:** Create Plotly and Matplotlib visualizations

**Functions:**
```python
sector_heatmap(heat_df, title)              # Static heatmap
animated_sector_heatmap(weekly_agg, title)  # Week-over-week animation
market_cap_line_chart(stock_data, name)     # Time-series chart
```

**Features:**
- Uses Plotly for interactive charts
- Custom hover templates for better UX
- Responsive layout sizing

---

### 4. **Grid Rendering: grid_utils.py**

**Responsibility:** Interactive table rendering with AG-Grid

**Main Function:**
```python
render_interactive_table(
    df,
    columns=["name", "market_cap", "industry"],
    key="unique_table_key",           # Unique identifier for widget
    rename_map={"name": "Company"},   # Display column names
    integer_cols=["hits_7"],          # Format as integers
    major_cols=["market_cap"],        # Format with commas
    one_decimal_cols=["%_gain_mc"],   # Show 1 decimal
    two_decimal_cols=["score"],       # Show 2 decimals
    link_col="name",                  # Column with HTML links
    height=400,                       # Grid height
    fit_columns=True                  # Auto-fit widths
)
```

**Features:**
- ✅ Sortable columns (click header)
- ✅ Filterable columns (right-click header)
- ✅ Resizable columns
- ✅ Number formatting (integers, decimals, commas)
- ✅ Clickable links (if link_col specified)
- ✅ Large numbers displayed in currency format

**Key Functions:**
```
_normalize_for_grid(df)        # Normalize data types for display
_js_number_formatter()         # JavaScript formatting for numbers
_js_major_formatter()          # JavaScript formatting for large values
_build_screener_url()          # Build links to Screener.in
_extract_link()                # Extract URLs from HTML
```

**Benefits:**
- Much better UX than st.dataframe()
- Users can export data to CSV
- Powerful filtering without reloading
- Professional appearance

---

### 5. **Configuration: config.py**

**Responsibility:** Centralized settings and constants

**Contents:**
```python
DB_PATH                  # Database file path
CACHE_TTL               # Cache refresh interval (seconds)
TABLE_HIGHS, TABLE_...  # Table names (DRY principle)
INVALID_CODES           # Data validation set
COLUMN_TYPES            # Type conversion mapping
PLOT_HEIGHT, PLOT_COLOR_SCALE  # Visual settings
ROLLING_WINDOWS         # Analysis periods [7, 30, 60]
```

**Benefits:**
- Single source of truth for all config
- Easy to modify without touching code
- Type-safe constants

---

### 5. **View Modules: views/*.py**

Each view implements a `main()` function that:

```python
def main():
    # 1. Set page title
    st.title("📈 Page Title")
    
    # 2. Fetch data using db_utils
    df = get_data_for_date(selected_date)
    
    # 3. Transform/filter data (add columns, compute metrics)
    df["new_column"] = transform(df["existing"])
    
    # 4. Display filters/controls (sidebars, sliders, etc.)
    market_cap_filter = st.sidebar.slider(...)
    df = df[df["market_cap"] > market_cap_filter]
    
    # 5. Visualize (tables, charts, metrics)
    st.dataframe(df)
    st.plotly_chart(fig)
    
    # 6. Add links and interactivity
    df = add_screener_links(df)
    st.markdown(styled_df.to_html(...), unsafe_allow_html=True)
```

---

## Data Flow Workflows

### Workflow 1: User Selects a View

```
1. User clicks radio button in sidebar (e.g., "Within 5% of 52W High")
2. streamlit_app.py extracts selected module name
3. importlib.import_module("views.near_52w_high_view")
4. Calls module.main()
5. View queries database → db_utils.get_data_for_date()
6. Database returns data (or error → st.error() shown)
7. View transforms data (add columns, format)
8. View displays UI (selectbox, dataframe, charts)
9. User interacts → widget values change
10. Streamlit reruns script with new widget state
11. Goto step 5 (fetch data again with new filters)
```

### Workflow 2: Cached Data Retrieval

```
FIRST CALL (cache miss):
1. View calls get_momentum_summary()
2. @st.cache_data decorator intercepts
3. Check cache → miss (not in memory)
4. Execute function:
   - Connect to database
   - Run 3 separate queries (7, 30, 60 day counts)
   - Join with latest snapshot
   - Apply type conversions
   - Close connection
5. Store result in cache with TTL=3600 seconds
6. Return result to caller
7. Display in UI

SUBSEQUENT CALL (within 1 hour, cache hit):
1. View calls get_momentum_summary()
2. @st.cache_data decorator intercepts
3. Check cache → hit (exists & not expired)
4. Return cached result immediately (no DB query!)

CALL AFTER 1 HOUR (cache miss again):
1. Cache entry expired
2. Repeat "FIRST CALL" sequence
```

### Workflow 3: Data Transformation & Styling

```
1. Fetch raw data from database
2. Apply type conversions: _apply_standard_types(df)
   - bse_code → Int64
   - nse_code → string
   - industry → string
   - name → string
3. Add computed columns:
   - Δ% MCap = (current - first) / first
   - P/E, P/BV (if provided)
4. Add HTML links: add_screener_links(df)
   - Extract NSE/BSE codes
   - Check validity (not "NA", empty, etc.)
   - Build URLs → https://screener.in/company/{code}/
5. Apply styling (gradient backgrounds):
   - highlight_valuation_gradient() → colors based on value
   - RdYlGn color scale (Red-Yellow-Green)
6. Render as HTML: styled_df.to_html(unsafe_allow_html=True)
7. Display in UI: st.markdown(..., unsafe_allow_html=True)
```

---

## Error Handling Strategy

### Layer 1: Database Operations
```python
try:
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql(query, conn)
except sqlite3.Error as e:
    st.error(f"Database error: {e}")
    return pd.DataFrame()  # Return empty, don't crash
```

**Features:**
- Context manager ensures connection close
- Catch `sqlite3.Error` exceptions
- Return empty DataFrame (safe default)
- User sees error message in UI

### Layer 2: Data Type Conversions
```python
def get_style(val, vmin, vmax):
    try:
        val = float(val)  # Convert string → numeric
    except (ValueError, TypeError):
        return None  # Skip if not convertible
    # ... continue styling
```

**Features:**
- Try to convert, catch conversion errors
- Skip non-convertible values gracefully
- No crashes on mixed data types

### Layer 3: Data Validation
```python
INVALID_CODES = {"", "NA", "<NA>", "<N/A>", "N/A", "NONE", "NAN"}

if code.upper() not in INVALID_CODES:
    # Safe to use this code
```

**Features:**
- Centralized validation constants
- Prevent invalid data from affecting output
- Multiple representations of "null" handled

---

## Performance Optimization

### 1. **Caching Strategy**
```
Expensive operations cached for 1 hour:
✓ get_momentum_summary() — 3 SQL queries + joins
✓ get_historical_market_cap() — Full table scan
✓ get_all_dates() — Expensive DISTINCT + sort
✓ get_data_for_date() — Per-date queries

Benefits:
- Repeated view access is instant
- Database load reduced 60x (1 hour cache)
- Financial data updates daily anyway (TTL appropriate)
```

### 2. **Parameterized Queries**
```python
query = "SELECT * FROM highs WHERE date = ?"
pd.read_sql(query, conn, params=(selected_date,))
```
**Benefit:** SQL injection prevention + database optimization

### 3. **Connection Context Managers**
```python
with sqlite3.connect(DB_PATH) as conn:
    # Uses connection
# Auto-closes after block exits
```
**Benefit:** Prevents connection leaks even with exceptions

---

## Extension Points

### Adding a New View

1. **Create file:** `views/my_new_view.py`
2. **Implement main():**
   ```python
   def main():
       st.title("📊 New View")
       # Your code here
   ```
3. **Add to navigation:** Edit `streamlit_app.py`
   ```python
   page_options = {
       "📊 My New View": "my_new_view",  # Add this line
       # ... existing entries
   }
   ```

### Adding New Database Functions

1. **Create in db_utils.py:**
   ```python
   @st.cache_data(ttl=CACHE_TTL)
   def my_new_query() -> pd.DataFrame:
       try:
           with sqlite3.connect(DB_PATH) as conn:
               df = pd.read_sql("SELECT ...", conn)
           df = _apply_standard_types(df)
           return df
       except sqlite3.Error as e:
           st.error(f"Database error: {e}")
           return pd.DataFrame()
   ```

### Adding New Charts

1. **Create function in plot_utils.py:**
   ```python
   def my_chart(data, title):
       fig = px.bar(...)  # Your plotly chart
       return fig
   ```
2. **Use in view:**
   ```python
   from plot_utils import my_chart
   fig = my_chart(df, "Title")
   st.plotly_chart(fig)
   ```

---

## Deployment Considerations

### Production Checklist

- [ ] Database (`highs.db`) backed up regularly
- [ ] Streamlit secrets configured (`~/.streamlit/secrets.toml`)
- [ ] Environment-specific config (dev vs prod settings)
- [ ] Monitoring for database errors
- [ ] Cache warming for large datasets
- [ ] Database indexing on frequently filtered columns

### Scaling Strategies

**If database grows large:**
1. Add indexes on `date`, `name`, `industry` columns
2. Archive old data to separate table
3. Use connection pooling (SQLAlchemy)
4. Consider PostgreSQL instead of SQLite

**If many concurrent users:**
1. Increase `CACHE_TTL` (less frequent recalculations)
2. Use Streamlit deployment (multi-worker support)
3. Add database connection pooling

---

## Current Known Limitations

1. **SQLite limitations** — Not ideal for 100K+ rows + concurrent access
2. **Dash vs Streamlit** — Streamlit reruns entire script on interaction
3. **Real-time data** — Updates only when data refreshed in database
4. **Type conversions** — Repeated in multiple views (mitigated by `_apply_standard_types()`)

---

**Last Updated:** March 2026

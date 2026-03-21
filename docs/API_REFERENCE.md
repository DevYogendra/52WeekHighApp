# 📚 API Reference

Complete function documentation for database utilities, visualization functions, and helper methods.

## Table of Contents

1. [db_utils.py](#db_utilspy) - Database and data management
2. [plot_utils.py](#plot_utilspy) - Visualization functions
3. [config.py](#configpy) - Configuration constants

---

## db_utils.py

### Database Query Functions

#### `get_fivetofiftyclub_dates()`

**Description:** Fetch all distinct dates available in the `fivetofiftyclub` table.

**Signature:**
```python
def get_fivetofiftyclub_dates() -> list[str]
```

**Returns:**
- `list[str]` → List of date strings (format: "YYYY-MM-DD")
- `[]` → Empty list if database error occurs (error shown to user)

**Raises:**
- `st.error()` displayed if `sqlite3.Error` occurs

**Example:**
```python
dates = get_fivetofiftyclub_dates()
print(dates)  # ["2026-03-01", "2026-03-02", ...]
```

**Performance:**
- ✓ Uses `SELECT DISTINCT` (efficient)
- ✓ Ordered by date (ready for display)
- ✓ Error handling included

---

#### `get_fivetofiftyclub_data_for_date(date_str: str) -> pd.DataFrame`

**Description:** Fetch all stocks in the 5-50% correction range for a specific date.

**Signature:**
```python
def get_fivetofiftyclub_data_for_date(date_str: str) -> pd.DataFrame
```

**Parameters:**
- `date_str` (str) → Date in format "YYYY-MM-DD"

**Returns:**
- `pd.DataFrame` → Columns: name, nse_code, bse_code, date, market_cap, industry, etc.
- `pd.DataFrame()` → Empty DataFrame if error occurs

**Raises:**
- `st.error()` displayed if `sqlite3.Error` occurs

**Example:**
```python
df = get_fivetofiftyclub_data_for_date("2026-03-19")
print(df.columns)  # ['name', 'nse_code', 'bse_code', 'date', ...]
print(len(df))     # Number of stocks in this range on this date
```

**Performance:**
- ✓ Parameterized query (SQL injection safe)
- ✓ Single database hit
- ✓ Automatic type conversion applied

**Data Types:**
```python
bse_code     → Int64 (nullable integer)
nse_code     → string
industry     → string
name         → string
market_cap   → float64
date         → datetime64[ns]
```

---

#### `get_downfromhigh_dates()`

**Description:** Fetch all distinct dates available in the `downfromhigh` table (stocks down 50%+).

**Signature:**
```python
def get_downfromhigh_dates() -> list[str]
```

**Returns:**
- `list[str]` → List of date strings
- `[]` → Empty list if database error

**Example:**
```python
dates = get_downfromhigh_dates()
```

**Note:** Same behavior as `get_fivetofiftyclub_dates()`, different table source.

---

#### `get_downfromhigh_data_for_date(date_str: str) -> pd.DataFrame`

**Description:** Fetch stocks down 50%+ from 52W highs for a specific date.

**Signature:**
```python
def get_downfromhigh_data_for_date(date_str: str) -> pd.DataFrame
```

**Parameters:**
- `date_str` (str) → Date in format "YYYY-MM-DD"

**Returns:**
- `pd.DataFrame` → Distressed/deep value opportunities
- `pd.DataFrame()` → Empty on error

**Note:** Same behavior as `get_fivetofiftyclub_data_for_date()`, different source table.

---

### Cached Data Functions

These functions use `@st.cache_data(ttl=CACHE_TTL)` for 1-hour caching.

#### `get_momentum_summary() -> pd.DataFrame`

**Description:** Compute momentum summary with rolling hit counts (7, 30, 60 days) and latest valuations.

**Signature:**
```python
@st.cache_data(ttl=CACHE_TTL)
def get_momentum_summary() -> pd.DataFrame
```

**Returns:**
```python
pd.DataFrame with columns:
├─ name                  (str)      Company name
├─ nse_code              (string)   NSE listing code
├─ bse_code              (Int64)    BSE listing code
├─ industry              (string)   Industry classification
├─ market_cap            (float64)  Current market cap (₹)
├─ first_market_cap      (float64)  Market cap at first appearance
├─ first_seen_date       (object)   Date of first appearance
├─ %_gain_mc             (float64)  % growth since first appearance
├─ hits_7                (int64)    Appearances in 7-day window
├─ hits_30               (int64)    Appearances in 30-day window
└─ hits_60               (int64)    Appearances in 60-day window
```

**Raises:**
- `st.error()` displayed if `sqlite3.Error` occurs

**Example:**
```python
summary = get_momentum_summary()
# Top 5 stocks by 7-day hits
top_movers = summary.nlargest(5, "hits_7")
print(top_movers[["name", "hits_7", "%_gain_mc"]])
```

**Cache Behavior:**
- 1st call: Executes queries (10-50ms)
- Subsequent calls (< 1 hour): Returns cached result (instant)
- After 1 hour: Re-executes (cache expired)

**Performance Notes:**
- ✓ Runs 3 complex queries combined
- ✓ Joins on multiple conditions
- ✓ Type conversion applied automatically

---

#### `get_historical_market_cap() -> pd.DataFrame`

**Description:** Fetch complete historical market cap data for all stocks.

**Signature:**
```python
@st.cache_data(ttl=CACHE_TTL)
def get_historical_market_cap() -> pd.DataFrame
```

**Returns:**
```python
pd.DataFrame with columns:
├─ name              (string)     Company name
├─ date              (datetime64)  Date
├─ market_cap        (float64)    Market cap
├─ nse_code          (string)     NSE code
├─ bse_code          (Int64)      BSE code
├─ industry          (string)     Industry
└─ [other columns from database]
```

**Example:**
```python
df = get_historical_market_cap()
# Filter to specific stock and date range
apple = df[(df["name"] == "Apple") & (df["date"] >= "2026-01-01")]
print(apple[["date", "market_cap"]])
```

**Use Cases:**
- Time-series analysis
- Trend visualization
- Week-over-week comparisons
- Industry-wide aggregations

**Performance:**
- ✓ Single full table scan (cached for 1 hour)
- ✓ Types applied: dates as datetime64, codes as string
- ✓ No filtering, raw data returned (filter in-memory)

---

#### `get_all_dates() -> list[datetime.date]`

**Description:** Fetch all distinct dates in the database, sorted chronologically.

**Signature:**
```python
@st.cache_data(ttl=CACHE_TTL)
def get_all_dates() -> list[datetime.date]
```

**Returns:**
- `list[datetime.date]` → Sorted dates, returns `datetime.date` objects
- `[]` → Empty list on database error

**Example:**
```python
dates = get_all_dates()
print(dates)  # [datetime.date(2026, 1, 1), datetime.date(2026, 1, 2), ...]
print(dates[-1])  # Latest date
print(dates[0])   # Oldest date
```

**Typical Usage:**
```python
dates = get_all_dates()
selected_date = st.selectbox(
    "Pick a date",
    dates,
    format_func=lambda d: d.strftime("%Y-%m-%d")
)
```

---

#### `get_data_for_date(selected_date: str | datetime.date) -> pd.DataFrame`

**Description:** Fetch all stocks in the `highs` table for a specific date.

**Signature:**
```python
@st.cache_data(ttl=CACHE_TTL)
def get_data_for_date(selected_date: str | datetime.date) -> pd.DataFrame
```

**Parameters:**
- `selected_date` (str or datetime.date) → Date to query
  - Accepts: "2026-03-19" or datetime.date(2026, 3, 19)
  - Automatically converted by database layer

**Returns:**
- `pd.DataFrame` → All stocks on that date
- `pd.DataFrame()` → Empty on error

**Example:**
```python
# Using string
df = get_data_for_date("2026-03-19")

# Using date object
import datetime
df = get_data_for_date(datetime.date(2026, 3, 19))

print(df.columns)  # All columns from highs table
print(len(df))     # Number of stocks on this date
```

**Data Types Applied:**
```python
bse_code     → Int64
nse_code     → string
industry     → string
name         → string
```

---

#### `get_latest_table_date(table_name: str) -> datetime.date | None`

**Description:** Get the most recent date available in a specific table (cached).

**Signature:**
```python
@st.cache_data(ttl=CACHE_TTL)
def get_latest_table_date(table_name: str) -> datetime.date | None
```

**Parameters:**
- `table_name` (str) → Name of table to check
  - `config.TABLE_HIGHS` → "highs"
  - `config.TABLE_FIVETOFIFTYCLUB` → "fivetofiftyclub"
  - `config.TABLE_DOWNFROMHIGH` → "downfromhigh"

**Returns:**
- `datetime.date` → Latest date in table
- `None` → If table empty or error occurs

**Example:**
```python
from config import TABLE_HIGHS
latest_date = get_latest_table_date(TABLE_HIGHS)
print(f"Latest: {latest_date}")  # datetime.date(2026, 3, 19)

if latest_date:
    st.caption(f"Data current as of: {latest_date}")
```

**Use Cases:**
- Display "data as of" timestamp in UI
- Determine lookback windows
- Validate if new data is available

---

#### `get_persistence_scores() -> pd.DataFrame`

**Description:** Compute persistence scores for multi-bagger candidate ranking.

**Signature:**
```python
@st.cache_data(ttl=CACHE_TTL)
def get_persistence_scores() -> pd.DataFrame
```

**Returns:**
```python
pd.DataFrame with additional columns:
├─... (all momentum_summary columns)
├─ freq_ratio_7_30          (float64)  hits_7 ÷ hits_30 (acceleration)
├─ freq_ratio_30_60         (float64)  hits_30 ÷ hits_60 (sustained?)
├─ gain_mc                  (float64)  Market cap gain
└─ persistence_score        (float64)  Composite ranking score
```

**Scoring Formula:**
```python
persistence_score = 
    (40 × freq_ratio_7_30 capped[0,10]) +
    (30 × freq_ratio_30_60 capped[0,10]) +
    (30 × (gain_mc capped[-100,300] ÷ 100))
```

**Interpretation:**
- Higher score = Stronger persistence + recent acceleration
- ~20+ = Candidate for multi-bagger hunt
- ~50+ = High confidence persistent performer

**Example:**
```python
df = get_persistence_scores()
# Top 10 multi-bagger candidates
top_10 = df.nlargest(10, "persistence_score")
print(top_10[["name", "hits_7", "persistence_score"]])
```

---

#### `get_frequency_timeline(stock_name: str, weeks: int = 12) -> pd.DataFrame`

**Description:** Get weekly 52W-high frequency trend for a given stock (last 12 weeks default).

**Signature:**
```python
@st.cache_data(ttl=CACHE_TTL)
def get_frequency_timeline(stock_name: str, weeks: int = 12) -> pd.DataFrame
```

**Parameters:**
- `stock_name` (str) → Exact company name to look up
- `weeks` (int) → Number of weeks to return (default: 12)

**Returns:**
```python
pd.DataFrame with columns:
├─ week              (datetime64)  Start of week
├─ frequency         (int64)       Count of high appearances in that week
└─ market_cap_last   (float64)     Latest market cap for that week
```

**Example:**
```python
timeline = get_frequency_timeline("HDFC Bank", weeks=13)
print(timeline)
#                week  frequency  market_cap_last
# 0 2026-01-05  2          450000000000
# 1 2026-01-12  3          455000000000
```

**Use Cases:**
- Visualize stock momentum trends
- Input to frequency chart (plotly)
- Identify acceleration phases

---

#### `get_sparkline_data() -> pd.DataFrame`

**Description:** Fetch sparkline presence data for all stocks (for chart overlays).

**Signature:**
```python
@st.cache_data(ttl=CACHE_TTL)
def get_sparkline_data() -> pd.DataFrame
```

**Returns:**
```python
pd.DataFrame with columns:
├─ name           (string)     Company name
├─ date           (datetime64) Date of appearance
└─ value          (int64)      Always 1 (presence flag)
```

**Note:** This returns raw presence data; typically grouped by name for chart visualization.

**Example:**
```python
df = get_sparkline_data()
# Find stocks with most recent appearances
latest = df.sort_values("date").groupby("name").tail(1)
```

---

### Helper & Formatting Functions

#### `add_screener_links(df: pd.DataFrame) -> pd.DataFrame`

**Description:** Convert company names to clickable Screener.in links.

**Signature:**
```python
def add_screener_links(df: pd.DataFrame) -> pd.DataFrame
```

**Parameters:**
- `df` (pd.DataFrame) → Must contain columns: `name`, `nse_code` (preferred), `bse_code`

**Returns:**
- `pd.DataFrame` → Copy with `name` column containing HTML `<a>` tags

**Behavior:**
- Prefers NSE code if valid
- Falls back to BSE code if NSE unavailable
- Returns plain name if both unavailable (warning displayed)

**Example:**
```python
df = get_data_for_date("2026-03-19")
df = add_screener_links(df)
st.markdown(df[["name", "market_cap"]].to_html(escape=False), unsafe_allow_html=True)
# Name will be clickable link to Screener.in
```

**Safety:**
- ✓ Validates codes before use (checks INVALID_CODES set)
- ✓ Warns if no valid codes found
- ✓ User clicks link opens in new tab

---

#### `_apply_standard_types(df: pd.DataFrame) -> pd.DataFrame`

**Description:** Apply consistent type conversions to standard columns internally (private function).

**Signature:**
```python
def _apply_standard_types(df: pd.DataFrame) -> pd.DataFrame
```

**Conversions Applied:**
```python
bse_code     → Int64 (nullable integer)
nse_code     → string
industry     → string
name         → string
```

**Note:** Automatically called by database query functions, not normally called directly.

---

#### `compute_industry_tailwind_stats(df: pd.DataFrame) -> pd.DataFrame`

**Description:** Aggregate industry stats with market-cap weighting to reduce small-cap outlier skew.

**Signature:**
```python
def compute_industry_tailwind_stats(df: pd.DataFrame) -> pd.DataFrame
```

**Parameters:**
- `df` (pd.DataFrame) → Must contain: `industry`, `name`, `hits_7`, `%_gain_mc`, `market_cap`

**Returns:**
```python
pd.DataFrame aggregated by industry:
├─ industry         (object)   Industry name
├─ count_stocks     (int64)    Number of companies
├─ avg_hits_7       (float64)  Average 7-day hit count
└─ weighted_gain_mc (float64)  Market-cap-weighted gain %
```

**Key Feature:** Market-cap weighting prevents tiny 1000% gainers from skewing sector averages.

**Example:**
```python
df = get_momentum_summary()
industry_stats = compute_industry_tailwind_stats(df)
print(industry_stats.sort_values("weighted_gain_mc", ascending=False))
```

---

#### `format_major_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame`

**Description:** Apply human-friendly formatting to large-value columns (e.g., market caps).

**Signature:**
```python
def format_major_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame
```

**Parameters:**
- `df` (pd.DataFrame) → DataFrame to format
- `columns` (list[str]) → Column names to format

**Formatting:**
```python
1000000 → "1,000,000"
5000000000 → "5,000,000,000"
```

**Example:**
```python
df = get_momentum_summary()
df_display = format_major_columns(df, ["market_cap", "first_market_cap"])
st.dataframe(df_display)
```

---

#### `format_decimal_columns(df, one_decimal_cols=None, two_decimal_cols=None) -> pd.DataFrame`

**Description:** Apply consistent decimal precision to display columns.

**Signature:**
```python
def format_decimal_columns(
    df: pd.DataFrame,
    one_decimal_cols: list[str] | None = None,
    two_decimal_cols: list[str] | None = None,
) -> pd.DataFrame
```

**Parameters:**
- `df` (pd.DataFrame) → DataFrame to format
- `one_decimal_cols` (list[str]) → Columns formatted to 1 decimal
- `two_decimal_cols` (list[str]) → Columns formatted to 2 decimals

**Example:**
```python
df = get_momentum_summary()
df_display = format_decimal_columns(
    df,
    one_decimal_cols=["gain_pct_this", "%_gain_mc"],
    two_decimal_cols=["persistence_score", "avg_valuation"]
)
```

---

#### `format_integer_columns(df, integer_cols=None) -> pd.DataFrame`

**Description:** Apply integer formatting to count-like display columns.

**Signature:**
```python
def format_integer_columns(
    df: pd.DataFrame,
    integer_cols: list[str] | None = None,
) -> pd.DataFrame
```

**Parameters:**
- `df` (pd.DataFrame) → DataFrame to format
- `integer_cols` (list[str]) → Column names (hit counts, frequencies, etc.)

**Example:**
```python
df_display = format_integer_columns(df, integer_cols=["hits_7", "hits_30", "hits_60"])
```

---

## grid_utils.py

### Interactive Table Rendering

#### `render_interactive_table(...) -> None`

**Description:** Render an interactive AG-Grid table with sorting, filtering, and column resizing.

**Signature:**
```python
def render_interactive_table(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    key: str | None = None,
    rename_map: dict[str, str] | None = None,
    integer_cols: list[str] | None = None,
    one_decimal_cols: list[str] | None = None,
    two_decimal_cols: list[str] | None = None,
    major_cols: list[str] | None = None,
    link_col: str | None = None,
    height: int = 400,
    fit_columns: bool = False,
) -> None
```

**Parameters:**
- `df` (pd.DataFrame) → Data to display
- `columns` (list[str]) → Which columns to show (default: all)
- `key` (str) → Unique key for Streamlit state (avoids widget conflicts)
- `rename_map` (dict) → Map old column names to display names
- `integer_cols` (list[str]) → Columns to format as integers
- `one_decimal_cols` (list[str]) → Columns with 1 decimal place
- `two_decimal_cols` (list[str]) → Columns with 2 decimal places
- `major_cols` (list[str]) → Large numbers (with commas)
- `link_col` (str) → Column name containing HTML links
- `height` (int) → Grid height in pixels
- `fit_columns` (bool) → Auto-fit column widths

**Example:**
```python
df = get_momentum_summary()
render_interactive_table(
    df,
    columns=["name", "industry", "hits_7", "market_cap", "%_gain_mc"],
    rename_map={"name": "Company", "industry": "Sector"},
    integer_cols=["hits_7"],
    major_cols=["market_cap"],
    one_decimal_cols=["%_gain_mc"],
    link_col="name",
    height=500,
)
```

**Features:**
- ✓ Sortable columns (click header)
- ✓ Filterable (right-click column header)
- ✓ Resizable columns
- ✓ Formatted numbers
- ✓ Clickable links (if link_col specified)

---

## plot_utils.py

### Visualization Functions

#### `sector_heatmap(heat_df: pd.DataFrame, title: str) -> plotly.graph_objects.Figure`

**Description:** Create a static heatmap of industry momentum.

**Signature:**
```python
def sector_heatmap(heat_df: pd.DataFrame, title: str) -> Figure
```

**Parameters:**
- `heat_df` (pd.DataFrame) → Must have columns: `industry`, `Count`, `Avg_Gain_Percent`
- `title` (str) → Chart title

**Returns:**
- `plotly.graph_objects.Figure` → Use with `st.plotly_chart()`

**Expected Columns:**
```python
industry              → Industry name (x-axis)
Count                 → Number of companies (y-axis)
Avg_Gain_Percent      → Average gain % (color intensity)
```

**Example:**
```python
df = get_momentum_summary()
industry_agg = df.groupby("industry").agg({
    "name": "count",  # → Count
    "%_gain_mc": "mean"  # → Avg_Gain_Percent
}).rename(columns={"name": "Count"})
industry_agg["Avg_Gain_Percent"] = industry_agg["%_gain_mc"]

fig = sector_heatmap(industry_agg, "Industry Momentum Heatmap")
st.plotly_chart(fig, use_container_width=True)
```

---

#### `animated_sector_heatmap(weekly_agg: pd.DataFrame, title: str) -> plotly.graph_objects.Figure`

**Description:** Create animated heatmap showing week-by-week sector momentum evolution.

**Signature:**
```python
def animated_sector_heatmap(weekly_agg: pd.DataFrame, title: str) -> Figure
```

**Parameters:**
- `weekly_agg` (pd.DataFrame) → Must have columns: `industry`, `Count`, `Avg_Gain_Percent`, `week`
- `title` (str) → Chart title

**Returns:**
- `plotly.graph_objects.Figure` → Animated across weeks

**Expected Columns:**
```python
industry              → Industry name
Count                 → Number of companies
Avg_Gain_Percent      → Average gain %
week                  → Week identifier (for animation frames)
```

**Example:**
```python
# Compute weekly aggregations...
fig = animated_sector_heatmap(weekly_data, "Weekly Industry Trends")
st.plotly_chart(fig, use_container_width=True)
```

---

#### `market_cap_line_chart(stock_data: pd.DataFrame, company_name: str) -> plotly.graph_objects.Figure`

**Description:** Create time-series line chart showing market cap evolution.

**Signature:**
```python
def market_cap_line_chart(stock_data: pd.DataFrame, company_name: str) -> Figure
```

**Parameters:**
- `stock_data` (pd.DataFrame) → Must have: `date`, `market_cap`
- `company_name` (str) → Company name for title

**Returns:**
- `plotly.graph_objects.Figure` → Interactive line chart with markers

**Example:**
```python
df = get_historical_market_cap()
stock_data = df[df["name"] == "HDFC Bank"]
fig = market_cap_line_chart(stock_data, "HDFC Bank")
st.plotly_chart(fig, use_container_width=True)
```

---

## config.py

All configuration constants centralized for easy modification.

### Database Configuration

```python
DB_PATH                          # Path to SQLite database (highs.db)
CACHE_TTL                        # Cache time-to-live (3600 seconds = 1 hour)
```

### Table Names

```python
TABLE_HIGHS                      # "highs" - Main 52W high stocks
TABLE_FIVETOFIFTYCLUB           # "fivetofiftyclub" - 5-50% correction
TABLE_DOWNFROMHIGH              # "downfromhigh" - 50%+ down
```

### Data Validation

```python
INVALID_CODES                    # Set of invalid stock codes {"", "NA", "<NA>", etc.}
STANDARD_COLUMNS                # ["bse_code", "nse_code", "industry", "name"]
COLUMN_TYPES                    # Type mapping for type conversion
```

### Visualization Settings

```python
PLOT_HEIGHT                      # Height of charts (600 pixels)
PLOT_COLOR_SCALE                # Color scheme "RdYlGn" (Red-Yellow-Green)
```

### Analysis Configuration

```python
ROLLING_WINDOWS                  # [7, 30, 60] - Days for rolling aggregations
```

---

## Key Patterns & Best Practices

### Error Handling

All database functions follow this pattern:
```python
try:
    # Database operation
except sqlite3.Error as e:
    st.error(f"Database error: {e}")
    return pd.DataFrame()  # or [] for lists
```

### Caching Strategy

```python
@st.cache_data(ttl=CACHE_TTL)
def expensive_function():
    # Cache expires after 1 hour
    # Prevents stale financial data
    pass
```

### Type Safety

```python
# Before display
df = _apply_standard_types(df)  # Normalize types

# Format for display
df = format_major_columns(df, ["market_cap"])
df = format_integer_columns(df, ["hits_7", "hits_30"])
```

### Safe SQL Queries

```python
# ✓ SAFE - Parameterized
df = pd.read_sql(
    f"SELECT * FROM {TABLE_HIGHS} WHERE date = ?",
    conn,
    params=(date_str,)
)

# ✗ UNSAFE - String interpolation (SQL injection risk)
df = pd.read_sql(
    f"SELECT * FROM {TABLE_HIGHS} WHERE date = '{date_str}'",
    conn
)
```

---

#### `get_sparkline_data() -> pd.DataFrame`

**Description:** Fetch presence data for generating sparkline charts (stock activity over time).

**Signature:**
```python
@st.cache_data(ttl=CACHE_TTL)
def get_sparkline_data() -> pd.DataFrame
```

**Returns:**
```python
pd.DataFrame with columns:
├─ name       (string)      Company name
├─ date       (datetime64)  Date of appearance
└─ value      (int)         Always 1 (presence flag)
```

**Example:**
```python
spark_df = get_sparkline_data()
# Group by company to get activity timeline
company_activity = spark_df[spark_df["name"] == "Reliance"]
print(company_activity["date"].min())  # First appearance
print(company_activity["date"].max())  # Last appearance
print(len(company_activity))           # Days in highs
```

**Use Cases:**
- Sparkline visualization (frequency over time)
- Activity heatmaps
- Consistency checks (which days was stock active)

---

### Data Transformation Functions

#### `_apply_standard_types(df: pd.DataFrame) -> pd.DataFrame`

**Description:** Apply standard type conversions to ensure data consistency.

**Signature:**
```python
def _apply_standard_types(df: pd.DataFrame) -> pd.DataFrame
```

**Parameters:**
- `df` (pd.DataFrame) → Input dataframe

**Returns:**
- `pd.DataFrame` → Input dataframe with converted columns

**Conversions Applied:**
```python
bse_code:    int → Int64 (nullable)
nse_code:    object → string
industry:    object → string
name:        object → string
```

**Example:**
```python
df = get_data_for_date("2026-03-19")  # Types may be mixed
df = _apply_standard_types(df)        # Normalize all types
print(df.dtypes)  # All correct types now
```

**Implementation Details:**
- ✓ Only modifies columns that exist
- ✓ Safe to call multiple times (idempotent)
- ✓ No data loss (coercion with errors="coerce")
- ✓ Used internally by all cached functions

---

#### `add_screener_links(df: pd.DataFrame) -> pd.DataFrame`

**Description:** Convert company names to clickable screener.in links.

**Signature:**
```python
def add_screener_links(df: pd.DataFrame) -> pd.DataFrame
```

**Parameters:**
- `df` (pd.DataFrame) → Must have columns: "name", "nse_code", "bse_code"

**Returns:**
- `pd.DataFrame` → Copy with "name" column replaced with HTML links

**Example:**
```python
df = get_data_for_date("2026-03-19")
df = add_screener_links(df)
# Now df["name"] contains HTML: <a href="...">Company Name</a>

# Display in Streamlit
st.markdown(df.to_html(escape=False), unsafe_allow_html=True)
```

**Link Generation Logic:**
```
1. Check if nse_code is valid (not NA, empty, NaN)
   ├─ YES → Link: https://screener.in/company/{nse_code}/
   └─ NO  → Check bse_code next

2. Check if bse_code is valid
   ├─ YES → Link: https://screener.in/company/{bse_code}/
   └─ NO  → Return plain company name (no link)

3. If no valid code found
   └─ Warn user: "⚠️ No NSE/BSE code for {name}"
```

**Invalid Code Examples:**
- Empty string: ""
- "NA", "N/A", "<NA>", "<N/A>"
- "NONE", "NAN"

**Usage Notes:**
- ✓ Must call before `st.markdown(..., unsafe_allow_html=True)`
- ✓ Returns a copy (doesn't modify original df)
- ✓ Safe for HTML rendering (uses href, not JavaScript)

---

## plot_utils.py

### Visualization Functions

#### `sector_heatmap(heat_df: pd.DataFrame, title: str) -> plotly.graph_objects.Figure`

**Description:** Create a static heatmap showing industry/sector momentum.

**Signature:**
```python
def sector_heatmap(heat_df: pd.DataFrame, title: str) -> plotly.graph_objects.Figure
```

**Parameters:**
- `heat_df` (pd.DataFrame) → Must have columns:
  - `industry` (str) → Industry name
  - `Count` (int) → Number of companies
  - `Avg_Gain_Percent` (float) → Average % gain
- `title` (str) → Chart title

**Returns:**
- `plotly.graph_objects.Figure` → Interactive heatmap

**Example:**
```python
df = get_historical_market_cap()
industry_summary = df.groupby("industry").agg({
    "name": "count",
    "%_gain_mc": "mean"
}).rename(columns={"name": "Count", "%_gain_mc": "Avg_Gain_Percent"})

fig = sector_heatmap(industry_summary, "Industry Momentum")
st.plotly_chart(fig, use_container_width=True)
```

**Chart Features:**
- X-axis: Industries
- Y-axis: Company count
- Color: Avg gain % (Green = positive, Red = negative)
- Height: 600px
- Hover: Shows industry, count, avg gain

**Color Scale:**
```
RdYlGn (Red-Yellow-Green):
├─ Red    (negative gain)
├─ Yellow (neutral)
└─ Green  (positive gain)
```

---

#### `animated_sector_heatmap(weekly_agg: pd.DataFrame, title: str) -> plotly.graph_objects.Figure`

**Description:** Create animated heatmap showing industry momentum evolution week-by-week.

**Signature:**
```python
def animated_sector_heatmap(weekly_agg: pd.DataFrame, title: str) -> plotly.graph_objects.Figure
```

**Parameters:**
- `weekly_agg` (pd.DataFrame) → Must have columns:
  - `industry` (str) → Industry name
  - `Count` (int) → Company count
  - `Avg_Gain_Percent` (float) → Average gain
  - `week` (str or int) → Week identifier (for animation)
- `title` (str) → Chart title

**Returns:**
- `plotly.graph_objects.Figure` → Animated heatmap with play controls

**Example:**
```python
df = get_historical_market_cap()
df["week"] = df["date"].dt.to_period("W")
weekly = df.groupby(["week", "industry"]).agg({
    "name": "count",
    "%_gain_mc": "mean"
}).reset_index()
weekly.columns = ["week", "industry", "Count", "Avg_Gain_Percent"]

fig = animated_sector_heatmap(weekly, "Weekly Industry Trends")
st.plotly_chart(fig, use_container_width=True)
```

**Animation Features:**
- Play/pause controls
- Frame slider
- Shows how industries rotate month-by-month
- Identify emerging/fading sectors

---

#### `market_cap_line_chart(stock_data: pd.DataFrame, company_name: str) -> plotly.graph_objects.Figure`

**Description:** Create line chart showing market cap evolution for a single stock.

**Signature:**
```python
def market_cap_line_chart(stock_data: pd.DataFrame, company_name: str) -> plotly.graph_objects.Figure
```

**Parameters:**
- `stock_data` (pd.DataFrame) → Must have columns:
  - `date` (datetime64) → Date
  - `market_cap` (float) → Market cap value
- `company_name` (str) → Company name (for title)

**Returns:**
- `plotly.graph_objects.Figure` → Interactive line chart

**Example:**
```python
df = get_historical_market_cap()
apple = df[df["name"] == "Apple"].sort_values("date")
fig = market_cap_line_chart(apple, "Apple Inc.")
st.plotly_chart(fig, use_container_width=True)
```

**Chart Features:**
- X-axis: Date (time-series)
- Y-axis: Market cap
- Markers: Points on each data
- Height: 500px
- Hover: Shows exact date and market cap

**Interactivity:**
- Zoom: Click & drag to zoom into time range
- Pan: Hold shift + drag to pan
- Reset: Double-click to reset view
- Legend: Click to toggle series

---

## config.py

### Constants

#### Database Configuration

```python
DB_PATH: str = "/path/to/highs.db"
```
- **Type:** str (absolute path)
- **Purpose:** Location of SQLite database file
- **Set by:** `Path(__file__).parent / "highs.db"`
- **Use:** All database functions reference this

---

#### Cache Configuration

```python
CACHE_TTL: int = 3600  # seconds
```
- **Type:** int
- **Purpose:** Time-to-live for cached data (1 hour)
- **Use:** All `@st.cache_data(ttl=CACHE_TTL)` decorators
- **Rationale:** Financial data updates daily, 1 hour is safe refresh rate

---

#### Table Names

```python
TABLE_HIGHS: str = "highs"
TABLE_FIVETOFIFTYCLUB: str = "fivetofiftyclub"
TABLE_DOWNFROMHIGH: str = "downfromhigh"
```
- **Type:** str
- **Purpose:** Centralize table name references (DRY principle)
- **Use:** Query building in db_utils.py
- **Benefit:** Change table names once, updates everywhere

---

#### Data Validation

```python
INVALID_CODES: set = {"", "NA", "<NA>", "<N/A>", "N/A", "NONE", "NAN"}
```
- **Type:** set (for fast O(1) lookups)
- **Purpose:** Invalid values for company codes
- **Use:** `add_screener_links()` validation
- **Examples:**
  - "" (empty string)
  - "NA", "N/A" (common null representations)
  - "NONE", "NAN" (alternative null values)

---

#### Column Type Mappings

```python
COLUMN_TYPES: dict = {
    "bse_code": "Int64",      # Nullable integer
    "nse_code": "string",     # pd.StringDtype
    "industry": "string",     # pd.StringDtype
    "name": "string",         # pd.StringDtype
}
```
- **Type:** dict
- **Purpose:** Standard type conversions
- **Use:** `_apply_standard_types()` function
- **Why nullable Int64:** BSE codes can be missing

---

#### Standard Columns

```python
STANDARD_COLUMNS: list = ["bse_code", "nse_code", "industry", "name"]
```
- **Type:** list[str]
- **Purpose:** Columns that appear in all main tables
- **Use:** Type consistency checks

---

#### Plot Configuration

```python
PLOT_HEIGHT: int = 600          # pixels
PLOT_COLOR_SCALE: str = "RdYlGn"  # Plotly color scale
```
- **Type:** int, str
- **Purpose:** Visual settings for charts
- **PLOT_HEIGHT:** Used in heatmaps and line charts
- **PLOT_COLOR_SCALE:** Red-Yellow-Green color scheme
  - Green = positive (good momentum)
  - Red = negative (poor momentum)

---

#### Analysis Windows

```python
ROLLING_WINDOWS: list = [7, 30, 60]  # days
```
- **Type:** list[int]
- **Purpose:** Rolling window periods for hit count analysis
- **Use:** `get_momentum_summary()` computes hits for each window
- **Meaning:**
  - 7-day: Recent momentum (current week)
  - 30-day: Medium-term momentum (current month)
  - 60-day: Consistency (2-month trend)

---

## Common Patterns

### Pattern 1: Get Data + Transform + Display

```python
# 1. Fetch data
df = get_data_for_date(selected_date)

# 2. Transform
df = compute_mcap_change(df)
df = add_screener_links(df)

# 3. Style
styled = df.style.apply(highlight_valuation_gradient, axis=1)

# 4. Display
st.markdown(styled.to_html(escape=False), unsafe_allow_html=True)
```

### Pattern 2: Query + Filter + Aggregate

```python
# 1. Get raw data
df = get_historical_market_cap()

# 2. Filter by date range
mask = (df["date"] >= start_date) & (df["date"] <= end_date)
df = df[mask]

# 3. Aggregate by industry
summary = df.groupby("industry").agg({
    "name": "count",
    "%_gain_mc": "mean"
})

# 4. Visualize
fig = sector_heatmap(summary, "Industry Performance")
st.plotly_chart(fig)
```

### Pattern 3: Cache with Error Handling

```python
@st.cache_data(ttl=CACHE_TTL)
def my_expensive_query() -> pd.DataFrame:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            df = pd.read_sql("SELECT ...", conn)
        df = _apply_standard_types(df)
        return df
    except sqlite3.Error as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame()
```

---

**Last Updated:** March 2026

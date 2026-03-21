# 📊 Detailed Workflows by Feature

## Overview

This document details the workflow and business logic for each view in the 52-Week High Tracker application.

---

## View 1: Within 5% of 52W High

**File:** `views/near_52w_high_view.py`

**Purpose:** Identify stocks trading near their 52-week peaks—potential breakout candidates with momentum.

### Workflow

```
┌─────────────────────────────────────────────────────────┐
│  1. PAGE INITIALIZATION                                 │
├─────────────────────────────────────────────────────────┤
│  • Title: "📈 Within 5% of 52W High"                    │
│  • Fetch all dates: get_all_dates()                     │
│  • Set date range limits (min_date, max_date available) │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│  2. DATE SELECTION MODE                                 │
├─────────────────────────────────────────────────────────┤
│  Radio button: "Single Date" | "Date Range" | "All"     │
│  ├─ Single Date: selectbox to pick one date             │
│  ├─ Date Range: date_input for start & end              │
│  └─ All Dates: use all available dates                  │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│  3. DATA FILTERING                                      │
├─────────────────────────────────────────────────────────┤
│  • Query database for selected date(s)                  │
│  • Result: DataFrame with columns:                      │
│    - name, nse_code, bse_code, P/E, P/BV               │
│    - market_cap, industry, etc.                         │
│  • Type conversion: _apply_standard_types()             │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│  4. DATA TRANSFORMATION                                 │
├─────────────────────────────────────────────────────────┤
│  • Add column: Δ% MCap (market cap change %)            │
│  • Add column: P/E (valuation metric)                   │
│  • Add column: P/BV (book value metric)                 │
│  • Apply type conversions                               │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│  5. DISPLAY OPTIONS                                     │
├─────────────────────────────────────────────────────────┤
│  Checkbox: "Use Chart View"?                            │
│  ├─ YES: Display animated sparkline chart               │
│  └─ NO: Display as table                                │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│  6. SORTING OPTIONS (for table view)                    │
├─────────────────────────────────────────────────────────┤
│  Radio: Sort by...                                      │
│  ├─ Company Name (alphabetical)                         │
│  ├─ Market Cap (largest first)                          │
│  ├─ P/E Ratio (lowest P/E first)                        │
│  ├─ P/BV Ratio (lowest P/BV first)                      │
│  └─ MCap Gain (highest gain first)                      │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│  7. ADD LINKS & STYLING                                 │
├─────────────────────────────────────────────────────────┤
│  • add_screener_links(): Convert names to clickable     │
│  • highlight_valuation_gradient(): Color P/E & P/BV    │
│  • Render as HTML: unsafe_allow_html=True              │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│  8. DISPLAY RESULTS                                     │
├─────────────────────────────────────────────────────────┤
│  st.markdown(styled_df.to_html(...))                    │
│  OR                                                      │
│  st.plotly_chart(sparkline_chart)                       │
└─────────────────────────────────────────────────────────┘
```

### Key Functions

| Function | Purpose |
|----------|---------|
| `get_all_dates()` | Fetch available dates from DB |
| `get_data_for_date(date)` | Fetch all stocks for a date |
| `compute_mcap_change(df)` | Calculate market cap % change |
| `add_screener_links(df)` | Add clickable company links |
| `highlight_valuation_gradient(row)` | Apply color styling |

### Data Flow

```
Database (highs table)
    ↓
get_data_for_date()
    ↓
DataFrame + Type Conversion
    ↓
Add Δ% MCap Column
    ↓
add_screener_links()
    ↓
highlight_valuation_gradient()
    ↓
st.markdown(HTML)
```

---

## View 2: 5–50% from 52W High

**File:** `views/pullback_candidates_view.py`

**Purpose:** Stocks that have corrected 5-50% from highs—balanced between pull back and recovery potential.

### Workflow

Nearly identical to View 1, but:
- Data sourced from `fivetofiftyclub` table instead of `highs`
- Uses `get_fivetofiftyclub_dates()` and `get_fivetofiftyclub_data_for_date()`
- Focus on correction % (how far down from 52-week high)

### Key Difference

```
View 1: Stocks NEAR 52W high (within 5%)
View 2: Stocks FAR from 52W high (5-50% correction)
View 3: Stocks VERY FAR from 52W high (50%+ correction)

          ↑ 52W High
          |
    View 1│ ████ (within 5%)
          |
    View 2│ ████████ (5-50% down)
          |
    View 3│ ██████████████ (50%+ down)
```

---

## View 3: Big Dippers (50%+ Down)

**File:** `views/deep_dippers_view.py`

**Purpose:** Deep value opportunities or distressed securities (down 50%+).

### Workflow

Similar structure but:
- Data from `downfromhigh` table
- Uses `get_downfromhigh_dates()` and `get_downfromhigh_data_for_date()`
- More focus on valuation metrics (P/E, P/BV are emphasized)

### Additional Features

```
┌─────────────────────────────────────────┐
│  Valuation Gradient Styling             │
├─────────────────────────────────────────┤
│  P/E Ratio:                              │
│  ├─ Green: Low P/E (0-20, attractive)   │
│  ├─ Yellow: Medium P/E (20-40)          │
│  └─ Red: High P/E (40-60, expensive)    │
│                                          │
│  P/BV Ratio:                             │
│  ├─ Green: Low P/BV (0-3, attractive)   │
│  ├─ Yellow: Medium (3-7)                │
│  └─ Red: High P/BV (7-12, expensive)    │
└─────────────────────────────────────────┘
```

### Error Handling

```
Type conversion issue fixed:
• P/E and P/BV may be strings
• Try: val = float(val)
• Except: Skip non-convertible values
• Result: No crashes on mixed types
```

---

## View 4: Trend Shift Analyzer

**File:** `views/trend_shift_view.py`

**Purpose:** Week-over-week momentum changes—identify accelerating or decelerating trends.

### Workflow

```
┌──────────────────────────────────────────────────────────┐
│  1. INITIALIZE                                           │
├──────────────────────────────────────────────────────────┤
│  • Get today's date                                      │
│  • Calculate: This Week (Mon-Sun)                        │
│  • Calculate: Last Week (Mon-Sun, 7 days prior)         │
│  • Fetch historical data: get_historical_market_cap()   │
└──────────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────┐
│  2. COMPUTE WEEKLY SUMMARIES                             │
├──────────────────────────────────────────────────────────┤
│  For THIS WEEK:                                          │
│  ├─ Group by company name                               │
│  ├─ Count hits (appearances in 52W high)                │
│  ├─ Get market cap at week start & end                  │
│  ├─ Calculate week gain %: (end - start) / start        │
│                                                          │
│  For LAST WEEK:                                          │
│  └─ Same aggregation as THIS WEEK                        │
└──────────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────┐
│  3. MERGE & CALCULATE DELTAS                             │
├──────────────────────────────────────────────────────────┤
│  • Outer join: this_week + last_week on company name    │
│  • Calculate: hits_delta = hits_this - hits_last        │
│  • Calculate: gain_delta = gain%_this - gain%_last      │
│  • Fill NaNs with 0 (company only in one week)          │
└──────────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────┐
│  4. MARKET CAP FILTERING                                 │
├──────────────────────────────────────────────────────────┤
│  • Convert market cap to ₹ Crores (÷ 10M)               │
│  • Create slider: min_cr → max_cr                       │
│  • Filter: market_cap_cr.between(slider_min, slider_max)│
│  • Rationale: Focus on specific market cap segments     │
└──────────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────┐
│  5. SORT & DISPLAY                                       │
├──────────────────────────────────────────────────────────┤
│  • Default sort: hits_delta (descending)                │
│  • Top rows: Companies accelerating (↑ hits this week)  │
│  • Bottom rows: Companies decelerating (↓ hits)         │
│  • Add links: add_screener_links(filtered_df)           │
│  • Display: HTML table with NSE/BSE links               │
└──────────────────────────────────────────────────────────┘
```

### Key Metrics

```
Column               | Meaning
─────────────────────┬─────────────────────────────
hits_this            | Count of 52W high hits THIS week
hits_last            | Count of 52W high hits LAST week
hits_delta (Δ Hits)  | this - last (positive = acceleration)
gain_pct_this        | % market cap change THIS week
gain_pct_last        | % market cap change LAST week
gain_delta (Δ Gain)  | this - last (positive = acceleration)
```

### Use Cases

```
Δ Hits > 0  → Stock gaining momentum (appeared more in highs)
Δ Hits < 0  → Stock losing momentum (fewer high appearances)
Δ Gain > 0  → Market cap growing faster than last week
Δ Gain < 0  → Market cap growth slowed down
```

---

## View 5: Emerging Winners

**File:** `views/emerging_winners_view.py`

**Purpose:** Identify momentum accelerators with rising valuations (high growth potential).

### Workflow

```
Combines trends from:
├─ Trend Shift (momentum acceleration check)
├─ Market Cap (valuation growth check)
└─ Frequency analysis (consistency check)

Score = 
  (Δ Hits > 0) +      // Momentum accelerating ✓
  (Δ Gain > 0) +      // Market cap growing ✓
  (Hits > threshold)  // Consistent momentum ✓
```

### Filters

- Market cap range (user slider)
- Minimum appearances in 52W highs (consistency)
- Industry focus (if selected)

### Output

Ranked by composite "momentum score"

---

## View 6: Trend Analyzer

**File:** `views/trend_analyzer_view.py`

**Purpose:** Long-term trend analysis with market cap evolution and valuation.

### Workflow

```
┌──────────────────────────────────────────┐
│  1. SELECT STOCK + DATE RANGE            │
├──────────────────────────────────────────┤
│  • Dropdown: Choose company              │
│  • Calendar range: Start → End date      │
└──────────────────────────────────────────┘
                  ↓
┌──────────────────────────────────────────┐
│  2. FETCH TIME-SERIES DATA               │
├──────────────────────────────────────────┤
│  • get_historical_market_cap()           │
│  • Filter: selected stock + date range   │
└──────────────────────────────────────────┘
                  ↓
┌──────────────────────────────────────────┐
│  3. VISUALIZE TRENDS                     │
├──────────────────────────────────────────┤
│  • Chart 1: Market cap over time         │
│  • Chart 2: P/E ratio over time          │
│  • Chart 3: P/BV ratio over time         │
│  • Use: plot_utils.market_cap_line_chart()│
└──────────────────────────────────────────┘
                  ↓
┌──────────────────────────────────────────┐
│  4. COMPUTE SUMMARY STATISTICS           │
├──────────────────────────────────────────┤
│  • Min/max market cap                    │
│  • Total growth %                        │
│  • Avg P/E, avg P/BV                     │
│  • Days in 52W highs                     │
└──────────────────────────────────────────┘
                  ↓
┌──────────────────────────────────────────┐
│  5. DISPLAY RESULTS                      │
├──────────────────────────────────────────┤
│  • Interactive charts (Plotly)           │
│  • Summary metrics (st.metric cards)     │
│  • Data table with link to Screener.in   │
└──────────────────────────────────────────┘
```

---

## View 7: Industry Tailwinds

**File:** `views/industry_tailwinds_view.py`

**Purpose:** Sector-level analysis of momentum trends.

### Workflow

```
┌──────────────────────────────────────────┐
│  1. INITIALIZE                           │
├──────────────────────────────────────────┤
│  • Fetch all historical data             │
│  • Extract industries from data          │
│  • Get all unique dates                  │
└──────────────────────────────────────────┘
                  ↓
┌──────────────────────────────────────────┐
│  2. AGGREGATE BY INDUSTRY                │
├──────────────────────────────────────────┤
│  For EACH industry:                      │
│  ├─ Count companies hitting 52W high     │
│  ├─ Avg market cap growth %              │
│  └─ Total market cap                     │
└──────────────────────────────────────────┘
                  ↓
┌──────────────────────────────────────────┐
│  3. CREATE VISUALIZATIONS                │
├──────────────────────────────────────────┤
│  • Static heatmap: Industry momentum     │
│  • Animated heatmap: Week-by-week        │
│  • Color: Green (strong) → Red (weak)    │
└──────────────────────────────────────────┘
                  ↓
┌──────────────────────────────────────────┐
│  4. DISPLAY RESULTS                      │
├──────────────────────────────────────────┤
│  • Industry performance heatmap          │
│  • Rankings (best/worst sectors)         │
│  • Historical comparison (animated)      │
└──────────────────────────────────────────┘
```

### Key Insights

```
Hot Industries (many highs, high growth):
→ Indicates sector rotation/tailwinds
→ Consider industry-wide momentum plays

Cold Industries (few highs, negative growth):
→ Sector headwinds
→ Avoid unless specific company opportunity
```

---

## View 8: Momentum Summary

**File:** `views/momentum_summary_view.py`

**Purpose:** Snapshot of which stocks appear most frequently in 52W highs.

### Workflow

```
┌──────────────────────────────────────────┐
│  1. COMPUTE ROLLING HIT COUNTS           │
├──────────────────────────────────────────┤
│  For 7-day window:                       │
│  └─ Count occurrences in highs table     │
│                                          │
│  For 30-day window:                      │
│  └─ Count occurrences in highs table     │
│                                          │
│  For 60-day window:                      │
│  └─ Count occurrences in highs table     │
└──────────────────────────────────────────┘
                  ↓
┌──────────────────────────────────────────┐
│  2. GET LATEST SNAPSHOT                  │
├──────────────────────────────────────────┤
│  • Latest date for each company          │
│  • Current market cap                    │
│  • First market cap (when first seen)    │
│  • Industry, NSE/BSE codes               │
└──────────────────────────────────────────┘
                  ↓
┌──────────────────────────────────────────┐
│  3. CALCULATE VALUATIONS                 │
├──────────────────────────────────────────┤
│  • % Gain MCap = (current - first) / first├─ Times stock has appreciated since first│
│    appearing in highs                    │
└──────────────────────────────────────────┘
                  ↓
┌──────────────────────────────────────────┐
│  4. BUILD SUMMARY TABLE                  │
├──────────────────────────────────────────┤
│  Columns:                                │
│  ├─ Company Name (with screener link)    │
│  ├─ Industry                             │
│  ├─ Hits 7-day (frequency)               │
│  ├─ Hits 30-day (momentum)               │
│  ├─ Hits 60-day (consistency)            │
│  ├─ Market Cap (size)                    │
│  └─ % Gain (appreciation)                │
└──────────────────────────────────────────┘
                  ↓
┌──────────────────────────────────────────┐
│  5. SORT & FILTER                        │
├──────────────────────────────────────────┤
│  • Sort by: Hits 7-day (default)         │
│  • Filter sidebar: Industry, Cap range   │
│  • Result: Top momentum stocks           │
└──────────────────────────────────────────┘
                  ↓
┌──────────────────────────────────────────┐
│  6. DISPLAY RESULTS                      │
├──────────────────────────────────────────┤
│  • Interactive dataframe                 │
│  • Sparkline charts (if available)       │
│  • Screener.in links for deep dives      │
└──────────────────────────────────────────┘
```

### Interpretation

```
High Hits 7-day:  Stock in momentum NOW (current strength)
High Hits 30-day: Sustained momentum (medium-term trend)
High Hits 60-day: Consistent performer (proven track record)

High % Gain:      Stock appreciated since first appearance
                  (usually correlated with being in highs)

No. of Hits > Market Cap correlation:
  If small-cap with many hits → undervalued momentum
  If large-cap with many hits → quality momentum
```

---

## View 9: Multi-Bagger Hunt

**File:** `views/multi_bagger_hunt_view.py`

**Purpose:** Rank stocks by persistence in 52-week highs—identify potential multi-baggers.

### Workflow

```
┌──────────────────────────────────────────────────────────┐
│  1. CALCULATE PERSISTENCE SCORES                         │
├──────────────────────────────────────────────────────────┤
│  For EACH stock:                                         │
│  ├─ Count total appearances in highs table              │
│  ├─ Weight recent appearances (7-day) higher            │
│  ├─ Calculate acceleration (trend direction)            │
│  └─ Compute persistence_score = weighted frequency      │
└──────────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────┐
│  2. GATHER MARKET DATA                                   │
├──────────────────────────────────────────────────────────┤
│  • Current market cap                                    │
│  • First market cap (when first seen in highs)          │
│  • First seen date                                       │
│  • Industry classification                              │
│  • Frequency timeline (hits over last 12 weeks)         │
└──────────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────┐
│  3. APPLY FILTERS                                        │
├──────────────────────────────────────────────────────────┤
│  • Minimum hits in 7 days (e.g., 2+)                    │
│  • Minimum persistence score (e.g., 20+)               │
│  • Market cap range (sidebar slider)                    │
│  • Industry filter (optional)                           │
└──────────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────┐
│  4. DISPLAY CANDIDATES                                   │
├──────────────────────────────────────────────────────────┤
│  • Ranked by persistence score (descending)            │
│  • Show frequency timeline chart (12-week history)      │
│  • Interactive grid with:                               │
│    ├─ Company name (with screener link)                │
│    ├─ Industry                                          │
│    ├─ Hits 7D / 30D (frequency metrics)                │
│    ├─ Persistence Score (composite metric)             │
│    ├─ Market cap                                        │
│    └─ Appreciation %                                    │
└──────────────────────────────────────────────────────────┘
```

### Key Concept

**Persistence Score** = Measure of how consistently a stock appears in 52W highs

```
High Persistence + Recent Acceleration = Potential Multi-Bagger
├─ Proven track record in 52W highs
├─ Momentum accelerating (more hits recently)
└─ Early stages of potential significant rally
```

### Use Cases

```
Use this view to find:
✓ Stocks with proven high momentum (persistent winners)
✓ Companies accelerating momentum (rising from baseline)
✓ Quality stocks at inflection points (ready to run)
✓ Candidates for medium to long-term holding
```

---

## View 10: Trend Analyzer (Consistent Performers)

**File:** `views/trend_analyzer_view.py`

**Purpose:** Identify consistent performers using non-overlapping time buckets.

### Workflow

```
┌──────────────────────────────────────────────────────────┐
│  1. CALCULATE FREQUENCY BUCKETS                          │
├──────────────────────────────────────────────────────────┤
│  For EACH company:                                       │
│  ├─ Hits 0-7D   = appearances in last 7 days           │
│  ├─ Hits 8-30D  = appearances in days 8-30 (no overlap)│
│  └─ Hits 31-60D = appearances in days 31-60 (no overlap)│
│                                                          │
│  This shows trend direction:                            │
│  ├─ If Hits 0-7D > Hits 8-30D → ACCELERATING ✓        │
│  └─ If Hits 0-7D < Hits 8-30D → DECELERATING ✗        │
└──────────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────┐
│  2. COMPUTE TREND SCORE                                  │
├──────────────────────────────────────────────────────────┤
│  Trend Score = (Hits 0-7D × 3) +                        │
│                (Hits 8-30D × 2) +                       │
│                (Hits 31-60D × 1)                        │
│                                                          │
│  Rationale: Weight recent hits more heavily            │
│  ├─ Recent weeks = 3x multiplier (highest importance)  │
│  ├─ Medium weeks = 2x multiplier                       │
│  └─ Older weeks = 1x multiplier (baseline)             │
└──────────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────┐
│  3. COMPUTE ACCELERATION                                 │
├──────────────────────────────────────────────────────────┤
│  Acceleration = (Hits 0-7D ÷ 7) - (Hits 8-30D ÷ 23)   │
│                                                          │
│  Daily comparison:                                       │
│  ├─ Positive = stock getting hits more frequently now  │
│  ├─ Negative = getting hits less frequently than before│
│  └─ Used as secondary sort criterion                   │
└──────────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────┐
│  4. FILTER & SORT                                        │
├──────────────────────────────────────────────────────────┤
│  • Filter: hits_7 > 0 (must have recent activity)       │
│  • Primary sort: Trend Score (descending)               │
│  • Secondary sort: Acceleration (descending)            │
│  • Tertiary sort: % Gain (descending)                   │
└──────────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────┐
│  5. DISPLAY RESULTS                                      │
├──────────────────────────────────────────────────────────┤
│  • Interactive grid with:                               │
│    ├─ Company name (screener link)                      │
│    ├─ Industry                                          │
│    ├─ Market Cap (colored by magnitude)                │
│    ├─ Hits 0-7D / 8-30D / 31-60D (colored bars)       │
│    ├─ Trend Score (composite metric)                   │
│    ├─ Acceleration (trend direction)                   │
│    └─ % Market Cap Gain                                │
│                                                          │
│  • Explanation caption with formula                    │
│  • Threshold: Only stocks with recent hits shown       │
└──────────────────────────────────────────────────────────┘
```

### Key Metrics Explained

```
Trend Score (0 to ∞):
  Higher = More frequent recent appearances in highs
  ~10+ = High confidence consistent performer
  ~5-10 = Moderate consistency
  ~1-5 = Lower consistency

Acceleration (-∞ to +∞):
  Positive = Momentum accelerating
  Negative = Momentum decelerating
  Near 0 = Steady state (no acceleration)

Example:
  Stock A: Hits 0-7D=5, 8-30D=2, 31-60D=1
  Score = (5×3) + (2×2) + (1×1) = 20
  Acceleration = (5÷7) - (2÷23) ≈ 0.624 (accelerating)

  Stock B: Hits 0-7D=1, 8-30D=5, 31-60D=3
  Score = (1×3) + (5×2) + (3×1) = 16
  Acceleration = (1÷7) - (5÷23) ≈ -0.142 (decelerating)
  → Stock A ranked higher (better score + accelerating)
```

---

## View 11: Start Here

**File:** `views/start_here_view.py`

**Purpose:** Dashboard overview and getting started guide for new users.

### Workflow

```
┌──────────────────────────────────────────────────────────┐
│  1. DASHBOARD INITIALIZATION                             │
├──────────────────────────────────────────────────────────┤
│  • Display welcome message                              │
│  • Show last data update timestamp                      │
│  • Provide getting started instructions                 │
└──────────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────┐
│  2. DISPLAY KEY METRICS                                  │
├──────────────────────────────────────────────────────────┤
│  • Total companies in 52W highs (all-time)              │
│  • Companies this week (recent)                          │
│  • Most common industries (sector focus)                │
│  • Top performers (by market cap appreciation)          │
└──────────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────┐
│  3. SHOW KEY SNAPSHOTS                                   │
├──────────────────────────────────────────────────────────┤
│  Tab 1: Trend Shift Snapshot                            │
│  ├─ Companies accelerating this week                    │
│  ├─ Top 5-8 rising stocks                               │
│  └─ Compare vs last week                                │
│                                                          │
│  Tab 2: Emerging Winners                                │
│  ├─ New entrants with momentum                          │
│  ├─ Showing strong gains                                │
│  └─ High growth potential candidates                    │
│                                                          │
│  Tab 3: Industry Rotation                               │
│  ├─ Hot industries this week                            │
│  ├─ Cold industries (potential shorts)                  │
│  └─ Sector momentum shifts                              │
└──────────────────────────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────┐
│  4. DISPLAY NAVIGATION GUIDE                             │
├──────────────────────────────────────────────────────────┤
│ Explain each page in sidebar:                            │
│  • How to use each view                                 │
│  • What questions each answers                          │
│  • Typical investment workflows                         │
└──────────────────────────────────────────────────────────┘
```

### Key Content Sections

```
1. INTRODUCTION
   "Welcome to 52-Week High Tracker"
   → Explain what the app does
   → Show how to interpret the data

2. QUICK START TABS
   ├─ Trend Shift: What's accelerating NOW
   ├─ Emerging Winners: New high-momentum stocks
   └─ Industry Tailwinds: Sector rotation trends

3. NAVIGATION GUIDE
   Each page explained with:
   • Title and emoji
   • What it shows
   • How to interpret results
   • Best use cases

4. HELP & DEFINITIONS
   • What = 52-week high
   • Why = Track momentum stocks
   • How = Use each view
```

### Purpose

Entry point for:
✓ New users learning the app
✓ Understanding data relationship
✓ Choosing which view to explore
✓ Getting investing inspiration

---

## Cross-View Patterns

### Data Fetching Pattern

All views follow this pattern:

```python
def main():
    # 1. Get dates or raw data
    dates = get_all_dates()  # or get_data_for_date(date)
    
    # 2. Display filters
    selected_date = st.selectbox("Pick date", dates)
    
    # 3. Query database
    df = get_data_for_date(selected_date)
    
    # 4. Transform
    df = compute_mcap_change(df)
    df = add_screener_links(df)
    
    # 5. Style
    styled_df = df.style.apply(highlight_valuation_gradient, axis=1)
    
    # 6. Display
    st.markdown(styled_df.to_html(...), unsafe_allow_html=True)
```

### Filtering Pattern

```python
# Market cap range slider
min_cr, max_cr = st.sidebar.slider(
    "Market Cap (₹ Cr)",
    min_value=int(df["market_cap_cr"].min()),
    max_value=int(df["market_cap_cr"].max()),
    value=(int(df["market_cap_cr"].min()), int(df["market_cap_cr"].max()))
)
df = df[df["market_cap_cr"].between(min_cr, max_cr)]

# Industry filter
industries = ["All"] + sorted(df["industry"].unique())
selected_industry = st.sidebar.selectbox("Industry", industries)
if selected_industry != "All":
    df = df[df["industry"] == selected_industry]
```

---

## Summary

| View | Data Source | Key Metric | User Action |
|------|-------------|-----------|-------------|
| Within 5% | `highs` | Proximity to 52W high | Find breakout candidates |
| 5-50% Down | `fivetofiftyclub` | Correction % | Find recovery plays |
| 50%+ Down | `downfromhigh` | Deep correction | Find deep value or distressed |
| Trend Shift | `highs` time-series | Δ Hits, Δ Gain | Identify acceleration |
| Emerging Winners | Combined | Momentum + Valuation | Find quality growth |
| Trend Analyzer | `highs` time-series | Market cap chart | Analyze individual stock |
| Industry Tailwinds | `highs` by industry | Industry momentum | Sector rotation plays |
| Momentum Summary | `highs` aggregated | Hit frequency | Top momentum stocks |

---

**Last Updated:** March 2026

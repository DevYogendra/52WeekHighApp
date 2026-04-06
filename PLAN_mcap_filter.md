# Plan: Global MCap Tier Filter Across All Views

**Goal:** Add a consistent, color-coded Market Cap tier filter to every view in the app.

---

## Phase 0 — Discovery Findings (Complete)

### Allowed APIs (verified from source)

| API | File | Lines | Notes |
|-----|------|-------|-------|
| `st.sidebar.multiselect()` | not yet used — valid Streamlit API | — | Returns `list[str]` |
| `st.column_config.NumberColumn(format="%.0f")` | grid_utils.py | 121–124 | Used by `major_cols` |
| `render_interactive_table(..., major_cols=[...])` | grid_utils.py | 41–55 | Accepts new `columns` |
| `df[col].between(lo, hi)` | price_position_view.py | 239 | Existing MCap range pattern |

### Key facts
- `market_cap` column is in **₹ Crores** everywhere — no unit conversion needed.
- Sidebar is **per-view** (not shared). Each view module owns its sidebar section.
- `st.multiselect` and `st.checkbox` are **not used anywhere yet** — safe to introduce.
- The existing IM Score "MCap tier filter" selectbox (momentum_view.py:316–325) is **broken** — `market_cap_tier` column is never computed. Must be fixed.
- `get_im_momentum_scores()` (db_utils.py:391–483) returns a dataframe that already has `market_cap`; just needs `market_cap_tier` added.

### Anti-patterns to avoid
- Do NOT add a `st.sidebar.slider` for raw MCap range — the user wants discrete tier checkboxes/multiselect.
- Do NOT invent a `market_cap_cr` alias — the column is already named `market_cap` in Crores.
- Do NOT add tier filtering inside `render_interactive_table` — keep it in each view before the call.

---

## Design Decisions (Recommended — confirm before coding)

### 1. Widget: `st.multiselect` (recommended over individual checkboxes)

```python
selected_tiers = st.sidebar.multiselect(
    "MCap Tier",
    options=["🔴 Micro", "🟠 Small", "🟡 Mid", "🟢 Large", "🔵 Mega"],
    default=["🔴 Micro", "🟠 Small", "🟡 Mid", "🟢 Large", "🔵 Mega"],
    key="mcap_tier_filter",
)
```

**Why multiselect over checkboxes:**
- 5 checkboxes would occupy ~5 sidebar lines; one multiselect is 1 line collapsed.
- Supports "select all" via default. User deselects tiers they don't want.
- Already the Streamlit-native pattern for multi-option filtering.

### 2. Tier Thresholds

| Emoji | Label | Range (₹ Cr) | Screener.in equivalent |
|-------|-------|-------------|------------------------|
| 🔴 | Micro | 0 – 1,000 | Small Cap fringe |
| 🟠 | Small | 1,000 – 5,000 | Small Cap |
| 🟡 | Mid | 5,000 – 25,000 | Mid Cap |
| 🟢 | Large | 25,000 – 1,00,000 | Large Cap |
| 🔵 | Mega | > 1,00,000 | Nifty 50 territory |

### 3. Colors in the table

Streamlit's `st.dataframe` does not support cell background colors natively.
**Recommended approach:** Add a computed `"Tier"` column to each table displaying the emoji + label (e.g., `"🟡 Mid"`). This gives instant visual scanning without hacks.

**Optional advanced:** Use `df.style.apply()` with `st.dataframe(df.style...)` for row-level background shading — heavier but works. Defer unless user wants it.

---

## Phase 1 — Shared MCap Tier Utility

**Create:** `52WeekHighApp/mcap_tier_utils.py`

**What to implement:**

```python
# Thresholds in ₹ Crores
MCAP_TIERS = [
    ("🔴 Micro",  0,         1_000),
    ("🟠 Small",  1_000,     5_000),
    ("🟡 Mid",    5_000,    25_000),
    ("🟢 Large", 25_000,  1_00_000),
    ("🔵 Mega", 1_00_000, float("inf")),
]
TIER_LABELS = [t[0] for t in MCAP_TIERS]

def get_mcap_tier(market_cap_cr) -> str:
    """Return emoji+label tier for a ₹Cr value. NA/0 → '🔴 Micro'."""
    ...

def add_mcap_tier_col(df, col="market_cap", out_col="mcap_tier") -> pd.DataFrame:
    """Add a tier column to df based on col. Returns df with new column."""
    ...

def render_mcap_sidebar_filter(key: str) -> list[str]:
    """Render multiselect in sidebar; returns selected tier labels (all by default)."""
    return st.sidebar.multiselect("MCap Tier", TIER_LABELS, default=TIER_LABELS, key=key)

def apply_mcap_tier_filter(df, selected_tiers, tier_col="mcap_tier") -> pd.DataFrame:
    """Filter df to rows whose tier_col is in selected_tiers. No-op if all selected."""
    if len(selected_tiers) == len(TIER_LABELS):
        return df
    return df[df[tier_col].isin(selected_tiers)]
```

**Verification:**
- `get_mcap_tier(500)` → `"🔴 Micro"`
- `get_mcap_tier(3000)` → `"🟠 Small"`
- `get_mcap_tier(pd.NA)` → `"🔴 Micro"` (safe default)
- `add_mcap_tier_col(df)` adds column without dropping rows

**Anti-pattern guards:**
- Do NOT use the old SMALL/MID/LARGE/MEGA names from im-momentum — use the 5 new labels
- Do NOT store tier as int — string label is displayable directly

---

## Phase 2 — Fix Broken IM Score Tier Filter

**File:** `52WeekHighApp/db_utils.py` lines 469–483 (`get_im_momentum_scores`)
**File:** `52WeekHighApp/views/momentum_view.py` lines 293–349 (`_render_im_score`)

### db_utils.py change
After computing `im_composite` (line 473), add:
```python
from mcap_tier_utils import add_mcap_tier_col
df = add_mcap_tier_col(df, col="market_cap", out_col="mcap_tier")
```

### momentum_view.py change
Replace the broken selectbox (lines 316–325) with:
```python
from mcap_tier_utils import render_mcap_sidebar_filter, apply_mcap_tier_filter

selected_tiers = render_mcap_sidebar_filter(key="im_mcap_tier")
filtered = df[df["im_composite"] >= min_composite]
filtered = apply_mcap_tier_filter(filtered, selected_tiers)
```

Also add `"mcap_tier"` to `columns` list and `rename_map` in `render_interactive_table` call:
```python
columns=[..., "mcap_tier", ...],
rename_map={..., "mcap_tier": "Tier", ...},
```

**Verification:**
- Selecting "🔵 Mega" only → only companies with market_cap > 1,00,000 Cr appear
- Selecting all → same as before

---

## Phase 3 — Add Filter to Remaining Momentum Tabs

**File:** `52WeekHighApp/views/momentum_view.py`

Each tab's render function gets the same pattern — call `render_mcap_sidebar_filter(key=...)` then `apply_mcap_tier_filter(df, ...)`. Add `mcap_tier` to the table columns.

### 3a — Trend Leaders (`_render_trend_leaders`, lines ~60–120)
- Data source: `get_momentum_summary()` → has `market_cap`
- Add `add_mcap_tier_col()` after data load
- Add `render_mcap_sidebar_filter(key="tl_mcap_tier")` to sidebar (after existing industry filter)
- Filter before `render_interactive_table`
- Add `"mcap_tier": "Tier"` to table columns

### 3b — New Breakouts (`_render_new_breakouts`, lines ~125–190)
- Same pattern; key = `"nb_mcap_tier"`

### 3c — Weekly Shift (`_render_weekly_shift`, lines ~191–250)
- Data source: weekly comparison df → has `market_cap_end_this`; use that column, rename to `market_cap` for tier computation or pass `col="market_cap_end_this"` to `add_mcap_tier_col`
- Key = `"ws_mcap_tier"`

### 3d — Persistence (`_render_persistence`, lines ~251–290)
- Data source: `get_persistence_scores()` → has `market_cap`
- Key = `"ps_mcap_tier"`

**Verification for each tab:**
- With no tiers selected → `st.info("No matching data.")` (via `render_interactive_table` empty-df guard at grid_utils.py:56)
- With all tiers → full list unchanged

---

## Phase 4 — Add Filter to Other Views

### 4a — Start Here (`start_here_view.py`)
- Has two tables: "Best Current Momentum" and "Rising This Week"
- Both come from `get_momentum_summary()` which includes `market_cap`
- Add `add_mcap_tier_col()` after data load in `main()`
- Add single `render_mcap_sidebar_filter(key="sh_mcap_tier")` — apply to both tables
- Key = `"sh_mcap_tier"`

### 4b — Price Position (`price_position_view.py`)
- Uses existing market cap slider (lines 233–239) in main content area — **keep it**
- Add tier multiselect to sidebar (currently this view has no sidebar filters at all)
- After bucket split, apply tier filter to each bucket's `df`
- Key = `"pp_mcap_tier"`
- `add_mcap_tier_col()` call on the main df before bucket split

### 4c — Industry Tailwinds (`industry_tailwinds_view.py`)
- Summary table is industry-aggregated (no per-stock market_cap)
- Detail expanders do have per-stock `market_cap`
- **Approach:** Filter the raw stock-level data before aggregation — requires calling `add_mcap_tier_col()` and `apply_mcap_tier_filter()` inside or before `get_tailwind_stocks()` call, OR post-filter the detail tables inside each expander
- **Simpler approach:** Post-filter the per-stock detail table inside each expander (summary counts will still reflect all stocks — note this in a `st.caption`)
- Key = `"tw_mcap_tier"`

---

## Phase 5 — Tier Column Display & Colors

**Scope:** Add `"Tier"` column with emoji label to all tables where `mcap_tier` is included.

The `render_interactive_table` will display `mcap_tier` as "Tier" via `rename_map`. No additional grid_utils changes needed — it will render as a plain string column.

**Optional enhancement (defer unless requested):** Row-level background shading using `df.style`:
```python
TIER_COLORS = {
    "🔴 Micro":  "#fff0f0",
    "🟠 Small":  "#fff5e6",
    "🟡 Mid":    "#fffde6",
    "🟢 Large":  "#f0fff4",
    "🔵 Mega":   "#e6f0ff",
}
def color_tier_rows(row):
    color = TIER_COLORS.get(row.get("Tier", ""), "")
    return [f"background-color: {color}"] * len(row)
```
This requires switching from `render_interactive_table` to direct `st.dataframe(df.style.apply(...))` — more invasive. **Recommend: emoji-only column first; add row colors as follow-up if user wants.**

---

## Phase 6 — Verification Checklist

- [ ] `mcap_tier_utils.py` has 100% coverage of edge cases (NA, 0, exact boundary values)
- [ ] Grep for old broken tier filter: `"market_cap_tier"` should only appear in `mcap_tier_utils.py` and one location in each view (not in `get_im_momentum_scores`)
- [ ] All 7 sidebar filter keys are unique (no Streamlit key collision): `im_mcap_tier`, `tl_mcap_tier`, `nb_mcap_tier`, `ws_mcap_tier`, `ps_mcap_tier`, `sh_mcap_tier`, `pp_mcap_tier`, `tw_mcap_tier`
- [ ] Deselecting all tiers shows empty table (not an error)
- [ ] Selecting "🔵 Mega" on Start Here → only Nifty 50-scale companies visible
- [ ] Price Position: existing market cap slider still works independently of tier filter
- [ ] Industry Tailwinds: `st.caption` explains tier filter applies to detail view only

---

## Implementation Order

1. Phase 1 (utility) — standalone, no dependencies
2. Phase 2 (fix IM Score) — depends on Phase 1
3. Phase 3 (momentum tabs) — depends on Phase 1
4. Phase 4 (other views) — depends on Phase 1
5. Phase 5 (Tier column display) — included in Phases 2–4, no separate pass needed
6. Phase 6 (verify) — final

Phases 2, 3, and 4 can be executed in parallel once Phase 1 is done.

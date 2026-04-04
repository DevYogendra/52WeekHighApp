# views/price_position_view.py
# Consolidates: near_52w_high_view, pullback_candidates_view, deep_dippers_view

import pandas as pd
import streamlit as st
from dateutil.relativedelta import relativedelta

from db_utils import (
    get_all_dates,
    get_data_for_date,
    get_downfromhigh_data_for_date,
    get_downfromhigh_dates,
    get_fivetofiftyclub_data_for_date,
    get_fivetofiftyclub_dates,
    get_historical_market_cap,
)
from grid_utils import render_interactive_table
from views.bucket_view_utils import (
    BUCKET_MAJOR_COLS,
    BUCKET_ONE_DECIMAL_COLS,
    BUCKET_TWO_DECIMAL_COLS,
    COMMON_RENAME_MAP,
    DETAILED_COLS,
    FOCUSED_COLS,
    compute_mcap_change,
    load_first_caps,
    prepare_grid_df,
)


# ── bucket configuration ──────────────────────────────────────────────────────

BUCKETS = {
    "Near High (0–5%)": {
        "caption": "Leadership names near highs. Rank by valuation, quality, and market-cap trend.",
        "get_dates": get_all_dates,
        "get_data":  get_data_for_date,
        "filename":  "near_high",
        "sort_options": {
            "Lowest P/E":           ("P/E", True),
            "Lowest P/BV":          ("P/BV", True),
            "Highest MCap":         ("MCap", False),
            "Highest Δ% MCap":      ("Δ% MCap", False),
            "Closest to 52W High":  ("↓52W High%", True),
            "Highest ROE":          ("ROE", False),
            "Highest Earnings Yield": ("Earnings Yield", False),
            "Alphabetical":         ("Name", True),
        },
    },
    "Pullback (5–50%)": {
        "caption": "Pullback watchlist. Names correcting from highs — evaluate for recovery or re-entry.",
        "get_dates": get_fivetofiftyclub_dates,
        "get_data":  get_fivetofiftyclub_data_for_date,
        "filename":  "pullback",
        "sort_options": {
            "Closest Recovery Setup": ("↓52W High%", True),
            "Lowest P/E":             ("P/E", True),
            "Lowest P/BV":            ("P/BV", True),
            "Highest ROE":            ("ROE", False),
            "Highest Δ% MCap":        ("Δ% MCap", False),
            "Highest MCap":           ("MCap", False),
            "Alphabetical":           ("Name", True),
        },
    },
    "Deep Dippers (50%+)": {
        "caption": "Distressed / deep-value triage. Separate cheap-looking names from genuinely improving businesses.",
        "get_dates": get_downfromhigh_dates,
        "get_data":  get_downfromhigh_data_for_date,
        "filename":  "deep_dippers",
        "sort_options": {
            "Deepest Discount":       ("↓52W High%", True),
            "Lowest P/E":             ("P/E", True),
            "Lowest P/BV":            ("P/BV", True),
            "Highest Earnings Yield": ("Earnings Yield", False),
            "Highest ROE":            ("ROE", False),
            "Highest MCap":           ("MCap", False),
            "Alphabetical":           ("Name", True),
        },
    },
}


# ── shared data loading ───────────────────────────────────────────────────────

def _load_data(bucket_cfg: dict) -> pd.DataFrame:
    """Load and deduplicate data for the chosen date mode."""
    get_dates = bucket_cfg["get_dates"]
    get_data  = bucket_cfg["get_data"]

    raw_dates = get_dates()
    if not raw_dates:
        st.warning("No data available.")
        return pd.DataFrame()

    dates = sorted([pd.to_datetime(d).date() for d in raw_dates])
    min_date = dates[0]
    max_date = dates[-1]

    date_mode = st.radio("Date mode", ["Single Date", "Date Range", "All Dates"], index=1, key="pp_date_mode")

    if date_mode == "Single Date":
        selected = st.selectbox("Date", dates, index=len(dates) - 1,
                                format_func=lambda d: d.strftime("%Y-%m-%d"), key="pp_single_date")
        df = get_data(selected.strftime("%Y-%m-%d"))
        date_info = selected.strftime("%Y-%m-%d")

    elif date_mode == "Date Range":
        col1, col2 = st.columns([1, 2])
        with col1:
            method = st.radio("Define by", ("Presets", "Last N days", "Last N months"), key="pp_range_method")
        with col2:
            if method == "Presets":
                preset = st.radio("Preset", ("1 Day", "Last 7 Days", "Last 14 Days",
                                             "Last 1 Month", "Last 3 Months", "Last 6 Months"), key="pp_preset")
                deltas = {
                    "1 Day": relativedelta(days=0),
                    "Last 7 Days": relativedelta(days=6),
                    "Last 14 Days": relativedelta(days=13),
                    "Last 1 Month": relativedelta(months=1),
                    "Last 3 Months": relativedelta(months=3),
                    "Last 6 Months": relativedelta(months=6),
                }
                start_default = max_date - deltas[preset]
            elif method == "Last N days":
                n = st.number_input("Days", min_value=1, value=7, key="pp_ndays")
                start_default = max_date - relativedelta(days=n - 1)
            else:
                n = st.number_input("Months", min_value=1, value=3, key="pp_nmonths")
                start_default = max_date - relativedelta(months=n)

        start_default = max(start_default, min_date)
        start = st.date_input("Start", value=start_default, min_value=min_date, max_value=max_date, key="pp_start")
        end   = st.date_input("End",   value=max_date,      min_value=min_date, max_value=max_date, key="pp_end")

        if start > end:
            st.error("Start date must be before or equal to end date.")
            return pd.DataFrame()

        selected_dates = [d.strftime("%Y-%m-%d") for d in dates if start <= d <= end]
        if not selected_dates:
            st.warning("No data in the selected date range.")
            return pd.DataFrame()

        dfs = [get_data(d) for d in selected_dates]
        df = pd.concat(dfs, ignore_index=True)
        if not df.empty and "name" in df.columns and "date" in df.columns:
            df = (df.sort_values(["name", "date"])
                    .drop_duplicates(subset=["name"], keep="last")
                    .reset_index(drop=True))
        date_info = f"{start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}"

    else:  # All Dates
        all_dates_str = [d.strftime("%Y-%m-%d") for d in dates]
        dfs = [get_data(d) for d in all_dates_str]
        all_df = pd.concat(dfs, ignore_index=True)
        all_df["date"] = pd.to_datetime(all_df["date"]).dt.date

        first_caps = (
            all_df.sort_values(["name", "date"])
                  .groupby("name", as_index=False)
                  .first()[["name", "market_cap", "date"]]
                  .rename(columns={"market_cap": "first_market_cap", "date": "first_seen_date"})
        )
        last_caps = (
            all_df.sort_values(["name", "date"])
                  .groupby("name", as_index=False)
                  .last()
                  .drop(columns=["first_seen_date", "first_market_cap"], errors="ignore")
        )
        df = last_caps.merge(first_caps, on="name", how="left")
        for col in ["date", "first_seen_date"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col]).dt.date
        date_info = "All Dates"

    # Attach first-seen caps and compute Δ% MCap
    first_caps = load_first_caps(get_historical_market_cap)
    df = df.drop(columns=["first_market_cap", "first_seen_date"], errors="ignore")
    df = df.merge(first_caps, on="name", how="left")
    for col in ["date", "first_seen_date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col]).dt.date

    df = compute_mcap_change(df)
    df["market_cap_cr"] = pd.to_numeric(df.get("market_cap"), errors="coerce")

    return df, date_info


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    st.title("Price Position")

    bucket_name = st.segmented_control(
        "Bucket",
        list(BUCKETS.keys()),
        default="Near High (0–5%)",
        key="pp_bucket",
    )
    cfg = BUCKETS[bucket_name]
    st.caption(cfg["caption"])

    result = _load_data(cfg)
    if isinstance(result, pd.DataFrame):
        return  # empty / error already shown
    daily_df, date_info = result

    if daily_df.empty:
        st.warning("No data available after processing.")
        return

    # ── filters ───────────────────────────────────────────────────────────────
    industries = ["All"] + sorted(daily_df["industry"].dropna().unique().tolist())
    fc1, fc2, fc3, fc4 = st.columns([1.2, 1.3, 1.2, 1.3])
    with fc1:
        sel_industry = st.selectbox("Industry", industries, key="pp_industry")
    with fc2:
        search_text = st.text_input("Company search", placeholder="Type part of a name", key="pp_search")
    with fc3:
        view_scope = st.selectbox("Columns", ["Focused", "Detailed"], key="pp_scope")
    with fc4:
        sort_by = st.selectbox("Sort by", list(cfg["sort_options"].keys()), key="pp_sort")

    filtered = daily_df.copy()
    if sel_industry != "All":
        filtered = filtered[filtered["industry"] == sel_industry]
    if search_text:
        filtered = filtered[
            filtered["name"].astype("string").str.contains(search_text, case=False, na=False)
        ]

    valid_caps = filtered["market_cap_cr"].dropna()
    if not valid_caps.empty:
        min_cap, max_cap = int(valid_caps.min()), int(valid_caps.max())
        if min_cap == max_cap:
            max_cap += 1
        cap_range = st.slider("Market Cap Range (₹ Cr)", min_cap, max_cap, (min_cap, max_cap), key="pp_cap")
        filtered = filtered[filtered["market_cap_cr"].between(cap_range[0], cap_range[1])]

    label = f"Showing **{len(filtered)}** records for **{date_info}**"
    if sel_industry != "All":
        label += f" in **{sel_industry}**"
    st.markdown(label)

    if filtered.empty:
        st.info("No records match the filters.")
        return

    # ── summary metrics ───────────────────────────────────────────────────────
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Companies", len(filtered))
    mc2.metric("Industries", int(filtered["industry"].nunique()) if "industry" in filtered.columns else 0)
    avg_drop = pd.to_numeric(filtered.get("down_from_52w_high"), errors="coerce")
    avg_mcap = pd.to_numeric(filtered.get("Δ% MCap"), errors="coerce")
    mc3.metric("Avg Distance From High", f"{avg_drop.mean():.1f}%" if avg_drop.notna().any() else "-")
    mc4.metric("Avg Δ% MCap", f"{avg_mcap.mean():.1f}%" if avg_mcap.notna().any() else "-")

    selected_cols = FOCUSED_COLS if view_scope == "Focused" else DETAILED_COLS
    sort_options  = cfg["sort_options"]
    height_group  = 320 if view_scope == "Focused" else 420
    height_list   = 520 if view_scope == "Focused" else 620

    # ── grouped / list tabs ───────────────────────────────────────────────────
    grouped_tab, list_tab = st.tabs(["Grouped by Industry", "Company List"])

    with grouped_tab:
        grouped_source = filtered.assign(industry=filtered["industry"].fillna("Unknown"))
        group_industries = sorted(grouped_source["industry"].dropna().unique().tolist())
        sel_group = st.selectbox("Industry", group_industries, key="pp_group_industry")
        group_df  = grouped_source[grouped_source["industry"] == sel_group].copy()

        avg_group_drop = pd.to_numeric(group_df.get("down_from_52w_high"), errors="coerce").mean()
        avg_group_pe   = pd.to_numeric(group_df.get("pe"), errors="coerce").mean()
        header = f"{sel_group} ({len(group_df)} companies)"
        if pd.notna(avg_group_drop):
            header += f" | avg drop {avg_group_drop:.1f}%"
        if pd.notna(avg_group_pe):
            header += f" | avg P/E {avg_group_pe:.1f}"
        st.markdown(f"#### {header}")

        render_interactive_table(
            prepare_grid_df(group_df, selected_cols, sort_by, sort_options,
                            include_industry=True, rename_map=COMMON_RENAME_MAP),
            columns=selected_cols,
            key=f"pp_group_{sel_group}",
            rename_map=COMMON_RENAME_MAP,
            one_decimal_cols=BUCKET_ONE_DECIMAL_COLS,
            two_decimal_cols=BUCKET_TWO_DECIMAL_COLS,
            major_cols=BUCKET_MAJOR_COLS,
            link_col="name",
            height=height_group,
        )

    with list_tab:
        render_interactive_table(
            prepare_grid_df(filtered, selected_cols, sort_by, sort_options,
                            include_industry=True, rename_map=COMMON_RENAME_MAP),
            columns=selected_cols,
            key="pp_list",
            rename_map=COMMON_RENAME_MAP,
            one_decimal_cols=BUCKET_ONE_DECIMAL_COLS,
            two_decimal_cols=BUCKET_TWO_DECIMAL_COLS,
            major_cols=BUCKET_MAJOR_COLS,
            link_col="name",
            height=height_list,
        )

    st.caption("Tip: use column filters and multi-sort in the table headers for quick screening.")
    st.download_button(
        "Download CSV",
        data=filtered.to_csv(index=False),
        file_name=f"{cfg['filename']}_{date_info.replace(' ', '_').replace('to', '-')}.csv",
    )


if __name__ == "__main__":
    main()

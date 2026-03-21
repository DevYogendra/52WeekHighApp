import pandas as pd
import streamlit as st
from dateutil.relativedelta import relativedelta

from db_utils import get_fivetofiftyclub_data_for_date, get_fivetofiftyclub_dates, get_historical_market_cap
from views.bucket_view_utils import (
    COMMON_RENAME_MAP,
    DETAILED_COLS,
    FOCUSED_COLS,
    compute_mcap_change,
    highlight_valuation_gradient,
    load_first_caps,
    prepare_display_df,
)


SORT_OPTIONS = {
    "Closest Recovery Setup": ("↓52W High%", True),
    "Lowest P/E": ("P/E", True),
    "Lowest P/BV": ("P/BV", True),
    "Highest ROE": ("ROE", False),
    "Highest Δ% MCap": ("Δ% MCap", False),
    "Highest MCap": ("MCap", False),
    "Alphabetical": ("Name", True),
}

def main():
    st.title("📉 5–50% from 52W High")
    st.caption("Pullback watchlist. Use this page to find names correcting from highs but still worth evaluating for recovery or re-entry.")

    dates = get_fivetofiftyclub_dates()
    if not dates:
        st.warning("No data available.")
        return

    dates = sorted([pd.to_datetime(d).date() for d in dates])
    min_date_available = dates[0]
    max_date_available = dates[-1]

    date_mode = st.radio("Select Date Mode", ["Single Date", "Date Range", "All Dates"], index=1)
    daily_df = pd.DataFrame()

    if date_mode == "Single Date":
        selected_date = st.selectbox("Select a date", dates, index=len(dates) - 1)
        daily_df = get_fivetofiftyclub_data_for_date(str(selected_date))
    elif date_mode == "Date Range":
        end_date_default = max_date_available
        start_date_default = min_date_available

        col1, col2 = st.columns([1, 2])
        with col1:
            range_method = st.radio("Define range by", ("Presets", "Last 'y' days", "Last 'x' months"))
        with col2:
            if range_method == "Presets":
                preset = st.radio("Preset period", ("1 Day", "Last 7 Days", "Last 1 Month"))
                delta = {
                    "1 Day": relativedelta(days=0),
                    "Last 7 Days": relativedelta(days=6),
                    "Last 1 Month": relativedelta(months=1),
                }.get(preset, relativedelta(days=6))
                start_date_default = max_date_available - delta
            elif range_method == "Last 'y' days":
                days = st.number_input("Days", min_value=1, value=7)
                start_date_default = max_date_available - relativedelta(days=days - 1)
            else:
                months = st.number_input("Months", min_value=1, value=3)
                start_date_default = max_date_available - relativedelta(months=months)

        start_date = st.date_input("Start date", value=start_date_default, min_value=min_date_available, max_value=max_date_available)
        end_date = st.date_input("End date", value=end_date_default, min_value=min_date_available, max_value=max_date_available)

        if start_date > end_date:
            st.error("Start date must be before or equal to end date.")
            return

        selected_dates_str = [d.strftime("%Y-%m-%d") for d in dates if start_date <= d <= end_date]
        dfs = [get_fivetofiftyclub_data_for_date(d_str) for d_str in selected_dates_str]
        daily_df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
        if not daily_df.empty and "name" in daily_df.columns and "date" in daily_df.columns:
            daily_df = (
                daily_df.sort_values(["name", "date"])
                .drop_duplicates(subset=["name"], keep="last")
                .reset_index(drop=True)
            )
    else:
        all_dates_str = [d.strftime("%Y-%m-%d") for d in dates]
        dfs = [get_fivetofiftyclub_data_for_date(d_str) for d_str in all_dates_str]
        if dfs:
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
            daily_df = last_caps.merge(first_caps, on="name", how="left")
            for col in ["date", "first_seen_date"]:
                if col in daily_df.columns:
                    daily_df[col] = pd.to_datetime(daily_df[col]).dt.date
        else:
            st.warning("No data found for all dates.")
            return

    if daily_df.empty:
        st.warning("No data available after processing.")
        return

    first_caps = load_first_caps(get_historical_market_cap)
    daily_df = daily_df.drop(columns=["first_market_cap", "first_seen_date"], errors="ignore")
    daily_df = daily_df.merge(first_caps, on="name", how="left")

    for col in ["date", "first_seen_date"]:
        if col in daily_df.columns:
            daily_df[col] = pd.to_datetime(daily_df[col]).dt.date

    daily_df = compute_mcap_change(daily_df)
    daily_df["market_cap_cr"] = pd.to_numeric(daily_df.get("market_cap"), errors="coerce") / 1e7

    if date_mode == "Single Date":
        date_info = selected_date.strftime("%Y-%m-%d")
    elif date_mode == "Date Range":
        date_info = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
    else:
        date_info = "All Dates"

    industries = sorted(daily_df["industry"].dropna().unique().tolist())
    industries.insert(0, "All")

    st.markdown("### Filters")
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([1.2, 1.3, 1.2, 1.3])
    with filter_col1:
        selected_industry = st.selectbox("Industry", industries)
    with filter_col2:
        search_text = st.text_input("Company Search", placeholder="Type part of a company name")
    with filter_col3:
        view_scope = st.selectbox("Columns", ["Focused", "Detailed"], index=0)
    with filter_col4:
        sort_by = st.selectbox("Sort By", list(SORT_OPTIONS.keys()), index=0)

    filtered_df = daily_df.copy()
    if selected_industry != "All":
        filtered_df = filtered_df[filtered_df["industry"] == selected_industry]

    if search_text:
        filtered_df = filtered_df[
            filtered_df["name"].astype("string").str.contains(search_text, case=False, na=False)
        ]

    valid_caps = filtered_df["market_cap_cr"].dropna()
    if not valid_caps.empty:
        min_cap = int(valid_caps.min())
        max_cap = int(valid_caps.max())
        if min_cap == max_cap:
            max_cap += 1
        selected_cap_range = st.slider(
            "Market Cap Range (₹ Cr)",
            min_value=min_cap,
            max_value=max_cap,
            value=(min_cap, max_cap),
        )
        filtered_df = filtered_df[filtered_df["market_cap_cr"].between(selected_cap_range[0], selected_cap_range[1])]

    st.markdown(
        f"Showing **{len(filtered_df)}** records for **{date_info}**"
        + (f" in **{selected_industry}**" if selected_industry != "All" else "")
    )

    if filtered_df.empty:
        st.info("No records match the filters.")
        return

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("Companies", len(filtered_df))
    metric_col2.metric("Industries", int(filtered_df["industry"].nunique()) if "industry" in filtered_df.columns else 0)
    avg_drop = pd.to_numeric(filtered_df.get("down_from_52w_high"), errors="coerce")
    avg_mcap = pd.to_numeric(filtered_df.get("Δ% MCap"), errors="coerce")
    metric_col3.metric("Avg Distance From High", f"{avg_drop.mean():.1f}%" if avg_drop.notna().any() else "-")
    metric_col4.metric("Avg Δ% MCap", f"{avg_mcap.mean():.1f}%" if avg_mcap.notna().any() else "-")

    selected_cols = FOCUSED_COLS if view_scope == "Focused" else DETAILED_COLS

    grouped_tab, list_tab = st.tabs(["Grouped by Industry", "Company List"])

    with grouped_tab:
        grouped = (
            filtered_df.assign(industry=filtered_df["industry"].fillna("Unknown"))
            .sort_values(["industry", "market_cap"], ascending=[True, False])
            .groupby("industry")
        )

        for industry, group_df in grouped:
            avg_group_drop = pd.to_numeric(group_df.get("down_from_52w_high"), errors="coerce").mean()
            avg_group_pe = pd.to_numeric(group_df.get("pe"), errors="coerce").mean()
            header = f"{industry} ({len(group_df)} companies)"
            if pd.notna(avg_group_drop):
                header += f" | avg drop {avg_group_drop:.1f}%"
            if pd.notna(avg_group_pe):
                header += f" | avg P/E {avg_group_pe:.1f}"
            st.markdown(f"#### {header}")

            display_df = prepare_display_df(group_df, selected_cols, sort_by, SORT_OPTIONS, include_industry=True, rename_map=COMMON_RENAME_MAP)
            styled_df = display_df.style.apply(highlight_valuation_gradient, axis=1)
            st.markdown(styled_df.to_html(index=False, escape=False), unsafe_allow_html=True)

    with list_tab:
        use_styled = st.toggle("Use styled table", value=True)
        display_df = prepare_display_df(filtered_df, selected_cols, sort_by, SORT_OPTIONS, include_industry=True, rename_map=COMMON_RENAME_MAP)

        if use_styled:
            styled_df = display_df.style.apply(highlight_valuation_gradient, axis=1)
            st.markdown(styled_df.to_html(index=False, escape=False), unsafe_allow_html=True)
        else:
            st.dataframe(display_df, use_container_width=True)

    st.markdown("Green = lower valuation | Red = higher valuation")
    st.markdown("---")
    st.download_button(
        "Download CSV",
        data=filtered_df.to_csv(index=False),
        file_name=f"fivetofifty_{date_info.replace(' ', '_').replace('to', '-')}.csv",
    )


if __name__ == "__main__":
    main()

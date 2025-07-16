import streamlit as st
import pandas as pd
import datetime
from dateutil.relativedelta import relativedelta
from db_utils import (
    get_all_dates,
    get_data_for_date,
    add_screener_links,
    get_historical_market_cap,   # 👈 NEW
)

def main():
    st.title("📅 Daily 52-Week Highs Viewer")

    dates = get_all_dates()
    if not dates:
        st.warning("No data available.")
        return

    dates = sorted([pd.to_datetime(d).date() for d in dates])
    min_date_available = dates[0]
    max_date_available = dates[-1]

    date_mode = st.radio("Select Date Mode", ["Single Date", "Date Range", "All Dates"], index=1)

    daily_df = pd.DataFrame()

    if date_mode == "Single Date":
        selected_date = st.selectbox(
            "Select a date", 
            dates, 
            index=len(dates) - 1,
            format_func=lambda date: date.strftime("%Y-%m-%d")
        )
        daily_df = get_data_for_date(selected_date.strftime("%Y-%m-%d"))
        
    elif date_mode == "Date Range":
        st.subheader("Date Range Selection")

        end_date_default = max_date_available
        start_date_default = min_date_available
        
        col1, col2 = st.columns([1, 2])
        with col1:
            range_method = st.radio("Define range by:", ("Presets", "Last 'y' days", "Last 'x' months"))

        with col2:
            if range_method == "Presets":
                preset = st.radio(
                    "Select preset period:",
                    ("1 Day", "Last 7 Days", "Last 14 Days", "Last 1 Month", "Last 3 Months", "Last 6 Months")
                )
                if preset == "1 Day":
                    start_date_default = max_date_available
                elif preset == "Last 7 Days":
                    start_date_default = max_date_available - relativedelta(days=6)
                elif preset == "Last 14 Days":
                    start_date_default = max_date_available - relativedelta(days=13)
                elif preset == "Last 1 Month":
                    start_date_default = max_date_available - relativedelta(months=1)
                elif preset == "Last 3 Months":
                    start_date_default = max_date_available - relativedelta(months=3)
                elif preset == "Last 6 Months":
                    start_date_default = max_date_available - relativedelta(months=6)

            elif range_method == "Last 'y' days":
                num_days = st.number_input("Enter days (y):", min_value=1, value=7)
                start_date_default = max_date_available - relativedelta(days=num_days - 1)
            
            elif range_method == "Last 'x' months":
                num_months = st.number_input("Enter months (x):", min_value=1, value=3)
                start_date_default = max_date_available - relativedelta(months=num_months)

        if start_date_default < min_date_available:
            start_date_default = min_date_available
            st.caption(f"Note: Range start adjusted to earliest available date: {min_date_available.strftime('%Y-%m-%d')}")

        st.markdown("---")
        st.write("You can adjust the final dates below:")

        start_date = st.date_input("Start date", value=start_date_default, min_value=min_date_available, max_value=max_date_available)
        end_date = st.date_input("End date", value=end_date_default, min_value=min_date_available, max_value=max_date_available)

        if start_date > end_date:
            st.error("Start date must be before or equal to end date.")
            return

        selected_dates_str = [d.strftime("%Y-%m-%d") for d in dates if start_date <= d <= end_date]
        if not selected_dates_str:
            st.warning("No data available in the selected date range.")
            return

        dfs = [get_data_for_date(d_str) for d_str in selected_dates_str]
        if dfs:
            daily_df = pd.concat(dfs, ignore_index=True)
            if 'name' in daily_df.columns:
                daily_df.drop_duplicates(subset=['name'], inplace=True)
            else:
                st.error("Error: 'name' column not found.")
                return 
        else:
            st.warning("No data found for the selected date range.")
            return
            
else:  # All Dates
    all_dates_str = [d.strftime("%Y-%m-%d") for d in dates]
    dfs = [get_data_for_date(d_str) for d_str in all_dates_str]
    if dfs:
        all_df = pd.concat(dfs, ignore_index=True)

        if "name" not in all_df.columns or "market_cap" not in all_df.columns:
            st.error("Required columns missing in data.")
            return

        if not pd.api.types.is_datetime64_any_dtype(all_df["date"]):
            all_df["date"] = pd.to_datetime(all_df["date"])

        # Capture first market cap and date seen
        first_caps = (
            all_df.sort_values(["name", "date"])
            .groupby("name", as_index=False)
            .first()[["name", "market_cap", "date"]]
            .rename(columns={"market_cap": "first_market_cap", "date": "first_seen_date"})
        )

        # Capture latest data with all needed columns
        latest_cols = [
            "name", "date", "market_cap", "industry", "current_price", "sales",
            "operating_profit", "opm", "opm_last_year", "pe", "pbv", "peg",
            "roa", "debt_to_equity", "roe", "working_capital", "other_income",
            "down_from_52w_high", "nse_code", "bse_code"
        ]

        available_cols = [col for col in latest_cols if col in all_df.columns]

        last_caps = (
            all_df.sort_values(["name", "date"])
            .groupby("name", as_index=False)
            .last()[available_cols]
        )

        # Merge
        daily_df = last_caps.merge(first_caps, on="name", how="left")

    else:
        st.warning("No data found for all dates.")
        return

    if daily_df.empty:
        st.warning("No data available after processing.")
        return

    if "first_market_cap" not in daily_df.columns or daily_df["first_market_cap"].isna().all():
        hist_df = get_historical_market_cap()
        first_caps = (
            hist_df.sort_values("date")
            .groupby("name", as_index=False)
            .first()[["name", "market_cap"]]
            .rename(columns={"market_cap": "first_market_cap"})
        )
        daily_df = daily_df.merge(first_caps, on="name", how="left")

    daily_df["Δ% MCap"] = (
        100
        * (daily_df["market_cap"] - daily_df["first_market_cap"])
        / daily_df["first_market_cap"]
    )

    industries = sorted(daily_df["industry"].dropna().unique().tolist())
    industries.insert(0, "All")
    selected_industry = st.selectbox("Filter by Industry", industries)

    filtered_df = daily_df.copy()
    if selected_industry != "All":
        filtered_df = filtered_df[filtered_df["industry"] == selected_industry]

    if date_mode == "Single Date":
        date_info = selected_date.strftime("%Y-%m-%d")
    elif date_mode == "Date Range":
        date_info = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
    else:
        date_info = "All Dates"

    st.markdown(
        f"Showing **{len(filtered_df)}** records for **{date_info}**"
        + (f" in **{selected_industry}**" if selected_industry != "All" else "")
    )

    if filtered_df.empty:
        st.info("No records match the filters.")
        return

    st.markdown("---")
    st.markdown("### 🏭 Grouped View by Industry")

    if "industry" not in filtered_df.columns:
        st.error("Error: 'industry' column not found.")
        return

    filtered_df["industry"] = filtered_df["industry"].fillna("None")

    grouped = (
        filtered_df
        .sort_values(["industry", "market_cap"], ascending=[True, False])
        .groupby("industry")
    )

    standard_cols = [
        'date', 'first_seen_date', 'name',
        'current_price', 'market_cap', 'first_market_cap', 'Δ% MCap',
        'sales', 'operating_profit', 'opm', 'opm_last_year', 'pe',
        'pbv', 'peg', 'roa', 'debt_to_equity', 'roe', 'working_capital',
        'other_income', 'down_from_52w_high','nse_code', 'bse_code'
    ]

    rename_map = {
        'date': 'Date', 'first_seen_date': 'First Seen', 'name': 'Name',
        'current_price': 'Price',
        'market_cap': 'MCap', 'first_market_cap': 'First MCap', 'Δ% MCap': 'Δ% MCap',
        'sales': 'Sales', 'operating_profit': 'Op Profit', 'opm': 'OPM%',
        'opm_last_year': 'OPM LY%', 'pe': 'P/E', 'pbv': 'P/BV', 'peg': 'PEG',
        'roa': 'ROA', 'debt_to_equity': 'D/E', 'roe': 'ROE', 'working_capital': 'WC',
        'other_income': 'Oth Income', 'down_from_52w_high': '↓52W High%',
        'nse_code': 'NSE', 'bse_code': 'BSE'
    }

    for industry, group_df in grouped:
        st.markdown(f"#### 🏷️ {industry} ({len(group_df)} companies)")

        for col in standard_cols:
            if col not in group_df.columns:
                group_df[col] = None

        display_df = group_df[standard_cols + ['industry']].copy()
        display_df = add_screener_links(display_df)

        numeric_cols = display_df.select_dtypes(include='number').columns
        display_df[numeric_cols] = display_df[numeric_cols].round(2)

        display_df = display_df.drop(columns=["industry"])
        display_df = display_df.rename(columns=rename_map)

        st.markdown(display_df.to_html(index=False, escape=False), unsafe_allow_html=True)

    filename_date_part = date_info.replace(" ", "_").replace("to", "-").lower()
    st.download_button(
        "📥 Download CSV",
        data=filtered_df.to_csv(index=False),
        file_name=f"highs_{filename_date_part}_{selected_industry if selected_industry != 'All' else 'all'}.csv"
    )

if __name__ == "__main__":
    main()

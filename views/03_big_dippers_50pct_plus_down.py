import streamlit as st
import pandas as pd
import datetime
from dateutil.relativedelta import relativedelta
from db_utils import (
    get_downfromhigh_dates,
    get_downfromhigh_data_for_date,
    get_historical_market_cap,
    add_screener_links,
)
from matplotlib import cm
from matplotlib.colors import Normalize, to_hex


def highlight_valuation_gradient(row):
    def get_style(val, vmin, vmax):
        if pd.isna(val):
            return None
        norm = Normalize(vmin=vmin, vmax=vmax)
        cmap = cm.get_cmap('RdYlGn_r')
        rgba = cmap(norm(min(val, vmax)))  # cap at vmax
        bg_color = to_hex(rgba)

        # Compute luminance for contrasting text color
        r, g, b = rgba[:3]
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        text_color = "#000000" if luminance > 0.6 else "#FFFFFF"

        return f"background-color: {bg_color}; color: {text_color}; font-weight: bold;"

    styles = []
    for col in row.index:
        if col == "P/E":
            styles.append(get_style(row[col], vmin=0, vmax=60) or "")
        elif col == "P/BV":
            styles.append(get_style(row[col], vmin=0, vmax=12) or "")
        else:
            styles.append("")
    return styles


def compute_mcap_change(df):
    df = df.copy()
    for col in ["market_cap", "first_market_cap"]:
        if col not in df.columns:
            df[col] = pd.NA
    df["Δ% MCap"] = (
        100 * (df["market_cap"] - df["first_market_cap"])
        / df["first_market_cap"].replace(0, pd.NA)
    )
    return df


def main():
    st.title("📉 Big Dippers (50%+ Down)")

    dates = get_downfromhigh_dates()
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
        daily_df = get_downfromhigh_data_for_date(str(selected_date))

    elif date_mode == "Date Range":
        end_date_default = max_date_available
        start_date_default = min_date_available

        col1, col2 = st.columns([1, 2])
        with col1:
            range_method = st.radio("Define range by:", ("Presets", "Last 'y' days", "Last 'x' months"))
        with col2:
            if range_method == "Presets":
                preset = st.radio("Select preset period:", ("1 Day", "Last 7 Days", "Last 1 Month"))
                delta = {
                    "1 Day": relativedelta(days=0),
                    "Last 7 Days": relativedelta(days=6),
                    "Last 1 Month": relativedelta(months=1),
                }.get(preset, relativedelta(days=6))
                start_date_default = max_date_available - delta
            elif range_method == "Last 'y' days":
                days = st.number_input("Enter days:", min_value=1, value=7)
                start_date_default = max_date_available - relativedelta(days=days - 1)
            elif range_method == "Last 'x' months":
                months = st.number_input("Enter months:", min_value=1, value=3)
                start_date_default = max_date_available - relativedelta(months=months)

        start_date = st.date_input("Start date", value=start_date_default, min_value=min_date_available, max_value=max_date_available)
        end_date = st.date_input("End date", value=end_date_default, min_value=min_date_available, max_value=max_date_available)

        if start_date > end_date:
            st.error("Start date must be before or equal to end date.")
            return

        selected_dates_str = [d.strftime("%Y-%m-%d") for d in dates if start_date <= d <= end_date]
        dfs = [get_downfromhigh_data_for_date(d_str) for d_str in selected_dates_str]
        daily_df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    else:  # All Dates
        all_dates_str = [d.strftime("%Y-%m-%d") for d in dates]
        dfs = [get_downfromhigh_data_for_date(d_str) for d_str in all_dates_str]
        #daily_df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
        if dfs:
            all_df = pd.concat(dfs, ignore_index=True)

            if "name" not in all_df.columns or "market_cap" not in all_df.columns:
                st.error("Required columns missing in data.")
                return

            # Ensure 'date' is clean and consistent (no time component)
            if not pd.api.types.is_datetime64_any_dtype(all_df["date"]):
                all_df["date"] = pd.to_datetime(all_df["date"])

            all_df["date"] = all_df["date"].dt.date  # Remove time part

            # Capture first market cap and date seen
            first_caps = (
                all_df.sort_values(["name", "date"])
                .groupby("name", as_index=False)
                .first()[["name", "market_cap", "date"]]
                .rename(columns={"market_cap": "first_market_cap", "date": "first_seen_date"})
            )

            # Define standard columns
            standard_cols = [
                'date', 'first_seen_date', 'name',
                'current_price', 'market_cap', 'first_market_cap', 'Δ% MCap',
                'sales', 'opm', 'opm_last_year', 'operating_profit', 'trade_receivables', 'trade_payables', 'inventory',
                'pe', 'pbv', 'peg', 'earnings_yield',
                'roa', 'roe',
                'other_income',
                'debt_to_equity',
                'down_from_52w_high',
                'change_in_dii_holding', 'change_in_fii_holding',
                'nse_code', 'bse_code',
                'industry'
            ]
            
            
            # Step 1: Get earliest market cap per company
            first_caps = (
                all_df.sort_values(["name", "date"])
                .groupby("name", as_index=False)
                .first()[["name", "market_cap", "date"]]
                .rename(columns={"market_cap": "first_market_cap", "date": "first_seen_date"})
            )

            # Step 2: Get latest data per company
            last_caps = (
                all_df.sort_values(["name", "date"])
                .groupby("name", as_index=False)
                .last()
            )

            # 🔁 Drop any existing first_seen_date or first_market_cap to avoid _x/_y mess
            last_caps = last_caps.drop(columns=["first_seen_date", "first_market_cap"], errors="ignore")

            # Step 3: Merge
            daily_df = last_caps.merge(first_caps, on="name", how="left")

            # st.write("Available columns:", daily_df.columns.tolist())


            # Step 4: Clean date columns
            for col in ["date", "first_seen_date"]:
                if col in daily_df.columns:
                    daily_df[col] = pd.to_datetime(daily_df[col]).dt.date

            # Convert dates
            for col in ["date", "first_seen_date"]:
                if col in daily_df.columns:
                    daily_df[col] = pd.to_datetime(daily_df[col]).dt.date
        
        else:
            st.warning("No data found for all dates.")
            return

    if daily_df.empty:
        st.warning("No data available after processing.")
        return

    hist_df = get_historical_market_cap()
    first_caps = (
        hist_df.sort_values(["name", "date"])
        .groupby("name", as_index=False)
        .first()[["name", "market_cap", "date"]]
        .rename(columns={"market_cap": "first_market_cap", "date": "first_seen_date"})
    )
    daily_df = daily_df.drop(columns=["first_market_cap", "first_seen_date"], errors="ignore")
    daily_df = daily_df.merge(first_caps, on="name", how="left")

    for col in ["date", "first_seen_date"]:
        if col in daily_df.columns:
            daily_df[col] = pd.to_datetime(daily_df[col]).dt.date

    daily_df = compute_mcap_change(daily_df)

    date_info = (
        selected_date.strftime("%Y-%m-%d") if date_mode == "Single Date"
        else f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        if date_mode == "Date Range"
        else "All Dates"
    )

    st.markdown(f"Showing data for **{date_info}**")

    if "industry" not in daily_df.columns:
        st.warning("Missing 'industry' column.")
        return

    grouped = (
        daily_df.fillna("").sort_values(["industry", "market_cap"], ascending=[True, False])
        .groupby("industry")
    )

    standard_cols = [
        "date", "first_seen_date", "name",
        "current_price", "market_cap", "first_market_cap", "Δ% MCap",
        "down_from_52w_high", "sales", "opm", "opm_last_year", "operating_profit",
        "trade_receivables", "trade_payables", "inventory",
        "pe", "pbv", "peg", "earnings_yield",
        "roa", "roe", "other_income", "debt_to_equity",
        "change_in_dii_holding", "change_in_fii_holding",
        "nse_code", "bse_code"
    ]

    rename_map = {
        "date": "Date", "first_seen_date": "First Seen", "name": "Name",
        "current_price": "Price", "market_cap": "MCap", "first_market_cap": "First MCap", "Δ% MCap": "Δ% MCap",
        "down_from_52w_high": "↓ 52W High%", "sales": "Sales", "opm": "OPM%", "opm_last_year": "OPM LY%",
        "operating_profit": "Op Profit", "trade_receivables": "Receivables", "trade_payables": "Payables",
        "inventory": "Inventory", "pe": "P/E", "pbv": "P/BV", "peg": "PEG", "earnings_yield": "Earnings Yield",
        "roa": "ROA", "roe": "ROE", "other_income": "Oth Income", "debt_to_equity": "D/E",
        "change_in_dii_holding": "Δ DII", "change_in_fii_holding": "Δ FII",
        "nse_code": "NSE", "bse_code": "BSE"
    }

    group_by_industry = st.checkbox("Group by Industry", value=True)

    st.markdown("---")

    if group_by_industry:
        for industry, group_df in grouped:
            st.markdown(f"#### 🏣 {industry} ({len(group_df)} companies)")

            # Fill missing columns
            for col in standard_cols:
                if col not in group_df.columns:
                    group_df[col] = None

            # Always include 'industry' for merging/grouped view
            full_cols = standard_cols + (['industry'] if 'industry' not in standard_cols else [])
            display_df = group_df[full_cols].copy()

            # Add Screener links
            display_df = add_screener_links(display_df)

            # Convert relevant columns to numeric safely
            for col in ["P/E", "P/BV"]:
                if col in display_df.columns:
                    display_df[col] = pd.to_numeric(display_df[col], errors="coerce")

            # Round numeric columns
            numeric_cols = display_df.select_dtypes(include='number').columns
            display_df[numeric_cols] = display_df[numeric_cols].round(2)

            # Rename columns
            display_df = display_df.rename(columns=rename_map)

            # Sort by P/E if available
            if "P/E" in display_df.columns:
                display_df = display_df.sort_values(by="P/E", ascending=True, na_position='last')

            # Apply styling
            styled_df = (
                display_df.style
                .apply(highlight_valuation_gradient, axis=1)
                .format(precision=2)
            )

            st.markdown(styled_df.to_html(index=False, escape=False), unsafe_allow_html=True)

    else:
        st.markdown("### 📃 Flat Company List")

        view_mode = st.checkbox("Use Styled View (color gradients)", value=False)

        # Fill missing columns
        # Fill missing columns
        for col in standard_cols:
            if col not in daily_df.columns:
                daily_df[col] = None

        full_cols = standard_cols + (['industry'] if 'industry' not in standard_cols else [])
        display_df = daily_df[full_cols].copy()

        if view_mode:
            # Add Screener links — non-intrusive
            display_df = add_screener_links(display_df)

            # st.write("Available columns:", daily_df.columns.tolist())
            for col in ["pe", "pbv"]:
                if col in display_df.columns:
                    display_df[col] = pd.to_numeric(display_df[col], errors="coerce")

            if "pe" in display_df.columns:
                display_df = display_df.sort_values(by="pe", ascending=True, na_position='last')

            # 🧽 Drop screener link in plain view to avoid clutter
            if not view_mode and "Screener" in display_df.columns:
                display_df = display_df.drop(columns=["Screener"])

            
            numeric_cols = display_df.select_dtypes(include='number').columns
            display_df[numeric_cols] = display_df[numeric_cols].round(2)

            display_df = display_df.rename(columns=rename_map)
            
            styled_df = (
                display_df.style
                .apply(highlight_valuation_gradient, axis=1)
                .format(precision=2)
            )
            st.markdown(styled_df.to_html(index=False, escape=False), unsafe_allow_html=True)
        else:
            
            for col in ["pe", "pbv"]:
                if col in display_df.columns:
                    display_df[col] = pd.to_numeric(display_df[col], errors="coerce")

            if "pe" in display_df.columns:
                display_df = display_df.sort_values(by="pe", ascending=True, na_position='last')

            # 🧽 Drop screener link in plain view to avoid clutter
            if not view_mode and "Screener" in display_df.columns:
                display_df = display_df.drop(columns=["Screener"])
            
            numeric_cols = display_df.select_dtypes(include='number').columns
            display_df[numeric_cols] = display_df[numeric_cols].round(2)

            display_df = display_df.rename(columns=rename_map)
            
            st.dataframe(display_df, use_container_width=True)

    st.markdown("🟩 Green = low valuation | 🟥 Red = high valuation")

    st.markdown("---")
    st.download_button(
        "📅 Download All Data as CSV",
        data=daily_df.to_csv(index=False),
        file_name=f"downfromhigh_{date_info.replace(' ', '_').replace('to', '-')}.csv"
    )


if __name__ == "__main__":
    main()

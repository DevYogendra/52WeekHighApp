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


# from .exclusion_filter import render_exclusion_ui

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
            if 'name' not in daily_df.columns:
                st.error("Missing 'name' column in daily data.")
                return

            daily_df.drop_duplicates(subset=['name'], inplace=True)

            # STEP 1: Load historical data
            hist_df = get_historical_market_cap()
            hist_df["date"] = pd.to_datetime(hist_df["date"])

            # STEP 2: Get earliest market cap per company
            first_caps = (
                hist_df.sort_values(["name", "date"])
                .groupby("name", as_index=False)
                .first()[["name", "market_cap", "date"]]
                .rename(columns={"market_cap": "first_market_cap", "date": "first_seen_date"})
            )
            
            # Clean up existing columns before merge to avoid _x, _y confusion
            daily_df = daily_df.drop(columns=[col for col in daily_df.columns if col in ["first_market_cap", "first_seen_date"]], errors="ignore")

            # STEP 3: Merge into working data
            daily_df = daily_df.merge(first_caps, on="name", how="left")

            # Now these columns will be available without _x/_y

            # 🔍 DEBUGGING aid (can remove later)
            if "first_market_cap" not in daily_df.columns:
                st.error("Column 'first_market_cap' missing after merge.")
                st.write("Merged columns:", daily_df.columns.tolist())
                st.write("Sample merged DataFrame:")
                st.dataframe(daily_df.head())
                st.stop()

            for col in ["date", "first_seen_date"]:
                if col in daily_df.columns:
                    daily_df[col] = pd.to_datetime(daily_df[col]).dt.date

            # STEP 4: Compute % change
            daily_df = compute_mcap_change(daily_df)

        else:
            st.warning("No data found for the selected date range.")
            return


        # Optional enhancement: fetch first_seen_date and first_market_cap from history
        if "first_market_cap" not in daily_df.columns or daily_df["first_market_cap"].isna().all():
            hist_df = get_historical_market_cap()
            hist_df["date"] = pd.to_datetime(hist_df["date"])

            first_caps = (
                hist_df.sort_values(["name", "date"])
                .groupby("name", as_index=False)
                .first()[["name", "market_cap", "date"]]
                .rename(columns={"market_cap": "first_market_cap", "date": "first_seen_date"})
            )

            daily_df = daily_df.merge(first_caps, on="name", how="left")

            
    else:  # All Dates
        all_dates_str = [d.strftime("%Y-%m-%d") for d in dates]
        dfs = [get_data_for_date(d_str) for d_str in all_dates_str]
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
            available_cols = [col for col in standard_cols if col in all_df.columns]

            # Fix: ensure 'first_seen_date' has no time
            all_df["first_seen_date"] = pd.to_datetime(all_df["first_seen_date"]).dt.date

            #st.write("Columns in display_df:", all_df.columns.tolist())
            #st.write("Sample data:", all_df.head()) 

            # Get latest record for each name
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

    daily_df = compute_mcap_change(daily_df)

    # 🔁 Apply persistent exclusion filter
    # daily_df = render_exclusion_ui(daily_df)

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

    standard_cols = [
        # ⏱️ Temporal & Identity
        'date', 'first_seen_date', 'name',

        # 💰 Price & Market Cap
        'current_price', 'market_cap', 'first_market_cap', 'Δ% MCap',

        # 📊 Business Performance
        'sales', 'opm', 'opm_last_year', 'operating_profit', 'trade_receivables', 'trade_payables', 'inventory', 

        # 💹 Valuation
        'pe', 'pbv', 'peg', 'earnings_yield',

        # 📈 Profitability & Returns
        'roa', 'roe', 
        # 'working_capital', 
        'other_income',

        # 🧾 Balance Sheet & Solvency
        'debt_to_equity', 
        # 'debt_to_ebit',

        # 📉 Price Signal
        'down_from_52w_high',

        # 🧳 Ownership Trends
        'change_in_dii_holding', 'change_in_fii_holding',

        # 🏷️ Identifiers
        'nse_code', 'bse_code'
    ]

    rename_map = {
        # ⏱️ Time & Identity
        'date': 'Date',
        'first_seen_date': 'First Seen',
        'name': 'Name',

        # 💰 Price & Market Cap
        'current_price': 'Price',
        'market_cap': 'MCap',
        'first_market_cap': 'First MCap',
        'Δ% MCap': 'Δ% MCap',

        # 📊 Business Performance
        'sales': 'Sales',
        'opm': 'OPM%',
        'opm_last_year': 'OPM LY%',        
        'operating_profit': 'Op Profit',
        'trade_receivables': 'Receivables',
        'trade_payables': 'Payables',
        'inventory': 'Inventory',
        

        # 💹 Valuation
        'pe': 'P/E',
        'pbv': 'P/BV',
        'peg': 'PEG',
        'earnings_yield': 'Earnings Yield',

        # 📈 Returns & Profitability
        'roa': 'ROA',
        'roe': 'ROE',
#        'working_capital': 'WC',
        'other_income': 'Oth Income',

        # 🧾 Balance Sheet
        'debt_to_equity': 'D/E',
#        'debt_to_ebit': 'Debt/EBIT',

        # 📉 Price Signal
        'down_from_52w_high': '↓52W High%',

        # 🧳 Institutional Holdings
        'change_in_dii_holding': 'Δ DII',
        'change_in_fii_holding': 'Δ FII',

        # 🏷️ Codes
        'nse_code': 'NSE',
        'bse_code': 'BSE'
    }

    group_by_industry = st.checkbox("Group by Industry", value=True)
   
    if group_by_industry:
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
            display_df = display_df.sort_values(by="P/E", ascending=True, na_position='last')

            styled_df = (
                display_df.style
                .apply(highlight_valuation_gradient, axis=1)
                .format(precision=2)
            )
            st.markdown(styled_df.to_html(index=False, escape=False), unsafe_allow_html=True)

    else:
        st.markdown("---")
        st.markdown("### 📃 Flat Company List")

        for col in standard_cols:
            if col not in filtered_df.columns:
                filtered_df[col] = None

        display_df = filtered_df[standard_cols + ['industry']].copy()
        display_df = add_screener_links(display_df)

        numeric_cols = display_df.select_dtypes(include='number').columns
        display_df[numeric_cols] = display_df[numeric_cols].round(2)

        display_df = display_df.rename(columns=rename_map)
        display_df = display_df.sort_values(by="P/E", ascending=True, na_position='last')

        styled_df = (
            display_df.style
            .apply(highlight_valuation_gradient, axis=1)
            .format(precision=2)
        )
        st.markdown(styled_df.to_html(index=False, escape=False), unsafe_allow_html=True)

    st.markdown("""
    <div style="margin: 1em 0;">
        <strong>Valuation Color Legend</strong><br>
        Applies to: <code>P/E (0–60)</code> and <code>P/BV (0–12)</code>
        <div style="display: flex; align-items: center; gap: 10px; font-size: 0.85em; margin-top: 0.5em;">
            <div style="width: 120px;">Low (Undervalued)</div>
            <div style="height: 15px; width: 150px; background: linear-gradient(to right, #1a9850, #fee08b, #d73027); border: 1px solid #ccc;"></div>
            <div style="width: 120px;">High (Overvalued)</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


    filename_date_part = date_info.replace(" ", "_").replace("to", "-").lower()
    st.download_button(
        "📥 Download CSV",
        data=filtered_df.to_csv(index=False),
        file_name=f"highs_{filename_date_part}_{selected_industry if selected_industry != 'All' else 'all'}.csv"
    )

if __name__ == "__main__":
    main()

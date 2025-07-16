import streamlit as st
import pandas as pd
from db_utils import get_momentum_summary, get_historical_market_cap, add_screener_links
from plot_utils import market_cap_line_chart

def main():
    st.title("📈 Momentum Summary")

    df = get_momentum_summary()
    if df.empty:
        st.warning("No momentum data available.")
        return

    # --- Sidebar Filters ------------------------------------------------
    st.sidebar.header("Filters")
    industries = ["All"] + sorted(df["industry"].dropna().unique().tolist())
    selected_industry = st.sidebar.selectbox("Filter by Industry", industries)
    min_hits = st.sidebar.slider("Minimum hits in last 30 days", 0, 30, 1)
    min_gain = st.sidebar.slider("Min % Market‑Cap Gain Since First Seen", 0, 500, 0)

    # --- Filtering ------------------------------------------------------
    filtered_df = df.copy()
    if selected_industry != "All":
        filtered_df = filtered_df[filtered_df["industry"] == selected_industry]
    filtered_df = filtered_df[
        (filtered_df["hits_30"] >= min_hits) & (filtered_df["%_gain_mc"] >= min_gain)
    ]

    st.markdown(f"Showing **{len(filtered_df)}** companies meeting criteria.")

    # --- Column rename map ---------------------------------------------
    rename_map = {
        "name": "Name",
        "bse_code": "BSE",
        "nse_code": "NSE",
        "market_cap": "MCap",
        "first_market_cap": "First MCap",
        "%_gain_mc": "Δ% MCap",
        "hits_7": "Hits 7D",
        "hits_30": "Hits 30D",
        "hits_60": "Hits 60D",
        "first_seen_date": "First Seen",
        "industry": "Industry"
    }

    # --- Display --------------------------------------------------------
    grouping_options = ["None", "industry", "sector"]
    valid_grouping_options = [opt for opt in grouping_options if opt == "None" or opt in filtered_df.columns]
    group_by_col = st.selectbox(
        "Group by",
        valid_grouping_options,
        index=valid_grouping_options.index("industry") if "industry" in valid_grouping_options else 0,
    )

    st.markdown("---")

    display_cols = [
        "name", "bse_code", "nse_code",
        "market_cap", "first_market_cap", "%_gain_mc",
        "hits_7", "hits_30", "hits_60", "first_seen_date"
    ]

    if group_by_col != "None":
        st.markdown(f"### 🏭 Grouped View by {group_by_col.capitalize()}")
        filtered_df[group_by_col] = filtered_df[group_by_col].fillna("None")

        grouped = (
            filtered_df
            .sort_values([group_by_col, "%_gain_mc"], ascending=[True, False])
            .groupby(group_by_col)
        )

        for group_name, group_df in grouped:
            st.markdown(f"#### 🏷️ {group_name} ({len(group_df)} companies)")
            display_df = group_df[display_cols].copy()
            display_df = add_screener_links(display_df)
            numeric_cols = display_df.select_dtypes(include="number").columns
            display_df[numeric_cols] = display_df[numeric_cols].round(2)
            display_df = display_df.rename(columns=rename_map)
            st.markdown(display_df.to_html(escape=False, index=False), unsafe_allow_html=True)
    else:
        display_df = filtered_df[["industry"] + display_cols].copy()
        display_df = add_screener_links(display_df)
        numeric_cols = display_df.select_dtypes(include="number").columns
        display_df[numeric_cols] = display_df[numeric_cols].round(2)
        display_df = display_df.rename(columns=rename_map)
        st.markdown(display_df.to_html(escape=False, index=False), unsafe_allow_html=True)

    # --- Download -------------------------------------------------------
    st.download_button(
        "📥 Download CSV", filtered_df.to_csv(index=False), "momentum_summary.csv"
    )

    st.markdown("---")

    # --- Market‑Cap Trend (All sorted by % gain) -------------------------
    st.header("📊 Market‑Cap Trend")

    if not filtered_df.empty:
        sorted_by_gain = (
            filtered_df.sort_values(by="%_gain_mc", ascending=False)
            .drop_duplicates(subset=["name"])
        )

        # Select by raw name
        selected_stock = st.selectbox(
            "Select company to view Market‑Cap trend",
            options=sorted_by_gain["name"].tolist(),
            key="market_cap_stock_selector"
        )

        if selected_stock:
            # Show link separately, rendered via markdown
            row = sorted_by_gain[sorted_by_gain["name"] == selected_stock].iloc[0]
            nse = str(row.get("nse_code", "")).strip()
            bse = str(row.get("bse_code", "")).strip()

            if nse:
                link = f"https://www.screener.in/company/{nse}/"
            elif bse:
                link = f"https://www.screener.in/company/{bse}/"
            else:
                link = None

            if link:
                st.markdown(f"🔗 [View {selected_stock} on Screener]({link})")

            show_market_cap_trend(selected_stock)
    else:
        st.info("No companies to display market‑cap trend.")


def show_market_cap_trend(selected_stock: str):
    try:
        hist_data = get_historical_market_cap()
        stock_data = hist_data[hist_data["name"] == selected_stock]
        if not stock_data.empty:
            fig = market_cap_line_chart(stock_data, selected_stock)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning(f"No market‑cap data available for {selected_stock}")
    except Exception as e:
        st.error(f"Could not load market‑cap data. Error: {e}")


if __name__ == "__main__":
    main()

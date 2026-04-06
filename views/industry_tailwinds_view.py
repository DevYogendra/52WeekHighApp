# views/industry_tailwinds_view.py

import pandas as pd
import streamlit as st

from db_utils import compute_industry_tailwind_stats, get_momentum_summary, get_tailwind_stocks
from grid_utils import render_interactive_table
from mcap_tier_utils import add_mcap_tier_col, apply_mcap_tier_filter, render_mcap_sidebar_filter


def _format_detail_table(df: pd.DataFrame, lookback_days: int) -> pd.DataFrame:
    hits_col = f"Hits {lookback_days}D"
    cols = {
        "name": "Stock",
        "hits_in_window": hits_col,
        "hits_30": "Hits 30D",
        "hits_60": "Hits 60D",
        "%_gain_mc": "Gain %",
        "market_cap": "Market Cap",
        "first_seen_date": "First Seen",
    }
    available = [c for c in cols if c in df.columns]
    detail_df = df[available].copy().rename(columns=cols)

    for col in [hits_col, "Hits 30D", "Hits 60D"]:
        if col in detail_df.columns:
            detail_df[col] = pd.to_numeric(detail_df[col], errors="coerce").astype("Int64")
    if "Gain %" in detail_df.columns:
        detail_df["Gain %"] = pd.to_numeric(detail_df["Gain %"], errors="coerce").map(
            lambda v: "-" if pd.isna(v) else f"{v:.1f}"
        )
    if "Market Cap" in detail_df.columns:
        detail_df["Market Cap"] = pd.to_numeric(detail_df["Market Cap"], errors="coerce").map(
            lambda v: "-" if pd.isna(v) else f"{v:,.0f}"
        )
    if "First Seen" in detail_df.columns:
        detail_df["First Seen"] = (
            pd.to_datetime(detail_df["First Seen"], errors="coerce")
            .dt.strftime("%Y-%m-%d")
            .fillna("-")
        )
    return detail_df


def main():
    st.title("🌪️ Industry Tailwinds")
    st.markdown(
        "Industries where a critical mass of stocks have **persistently** appeared "
        "on the 52-week high list over a multi-week window."
    )
    st.caption("Gain is market-cap weighted so a tiny outlier does not distort the industry trend.")

    st.sidebar.subheader("Filters")
    lookback   = st.sidebar.slider("Lookback Window (Days)", 30, 90, 60, key="tw_lookback")
    min_hits   = st.sidebar.slider("Min Appearances per Stock", 1, 20, 5, key="tw_min_hits")
    min_stocks = st.sidebar.slider("Min Qualifying Stocks per Industry", 1, 10, 3, key="tw_min_stocks")
    selected_tiers = render_mcap_sidebar_filter(key="tw_mcap_tier")

    active_df = get_tailwind_stocks(lookback, min_hits)
    if active_df.empty:
        st.info("No stocks match the selected filters.")
        return
    active_df = apply_mcap_tier_filter(
        add_mcap_tier_col(active_df, col="market_cap"), selected_tiers
    )
    if active_df.empty:
        st.info("No stocks match the selected MCap tier filter.")
        return

    # Total stocks per industry (all time) — used for breadth %
    all_df = get_momentum_summary()
    total_per_industry = (
        all_df.groupby("industry")["name"].count().rename("total_stocks").reset_index()
        if not all_df.empty else pd.DataFrame(columns=["industry", "total_stocks"])
    )

    industry_stats = compute_industry_tailwind_stats(active_df).rename(columns={
        "count_stocks":    "Qualifying_Stocks",
        "total_hits":      "Total_Hits",
        "avg_hits":        "Avg_Hits",
        "weighted_gain_mc": "Weighted_Gain_MCap",
    })
    industry_stats = industry_stats[industry_stats["Qualifying_Stocks"] >= min_stocks]

    if industry_stats.empty:
        st.info("No industries match the selected filters.")
        return

    # Breadth % = qualifying stocks / all stocks ever seen in that industry
    industry_stats = industry_stats.merge(total_per_industry, on="industry", how="left")
    industry_stats["Breadth_Pct"] = (
        100 * industry_stats["Qualifying_Stocks"] / industry_stats["total_stocks"]
    ).round(1)

    industry_stats = industry_stats.sort_values(
        ["Qualifying_Stocks", "Weighted_Gain_MCap"], ascending=[False, False]
    )

    st.caption(
        f"Showing industries with ≥ **{min_stocks}** stocks that appeared ≥ **{min_hits}×** "
        f"in the last **{lookback}** days. MCap tier filter applies to individual stocks before aggregation."
    )

    render_interactive_table(
        industry_stats,
        columns=["industry", "Qualifying_Stocks", "Total_Hits", "Avg_Hits", "Breadth_Pct", "Weighted_Gain_MCap"],
        key="industry_tailwinds_summary",
        rename_map={
            "industry":           "Industry",
            "Qualifying_Stocks":  "Stocks",
            "Total_Hits":         "Total Hits",
            "Avg_Hits":           "Avg Hits/Stock",
            "Breadth_Pct":        "Breadth %",
            "Weighted_Gain_MCap": "Weighted Gain %",
        },
        integer_cols=["Qualifying_Stocks", "Total_Hits"],
        one_decimal_cols=["Weighted_Gain_MCap", "Breadth_Pct"],
        two_decimal_cols=["Avg_Hits"],
        height=280,
    )

    # Per-industry expanders — join hits_30/hits_60 from momentum summary for context
    hits_context = (
        all_df[["name", "hits_30", "hits_60"]].copy() if not all_df.empty else pd.DataFrame()
    )

    st.markdown("### Industry details")
    st.caption("Open any industry to see the stocks behind the tailwind signal.")

    for industry_name in industry_stats["industry"].dropna().tolist():
        industry_stocks = (
            active_df[active_df["industry"] == industry_name]
            .copy()
            .sort_values("hits_in_window", ascending=False)
        )
        if not hits_context.empty:
            industry_stocks = industry_stocks.merge(hits_context, on="name", how="left")

        if industry_stocks.empty:
            continue

        row = industry_stats[industry_stats["industry"] == industry_name].iloc[0]
        expander_label = (
            f"{industry_name} | "
            f"{int(row['Qualifying_Stocks'])} stocks | "
            f"avg {row['Avg_Hits']:.1f} hits | "
            f"breadth {row['Breadth_Pct']:.0f}% | "
            f"weighted gain {row['Weighted_Gain_MCap']:.1f}%"
        )

        with st.expander(expander_label, expanded=False):
            st.dataframe(
                _format_detail_table(industry_stocks, lookback),
                use_container_width=True,
                hide_index=True,
            )

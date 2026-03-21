# views/industry_tailwinds_view.py

import pandas as pd
import streamlit as st

from db_utils import compute_industry_tailwind_stats, get_momentum_summary
from grid_utils import render_interactive_table


def main():
    st.title("🌪️ Industry Tailwinds")
    st.markdown("Industries with multiple momentum stocks hitting 52-week highs recently.")
    st.caption("Gain is market-cap weighted so a tiny outlier does not distort the industry trend.")

    st.sidebar.subheader("Filters")
    lookback = st.sidebar.slider("Minimum Hits in Last 7 Days", 1, 6, 2)
    min_stocks = st.sidebar.slider("Minimum Stocks per Industry", 1, 10, 3)

    df = get_momentum_summary()
    if df.empty:
        st.warning("No momentum data available.")
        return

    df_active = df[df["hits_7"] >= lookback].copy()
    industry_counts = compute_industry_tailwind_stats(df_active).rename(
        columns={
            "count_stocks": "Momentum_Stocks",
            "avg_hits_7": "Avg_Hits_7",
            "weighted_gain_mc": "Weighted_Gain_MCap",
        }
    )
    industry_counts = industry_counts[industry_counts["Momentum_Stocks"] >= min_stocks]
    industry_counts = industry_counts.sort_values(
        by=["Momentum_Stocks", "Weighted_Gain_MCap"],
        ascending=[False, False],
    )

    if industry_counts.empty:
        st.info("No industries match the selected filters.")
        return

    render_interactive_table(
        industry_counts,
        columns=["industry", "Momentum_Stocks", "Avg_Hits_7", "Weighted_Gain_MCap"],
        key="industry_tailwinds_summary",
        rename_map={
            "industry": "Industry",
            "Momentum_Stocks": "Stocks",
            "Avg_Hits_7": "Avg Hits 7D",
            "Weighted_Gain_MCap": "Weighted Gain %",
        },
        integer_cols=["Momentum_Stocks"],
        one_decimal_cols=["Weighted_Gain_MCap"],
        two_decimal_cols=["Avg_Hits_7"],
        height=280,
    )

    st.markdown("### Industry details")
    st.caption("Open any industry below to see the stocks behind the tailwind signal.")

    for industry_name in industry_counts["industry"].dropna().tolist():
        industry_stocks = (
            df_active[df_active["industry"] == industry_name]
            .copy()
            .sort_values(by=["hits_7", "%_gain_mc"], ascending=[False, False])
        )
        if industry_stocks.empty:
            continue

        summary_row = industry_counts[industry_counts["industry"] == industry_name].iloc[0]
        expander_label = (
            f"{industry_name} | "
            f"{int(summary_row['Momentum_Stocks'])} stocks | "
            f"avg hits {summary_row['Avg_Hits_7']:.1f} | "
            f"weighted gain {summary_row['Weighted_Gain_MCap']:.1f}%"
        )

        with st.expander(expander_label, expanded=False):
            render_interactive_table(
                industry_stocks,
                columns=["name", "hits_7", "hits_30", "hits_60", "%_gain_mc", "market_cap", "first_seen_date"],
                key=f"industry_tailwinds_{industry_name}",
                rename_map={
                    "name": "Stock",
                    "hits_7": "Hits 7D",
                    "hits_30": "Hits 30D",
                    "hits_60": "Hits 60D",
                    "%_gain_mc": "Gain %",
                    "market_cap": "Market Cap",
                    "first_seen_date": "First Seen",
                },
                integer_cols=["hits_7", "hits_30", "hits_60"],
                one_decimal_cols=["%_gain_mc"],
                major_cols=["market_cap"],
                link_col="name",
                height=260,
            )

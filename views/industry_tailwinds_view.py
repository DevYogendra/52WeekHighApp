# views/industry_tailwinds_view.py

import pandas as pd
import streamlit as st
import re

from db_utils import compute_industry_tailwind_stats, get_momentum_summary
from grid_utils import render_interactive_table

_TAG_RE = re.compile(r"<[^>]+>")


def _format_detail_table(df: pd.DataFrame) -> pd.DataFrame:
    detail_df = df[
        ["name", "hits_7", "hits_30", "hits_60", "%_gain_mc", "market_cap", "first_seen_date"]
    ].copy()
    detail_df = detail_df.rename(
        columns={
            "name": "Stock",
            "hits_7": "Hits 7D",
            "hits_30": "Hits 30D",
            "hits_60": "Hits 60D",
            "%_gain_mc": "Gain %",
            "market_cap": "Market Cap",
            "first_seen_date": "First Seen",
        }
    )
    detail_df["Stock"] = detail_df["Stock"].map(
        lambda value: "" if pd.isna(value) else _TAG_RE.sub("", str(value))
    )
    for col in ["Hits 7D", "Hits 30D", "Hits 60D"]:
        detail_df[col] = pd.to_numeric(detail_df[col], errors="coerce").astype("Int64")
    detail_df["Gain %"] = pd.to_numeric(detail_df["Gain %"], errors="coerce").map(
        lambda value: "-" if pd.isna(value) else f"{value:.1f}"
    )
    detail_df["Market Cap"] = pd.to_numeric(detail_df["Market Cap"], errors="coerce").map(
        lambda value: "-" if pd.isna(value) else f"{value:,.0f}"
    )
    detail_df["First Seen"] = pd.to_datetime(detail_df["First Seen"], errors="coerce").dt.strftime("%Y-%m-%d")
    detail_df["First Seen"] = detail_df["First Seen"].fillna("-")
    return detail_df


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
            st.dataframe(
                _format_detail_table(industry_stocks),
                use_container_width=True,
                hide_index=True,
            )

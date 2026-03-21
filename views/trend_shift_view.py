import datetime

import pandas as pd
import streamlit as st

from config import TABLE_HIGHS
from db_utils import get_historical_market_cap, get_latest_table_date
from grid_utils import render_interactive_table


def get_week_range(date):
    weekday = date.weekday()
    monday = date - datetime.timedelta(days=weekday)
    sunday = monday + datetime.timedelta(days=6)
    return monday, sunday


def compute_weekly_summary(df, start_date, end_date):
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    mask = (df["date"] >= start_date) & (df["date"] <= end_date)
    week_df = df[mask].copy()

    summary = week_df.groupby("name").agg(
        hits=("date", "count"),
        market_cap_start=("market_cap", "first"),
        market_cap_end=("market_cap", "last"),
        industry=("industry", "first"),
        nse_code=("nse_code", "first"),
        bse_code=("bse_code", "first"),
    ).reset_index()

    summary["gain_pct"] = 100 * (summary["market_cap_end"] - summary["market_cap_start"]) / summary["market_cap_start"]
    return summary


def main():
    st.title("Trend Shift Analyzer")
    st.markdown(
        """
        This page helps you analyze week-over-week momentum shifts across stocks in terms of:

        - Frequency of 52-week high appearances (`Hits`)
        - Change in market cap (`% Gain`)

        Use this tool to:
        - Identify rising momentum stocks early
        - Spot stocks losing momentum
        - Focus on companies within a specific market cap range

        Tip: Sort by Delta Hits or Delta Gain to surface accelerating trends.
        """
    )
    st.markdown("Compare weekly changes in momentum for stocks and industries.")
    st.caption("Use the MCap column filter in the table for market-cap screening.")

    df = get_historical_market_cap()
    if df.empty:
        st.warning("No historical market cap data available.")
        return

    df["date"] = pd.to_datetime(df["date"])

    latest_data_date = get_latest_table_date(TABLE_HIGHS)
    if latest_data_date is None:
        st.warning("No dated highs data available.")
        return

    this_mon, this_sun = get_week_range(latest_data_date)
    last_mon, last_sun = this_mon - datetime.timedelta(days=7), this_sun - datetime.timedelta(days=7)

    st.caption(f"Latest data date: {latest_data_date}")
    st.markdown(f"**This Week:** {this_mon} to {this_sun}")
    st.markdown(f"**Last Week:** {last_mon} to {last_sun}")

    this_week = compute_weekly_summary(df, this_mon, this_sun)
    last_week = compute_weekly_summary(df, last_mon, last_sun)

    merged = pd.merge(
        this_week,
        last_week,
        on="name",
        how="outer",
        suffixes=("_this", "_last"),
    )

    merged["hits_delta"] = merged["hits_this"].fillna(0) - merged["hits_last"].fillna(0)
    merged["gain_delta"] = merged["gain_pct_this"].fillna(0) - merged["gain_pct_last"].fillna(0)
    merged = merged.sort_values(by="hits_delta", ascending=False)

    merged["market_cap_cr"] = merged["market_cap_end_this"] / 1e7
    filtered = merged.copy()
    filtered["nse_code"] = filtered["nse_code_this"]
    filtered["bse_code"] = filtered["bse_code_this"]

    rising = filtered[(filtered["hits_delta"] > 0) & (filtered["gain_delta"] > 0)].copy()
    losing = filtered[(filtered["hits_delta"] < 0) & (filtered["gain_delta"] < 0)].copy()

    def render_table(frame, title):
        st.markdown(f"### {title}")
        render_interactive_table(
            frame,
            columns=[
                "name",
                "industry_this",
                "market_cap_end_this",
                "hits_last",
                "hits_this",
                "gain_pct_last",
                "gain_pct_this",
                "hits_delta",
                "gain_delta",
            ],
            key=f"trend_shift_{title.replace(' ', '_').lower()}",
            rename_map={
                "name": "Company",
                "industry_this": "Industry",
                "market_cap_end_this": "MCap",
                "hits_last": "Hits LW",
                "hits_this": "Hits TW",
                "gain_pct_last": "%Gain LW",
                "gain_pct_this": "%Gain TW",
                "hits_delta": "Delta Hits",
                "gain_delta": "Delta Gain",
            },
            integer_cols=["hits_last", "hits_this", "hits_delta"],
            one_decimal_cols=["gain_pct_last", "gain_pct_this", "gain_delta"],
            major_cols=["market_cap_end_this"],
            link_col="name",
            height=320,
        )

    render_table(rising, "Stocks with Rising Momentum")
    render_table(losing, "Stocks Losing Momentum")


if __name__ == "__main__":
    main()

import streamlit as st
import pandas as pd
import datetime
from db_utils import get_historical_market_cap


def get_week_range(date):
    # Get previous Monday and Sunday
    weekday = date.weekday()
    monday = date - datetime.timedelta(days=weekday)
    sunday = monday + datetime.timedelta(days=6)
    return monday, sunday


def compute_weekly_summary(df, start_date, end_date):
    mask = (df["date"] >= start_date) & (df["date"] <= end_date)
    week_df = df[mask].copy()

    summary = week_df.groupby("name").agg(
        hits=("date", "count"),
        market_cap_start=("market_cap", "first"),
        market_cap_end=("market_cap", "last"),
        industry=("industry", "first")
    )
    summary["gain_pct"] = 100 * (summary["market_cap_end"] - summary["market_cap_start"]) / summary["market_cap_start"]
    return summary.reset_index()


def main():
    st.title("📊 Trend Shift Analyzer")
    st.markdown("Compare weekly changes in momentum for stocks and industries.")

    df = get_historical_market_cap()
    today = datetime.date.today()

    this_mon, this_sun = get_week_range(today)
    last_mon, last_sun = this_mon - datetime.timedelta(days=7), this_sun - datetime.timedelta(days=7)

    st.markdown(f"**This Week:** {this_mon} → {this_sun}")
    st.markdown(f"**Last Week:** {last_mon} → {last_sun}")

    this_week = compute_weekly_summary(df, this_mon, this_sun)
    last_week = compute_weekly_summary(df, last_mon, last_sun)

    merged = pd.merge(
        this_week,
        last_week,
        on="name",
        how="outer",
        suffixes=("_this", "_last")
    )

    merged["hits_delta"] = merged["hits_this"].fillna(0) - merged["hits_last"].fillna(0)
    merged["gain_delta"] = merged["gain_pct_this"].fillna(0) - merged["gain_pct_last"].fillna(0)

    merged = merged.sort_values(by="hits_delta", ascending=False)

    st.markdown("### 📈 Stocks with Rising Momentum")
    st.dataframe(
        merged[(merged["hits_delta"] > 0) & (merged["gain_delta"] > 0)][
            ["name", "industry_this", "hits_last", "hits_this", "gain_pct_last", "gain_pct_this", "hits_delta", "gain_delta"]
        ].rename(columns={"industry_this": "industry"}),
        use_container_width=True
    )

    st.markdown("### 📉 Stocks Losing Momentum")
    st.dataframe(
        merged[(merged["hits_delta"] < 0) & (merged["gain_delta"] < 0)][
            ["name", "industry_this", "hits_last", "hits_this", "gain_pct_last", "gain_pct_this", "hits_delta", "gain_delta"]
        ].rename(columns={"industry_this": "industry"}),
        use_container_width=True
    )

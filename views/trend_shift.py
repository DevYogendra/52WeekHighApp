import datetime

import pandas as pd
import streamlit as st

from config import TABLE_HIGHS
from db_utils import add_screener_links, get_historical_market_cap, get_latest_table_date


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
    st.title("📊 Trend Shift Analyzer")
    st.markdown(
        """
        This page helps you **analyze week-over-week momentum shifts** across stocks in terms of:

        - 📈 Frequency of 52-week high appearances (`Hits`)
        - 📊 Change in market cap (`% Gain`)

        Use this tool to:
        - Identify **rising momentum stocks** early
        - Spot stocks **losing momentum** (risk of trend reversal)
        - Focus on companies within a specific **Market Cap range** (e.g., midcaps)

        **Tip:** Sort by Δ Hits or Δ Gain to surface accelerating trends.
        """
    )
    st.markdown("Compare weekly changes in momentum for stocks and industries.")

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
    market_cap_cr = merged["market_cap_cr"].dropna()
    if market_cap_cr.empty:
        st.warning("No market cap data available for filtering.")
        return

    min_cr = int(market_cap_cr.min())
    max_cr = int(market_cap_cr.max())
    if min_cr == max_cr:
        max_cr += 1

    cr_filter = st.sidebar.slider("Market Cap Filter (₹ Cr)", min_value=min_cr, max_value=max_cr, value=(min_cr, max_cr))

    filtered = merged[merged["market_cap_cr"].between(cr_filter[0], cr_filter[1])].copy()
    filtered["nse_code"] = filtered["nse_code_this"]
    filtered["bse_code"] = filtered["bse_code_this"]
    filtered = add_screener_links(filtered)

    rising = filtered[(filtered["hits_delta"] > 0) & (filtered["gain_delta"] > 0)].copy()
    losing = filtered[(filtered["hits_delta"] < 0) & (filtered["gain_delta"] < 0)].copy()

    def render_table(frame, title):
        st.markdown(f"### {title}")
        if frame.empty:
            st.info("No matching stocks.")
            return

        display_df = frame[
            [
                "name",
                "industry_this",
                "market_cap_end_this",
                "hits_last",
                "hits_this",
                "gain_pct_last",
                "gain_pct_this",
                "hits_delta",
                "gain_delta",
            ]
        ].rename(
            columns={
                "name": "Company",
                "industry_this": "Industry",
                "market_cap_end_this": "MCap",
                "hits_last": "Hits LW",
                "hits_this": "Hits TW",
                "gain_pct_last": "%Gain LW",
                "gain_pct_this": "%Gain TW",
                "hits_delta": "Δ Hits",
                "gain_delta": "Δ Gain",
            }
        )

        display_df["MCap"] = display_df["MCap"].map(lambda x: f"₹{x:,.0f}" if pd.notna(x) else "-")
        for col in ["%Gain LW", "%Gain TW", "Δ Gain"]:
            display_df[col] = pd.to_numeric(display_df[col], errors="coerce").round(1)

        html_table = display_df.style.hide(axis="index").to_html(escape=False)
        st.markdown(html_table, unsafe_allow_html=True)

    render_table(rising, "📈 Stocks with Rising Momentum")
    render_table(losing, "📉 Stocks Losing Momentum")


if __name__ == "__main__":
    main()

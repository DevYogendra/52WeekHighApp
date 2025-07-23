import streamlit as st
import pandas as pd
import datetime
from db_utils import get_historical_market_cap, add_screener_links


def get_week_range(date):
    # Get previous Monday and Sunday
    weekday = date.weekday()
    monday = date - datetime.timedelta(days=weekday)
    sunday = monday + datetime.timedelta(days=6)
    return monday, sunday


def compute_weekly_summary(df, start_date, end_date):
    # Ensure date range is in pandas datetime format
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
        bse_code=("bse_code", "first")
    )
    summary["gain_pct"] = 100 * (summary["market_cap_end"] - summary["market_cap_start"]) / summary["market_cap_start"]
    return summary.reset_index()


def main():
    st.title("📊 Trend Shift Analyzer")
    st.markdown("Compare weekly changes in momentum for stocks and industries.")

    df = get_historical_market_cap()
    df["date"] = pd.to_datetime(df["date"])  # Ensure date column is datetime

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
        suffixes=('_this', '_last')
    )

    merged["hits_delta"] = merged["hits_this"].fillna(0) - merged["hits_last"].fillna(0)
    merged["gain_delta"] = merged["gain_pct_this"].fillna(0) - merged["gain_pct_last"].fillna(0)

    merged = merged.sort_values(by="hits_delta", ascending=False)

    # Add Market Cap filter
    min_cap, max_cap = float(merged["market_cap_end_this"].min()), float(merged["market_cap_end_this"].max())
    cap_filter = st.sidebar.slider("Market Cap Filter (This Week)", int(min_cap), int(max_cap), (int(min_cap), int(max_cap)))

    filtered = merged[merged["market_cap_end_this"].between(cap_filter[0], cap_filter[1])].copy()

    # Add links
    filtered = add_screener_links(filtered)

    rising = filtered[(filtered["hits_delta"] > 0) & (filtered["gain_delta"] > 0)].copy()
    losing = filtered[(filtered["hits_delta"] < 0) & (filtered["gain_delta"] < 0)].copy()

    def render_markdown_table(df, title):
        if df.empty:
            st.markdown(f"**{title}**\n\n_No matching stocks._")
            return
        display_cols = [
            "name", "industry_this", "market_cap_end_this",
            "hits_last", "hits_this", "gain_pct_last", "gain_pct_this",
            "hits_delta", "gain_delta"
        ]
        df = df[display_cols].rename(columns={
            "name": "Company",
            "industry_this": "Industry",
            "market_cap_end_this": "MCap",
            "hits_last": "Hits LW",
            "hits_this": "Hits TW",
            "gain_pct_last": "%Gain LW",
            "gain_pct_this": "%Gain TW",
            "hits_delta": "Δ Hits",
            "gain_delta": "Δ Gain"
        })
        df["MCap"] = df["MCap"].apply(lambda x: f"₹{x:,.0f}")
        df["%Gain LW"] = df["%Gain LW"].round(1)
        df["%Gain TW"] = df["%Gain TW"].round(1)
        df["Δ Gain"] = df["Δ Gain"].round(1)
        st.markdown(f"### {title}")
        st.markdown(df.to_markdown(index=False), unsafe_allow_html=True)

    render_markdown_table(rising, "📈 Stocks with Rising Momentum")
    render_markdown_table(losing, "📉 Stocks Losing Momentum")

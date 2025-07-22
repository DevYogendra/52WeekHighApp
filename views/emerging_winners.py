# views/emerging_winners.py

import streamlit as st
import sqlite3
import datetime
import pandas as pd

DB_PATH = "highs.db"

def fetch_emerging_winners(recent_days=7, min_appearances=2, min_gain_pct=5):
    today = datetime.date.today()
    recent_cutoff = today - datetime.timedelta(days=recent_days)

    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    query = f"""
    SELECT name, first_seen_date, first_market_cap,
           COUNT(*) as appearance_count,
           MAX(market_cap) as latest_market_cap
    FROM highs
    WHERE date >= ? AND first_seen_date >= ?
    GROUP BY name
    HAVING appearance_count >= ? AND
           ((latest_market_cap - first_market_cap) * 100.0 / first_market_cap) >= ?
    ORDER BY ((latest_market_cap - first_market_cap) * 100.0 / first_market_cap) DESC
    """

    params = (recent_cutoff, recent_cutoff, min_appearances, min_gain_pct)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    if not df.empty:
        df["Market Cap Gain (%)"] = ((df["latest_market_cap"] - df["first_market_cap"]) * 100 / df["first_market_cap"]).round(2)
        df.rename(columns={
            "name": "Company",
            "first_seen_date": "First Seen",
            "appearance_count": "Appearances (7d)",
            "first_market_cap": "Market Cap Then",
            "latest_market_cap": "Market Cap Now"
        }, inplace=True)

    return df

def main():
    st.title("🚀 Emerging Winners")
    st.markdown("Stocks that recently started hitting 52-week highs and are gaining momentum.")

    st.sidebar.subheader("Filters")
    recent_days = st.sidebar.slider("Lookback Window (Days)", 3, 15, 7)
    min_appearances = st.sidebar.slider("Min Appearances", 1, 5, 2)
    min_gain_pct = st.sidebar.slider("Min Market Cap Gain (%)", 0, 50, 5)

    df = fetch_emerging_winners(recent_days, min_appearances, min_gain_pct)

    if df.empty:
        st.info("No emerging winners match the selected filters.")
    else:
        st.dataframe(df, use_container_width=True)


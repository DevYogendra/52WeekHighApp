# views/emerging_winners_view.py

import datetime
import sqlite3

import pandas as pd
import streamlit as st

from config import CACHE_TTL, DB_PATH, TABLE_HIGHS
from db_utils import get_latest_table_date
from grid_utils import render_interactive_table


@st.cache_data(ttl=CACHE_TTL)
def fetch_emerging_winners(recent_days: int = 7, min_appearances: int = 2, min_gain_pct: int = 5) -> pd.DataFrame:
    latest_data_date = get_latest_table_date(TABLE_HIGHS)
    if latest_data_date is None:
        return pd.DataFrame()

    recent_cutoff = latest_data_date - datetime.timedelta(days=recent_days - 1)

    with sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES) as conn:
        query = f"""
        SELECT
            name,
            industry,
            nse_code,
            bse_code,
            first_seen_date,
            first_market_cap,
            COUNT(*) as appearance_count,
            MAX(market_cap) as latest_market_cap
        FROM {TABLE_HIGHS}
        WHERE date BETWEEN ? AND ? AND first_seen_date >= ?
        GROUP BY name, industry, nse_code, bse_code, first_seen_date, first_market_cap
        HAVING appearance_count >= ? AND
               ((latest_market_cap - first_market_cap) * 100.0 / NULLIF(first_market_cap, 0)) >= ?
        ORDER BY ((latest_market_cap - first_market_cap) * 100.0 / NULLIF(first_market_cap, 0)) DESC
        """
        params = (recent_cutoff, latest_data_date, recent_cutoff, min_appearances, min_gain_pct)
        df = pd.read_sql_query(query, conn, params=params)

    if df.empty:
        return df

    df["Market Cap Gain (%)"] = (
        (df["latest_market_cap"] - df["first_market_cap"]) * 100 / df["first_market_cap"]
    ).round(2)
    return df.rename(
        columns={
            "name": "Company",
            "industry": "Industry",
            "first_seen_date": "First Seen",
            "appearance_count": "Appearances",
            "first_market_cap": "Market Cap Then",
            "latest_market_cap": "Market Cap Now",
        }
    )


def main():
    st.title("🚀 Emerging Winners")
    st.markdown("Stocks that recently started hitting 52-week highs and are gaining momentum.")

    latest_data_date = get_latest_table_date(TABLE_HIGHS)
    if latest_data_date is not None:
        st.caption(f"Latest data date: {latest_data_date}")

    st.sidebar.subheader("Filters")
    recent_days = st.sidebar.slider("Lookback Window (Days)", 3, 15, 7)
    min_appearances = st.sidebar.slider("Min Appearances", 1, 5, 2)
    min_gain_pct = st.sidebar.slider("Min Market Cap Gain (%)", 0, 50, 5)

    df = fetch_emerging_winners(recent_days, min_appearances, min_gain_pct)

    if df.empty:
        st.info("No emerging winners match the selected filters.")
        return

    render_interactive_table(
        df,
        columns=[
            "Company",
            "Industry",
            "First Seen",
            "Appearances",
            "Market Cap Then",
            "Market Cap Now",
            "Market Cap Gain (%)",
        ],
        key="emerging_winners_main",
        integer_cols=["Appearances"],
        one_decimal_cols=["Market Cap Gain (%)"],
        major_cols=["Market Cap Then", "Market Cap Now"],
        link_col="Company",
        height=460,
        fit_columns=True,
    )


if __name__ == "__main__":
    main()

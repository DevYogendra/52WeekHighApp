# views/industry_tailwinds.py

import streamlit as st
from db_utils import get_momentum_summary

def main():
    st.title("🌪️ Industry Tailwinds")
    st.markdown("Industries with multiple momentum stocks hitting 52-week highs recently.")

    df = get_momentum_summary()

    lookback = st.slider("Minimum Hits in Last 7 Days", 1, 10, 2)
    min_stocks = st.slider("Minimum Stocks per Industry", 1, 10, 3)

    # Filter for active stocks only
    df_active = df[df["hits_7"] >= lookback]
    industry_counts = df_active.groupby("industry").agg(
        Momentum_Stocks=("name", "count"),
        Avg_Hits_7=("hits_7", "mean"),
        Avg_Gain_MCap=("%_gain_mc", "mean")
    ).reset_index()

    industry_counts = industry_counts[industry_counts["Momentum_Stocks"] >= min_stocks]
    industry_counts = industry_counts.sort_values(by="Momentum_Stocks", ascending=False)

    st.dataframe(industry_counts, use_container_width=True)

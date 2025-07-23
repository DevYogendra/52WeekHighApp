# views/trend_analyzer.py

import streamlit as st
import pandas as pd
from db_utils import get_momentum_summary, add_screener_links

def main():
    st.title("📈 Trend Analyzer")
    st.markdown("Identify consistent and accelerating performers based on 52-week high appearances.")

    df = get_momentum_summary()
    df["Trend Score"] = df["hits_7"] * 3 + df["hits_30"] * 2 + df["hits_60"]
    df = df[df["hits_7"] > 0].sort_values(by="Trend Score", ascending=False)

    df = add_screener_links(df)

    # Format for markdown rendering
    df_display = df.copy()
    df_display["name"] = df_display["name"].astype(str)

    # Show as HTML table using unsafe_allow_html
    st.caption("Weighted score = 3×7-day + 2×30-day + 1×60-day hits.")
    st.markdown(
        df_display[[
            "name", "industry", "market_cap", "first_market_cap", "%_gain_mc",
            "hits_7", "hits_30", "hits_60", "Trend Score"
        ]].to_html(escape=False, index=False),
        unsafe_allow_html=True
    )

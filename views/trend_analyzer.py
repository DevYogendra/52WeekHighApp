# views/trend_analyzer.py

import streamlit as st
from db_utils import get_momentum_summary, add_screener_links

def main():
    st.title("📈 Trend Analyzer")
    st.markdown("Identify consistent and accelerating performers based on 52-week high appearances.")

    df = get_momentum_summary()
    df["Trend Score"] = df["hits_7"] * 3 + df["hits_30"] * 2 + df["hits_60"]
    df = df[df["hits_7"] > 0].sort_values(by="Trend Score", ascending=False)

    st.caption("Weighted score: 3×7-day + 2×30-day + 1×60-day hits.")
    st.dataframe(add_screener_links(df), use_container_width=True)

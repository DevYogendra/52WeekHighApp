# views/industry_tailwinds.py

import streamlit as st
from db_utils import get_momentum_summary

def main():
    st.title("🌪️ Industry Tailwinds")
    st.markdown("Industries with multiple momentum stocks hitting 52-week highs recently.")

    st.sidebar.subheader("Filters")
    lookback = st.sidebar.slider("Minimum Hits in Last 7 Days", 1, 7, 2)
    min_stocks = st.sidebar.slider("Minimum Stocks per Industry", 1, 10, 3)
    
    df = get_momentum_summary()

    # Filter for active stocks only
    df_active = df[df["hits_7"] >= lookback]
    industry_counts = df_active.groupby("industry").agg(
        Momentum_Stocks=("name", "count"),
        Avg_Hits_7=("hits_7", "mean"),
        Avg_Gain_MCap=("%_gain_mc", "mean")
    ).reset_index()

    industry_counts = industry_counts[industry_counts["Momentum_Stocks"] >= min_stocks]
    industry_counts = industry_counts.sort_values(by="Momentum_Stocks", ascending=False)

    # Format values for display
    industry_counts["Avg_Hits_7"] = industry_counts["Avg_Hits_7"].round(2)
    industry_counts["Avg_Gain_MCap"] = industry_counts["Avg_Gain_MCap"].map(lambda x: f"{x:.1f}%")

    # Convert to Markdown table
    markdown_table = industry_counts.to_markdown(index=False)

    st.markdown(f"```markdown\n{markdown_table}\n```")

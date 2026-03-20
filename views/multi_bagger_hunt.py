import streamlit as st
import pandas as pd
import plotly.express as px
from db_utils import get_persistence_scores, get_frequency_timeline, add_screener_links


def main():
    st.title("🎯 Multi-Bagger Hunt")
    st.markdown(
        """
        This page ranks stocks by persistence in 52-week highs.
        Focus is on stocks that keep appearing in highs and are accelerating.
        """
    )

    # Get candidate scores
    df = get_persistence_scores()
    if df.empty:
        st.warning("No persistence data available. Make sure the database contains `highs` data.")
        return

    # Market cap filter in crores (approx)
    df["market_cap_cr"] = (df["market_cap"].fillna(0) / 1e7).astype(float)
    min_mcap = int(df["market_cap_cr"].min())
    max_mcap = int(df["market_cap_cr"].max())

    if min_mcap >= max_mcap:
        # Streamlit slider requires min < max for range sliders
        max_mcap = min_mcap + 1

    cap_range = st.sidebar.slider(
        "Market Cap range (₹ Cr)",
        min_value=min_mcap,
        max_value=max_mcap,
        value=(min_mcap, max_mcap),
    )

    min_hits = st.sidebar.slider("Minimum hits in 7 days", min_value=0, max_value=int(df["hits_7"].max()), value=2)
    score_cutoff = st.sidebar.slider("Minimum persistence score", min_value=0.0, max_value=float(df["persistence_score"].max()), value=20.0)

    df = df[
        (df["hits_7"] >= min_hits) &
        (df["persistence_score"] >= score_cutoff) &
        (df["market_cap_cr"].between(cap_range[0], cap_range[1]))
    ]

    if df.empty:
        st.info("No candidates match the selected filters.")
        return

    df = add_screener_links(df)
    df["name_text"] = df["name"].str.replace(r"<[^>]*>", "", regex=True).astype("string")

    st.markdown("### Top multi-bagger candidates")
    show_cols = ["name", "industry", "hits_7", "hits_30", "hits_60", "%_gain_mc", "persistence_score"]
    html_table = df[show_cols].sort_values(by="persistence_score", ascending=False).style.format({"%_gain_mc": "{:.2f}", "persistence_score": "{:.2f}"}).to_html(index=False, escape=False)
    st.markdown(html_table, unsafe_allow_html=True)

    top_stock = st.selectbox("Select stock for frequency timeline", options=df["name_text"].tolist())
    if top_stock:
        timeline = get_frequency_timeline(top_stock)
        if timeline.empty:
            st.warning(f"No timeline data available for {top_stock}.")
        else:
            fig = px.bar(timeline, x="week", y="frequency", title=f"Weekly 52W-high frequency: {top_stock}")
            st.plotly_chart(fig, use_container_width=True)

    # Industry tailwind summary
    st.markdown("### Industry tailwind signals")
    industry_stats = df.groupby("industry").agg(
        count_stocks=("name", "count"),
        avg_hits_7=("hits_7", "mean"),
        avg_persistence=("persistence_score", "mean"),
        avg_gain_mc=("%_gain_mc", "mean")
    ).reset_index()

    industry_stats["tailwind_score"] = (
        industry_stats["avg_persistence"] * 0.5 +
        industry_stats["avg_hits_7"] * 0.3 +
        (industry_stats["avg_gain_mc"].fillna(0) / 100) * 0.2
    )

    industry_stats = industry_stats.sort_values(by="tailwind_score", ascending=False)
    st.dataframe(industry_stats.style.format({"avg_hits_7": "{:.2f}", "avg_persistence": "{:.2f}", "avg_gain_mc": "{:.2f}", "tailwind_score": "{:.2f}"}))

    st.markdown("---")
    st.markdown(
        "*Persistence score = 40% (7/30 hit ratio) + 30% (30/60 hit ratio) + 30% (market-cap gain). Frequent high hits and a rising score indicate strong momentum potential.*"
    )

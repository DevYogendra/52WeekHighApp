import streamlit as st
import pandas as pd
import plotly.express as px
from db_utils import get_persistence_scores, get_frequency_timeline, add_screener_links, compute_industry_tailwind_stats


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
    industry_stats = compute_industry_tailwind_stats(df)
    avg_persistence = (
        df.groupby("industry", dropna=False)["persistence_score"]
        .mean()
        .rename("avg_persistence")
        .reset_index()
    )
    industry_stats = industry_stats.merge(avg_persistence, on="industry", how="left")

    industry_stats["tailwind_score"] = (
        industry_stats["avg_persistence"] * 0.5 +
        industry_stats["avg_hits_7"] * 0.3 +
        (industry_stats["weighted_gain_mc"].fillna(0) / 100) * 0.2
    )

    industry_stats = industry_stats.sort_values(by="tailwind_score", ascending=False)
    st.dataframe(
        industry_stats.rename(
            columns={
                "industry": "Industry",
                "count_stocks": "Stocks",
                "avg_hits_7": "Avg Hits 7D",
                "avg_persistence": "Avg Persistence",
                "weighted_gain_mc": "Weighted Gain %",
                "tailwind_score": "Tailwind Score",
            }
        ).style.format(
            {
                "Avg Hits 7D": "{:.2f}",
                "Avg Persistence": "{:.2f}",
                "Weighted Gain %": "{:.2f}",
                "Tailwind Score": "{:.2f}",
            }
        )
    )
    st.caption("Open an industry below to see the stocks behind the tailwind signal.")

    for industry_name in industry_stats["industry"].dropna().tolist():
        industry_df = (
            df[df["industry"] == industry_name]
            .copy()
            .sort_values(by=["persistence_score", "hits_7", "%_gain_mc"], ascending=[False, False, False])
        )
        if industry_df.empty:
            continue

        summary_row = industry_stats[industry_stats["industry"] == industry_name].iloc[0]
        expander_label = (
            f"{industry_name} | "
            f"{int(summary_row['count_stocks'])} stocks | "
            f"avg persistence {summary_row['avg_persistence']:.1f} | "
            f"weighted gain {summary_row['weighted_gain_mc']:.1f}%"
        )

        detail_table = industry_df[
            ["name", "hits_7", "hits_30", "hits_60", "%_gain_mc", "persistence_score"]
        ].rename(
            columns={
                "name": "Stock",
                "hits_7": "Hits 7D",
                "hits_30": "Hits 30D",
                "hits_60": "Hits 60D",
                "%_gain_mc": "Gain %",
                "persistence_score": "Persistence Score",
            }
        )

        with st.expander(expander_label, expanded=False):
            html_table = detail_table.style.format(
                {"Gain %": "{:.2f}", "Persistence Score": "{:.2f}"}
            ).hide(axis="index").to_html(escape=False)
            st.markdown(html_table, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(
        "*Persistence score = 40% (7/30 hit ratio) + 30% (30/60 hit ratio) + 30% (market-cap gain). Frequent high hits and a rising score indicate strong momentum potential.*"
    )

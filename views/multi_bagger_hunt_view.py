import pandas as pd
import plotly.express as px
import streamlit as st

from db_utils import (
    compute_industry_tailwind_stats,
    get_frequency_timeline,
    get_persistence_scores,
)
from grid_utils import render_interactive_table


def main():
    st.title("Multi-Bagger Hunt")
    st.markdown(
        """
        This page ranks stocks by persistence in 52-week highs.
        Focus is on stocks that keep appearing in highs and are accelerating.
        """
    )

    df = get_persistence_scores()
    if df.empty:
        st.warning("No persistence data available. Make sure the database contains `highs` data.")
        return

    df["market_cap_cr"] = (df["market_cap"].fillna(0) / 1e7).astype(float)
    min_hits = st.sidebar.number_input(
        "Minimum hits in 7 days",
        min_value=0,
        max_value=int(df["hits_7"].max()),
        value=2,
        step=1,
    )
    score_cutoff = st.sidebar.number_input(
        "Minimum persistence score",
        min_value=0.0,
        max_value=float(df["persistence_score"].max()),
        value=20.0,
        step=1.0,
    )

    df = df[
        (df["hits_7"] >= min_hits)
        & (df["persistence_score"] >= score_cutoff)
    ]

    if df.empty:
        st.info("No candidates match the selected filters.")
        return

    df["name_text"] = df["name"].astype("string")

    st.markdown("### Top multi-bagger candidates")
    st.caption("Use the grid's MCap (Cr) column filter for market-cap screening.")
    show_cols = ["name", "industry", "market_cap_cr", "hits_7", "hits_30", "hits_60", "%_gain_mc", "persistence_score"]
    render_interactive_table(
        df.sort_values(by="persistence_score", ascending=False),
        columns=show_cols,
        key="multi_bagger_candidates",
        rename_map={"market_cap_cr": "MCap (Cr)", "%_gain_mc": "Gain %", "persistence_score": "Persistence Score"},
        integer_cols=["hits_7", "hits_30", "hits_60"],
        one_decimal_cols=["%_gain_mc"],
        two_decimal_cols=["persistence_score"],
        major_cols=["market_cap_cr"],
        link_col="name",
        height=420,
    )

    top_stock = st.selectbox("Select stock for frequency timeline", options=df["name_text"].tolist())
    if top_stock:
        timeline = get_frequency_timeline(top_stock)
        if timeline.empty:
            st.warning(f"No timeline data available for {top_stock}.")
        else:
            fig = px.bar(timeline, x="week", y="frequency", title=f"Weekly 52W-high frequency: {top_stock}")
            st.plotly_chart(fig, use_container_width=True)

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
        industry_stats["avg_persistence"] * 0.5
        + industry_stats["avg_hits_7"] * 0.3
        + (industry_stats["weighted_gain_mc"].fillna(0) / 100) * 0.2
    )

    industry_stats = industry_stats.sort_values(by="tailwind_score", ascending=False)
    render_interactive_table(
        industry_stats,
        columns=["industry", "count_stocks", "avg_hits_7", "avg_persistence", "weighted_gain_mc", "tailwind_score"],
        key="multi_bagger_industry_summary",
        rename_map={
            "industry": "Industry",
            "count_stocks": "Stocks",
            "avg_hits_7": "Avg Hits 7D",
            "avg_persistence": "Avg Persistence",
            "weighted_gain_mc": "Weighted Gain %",
            "tailwind_score": "Tailwind Score",
        },
        integer_cols=["count_stocks"],
        two_decimal_cols=["avg_hits_7", "avg_persistence", "weighted_gain_mc", "tailwind_score"],
        height=320,
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

        with st.expander(expander_label, expanded=False):
            render_interactive_table(
                industry_df,
                columns=["name", "hits_7", "hits_30", "hits_60", "%_gain_mc", "persistence_score"],
                key=f"multi_bagger_{industry_name}",
                rename_map={
                    "name": "Stock",
                    "hits_7": "Hits 7D",
                    "hits_30": "Hits 30D",
                    "hits_60": "Hits 60D",
                    "%_gain_mc": "Gain %",
                    "persistence_score": "Persistence Score",
                },
                integer_cols=["hits_7", "hits_30", "hits_60"],
                one_decimal_cols=["%_gain_mc"],
                two_decimal_cols=["persistence_score"],
                link_col="name",
                height=260,
            )

    st.markdown("---")
    st.markdown(
        "*Persistence score = 40% (7/30 hit ratio) + 30% (30/60 hit ratio) + 30% (market-cap gain). Frequent high hits and a rising score indicate strong momentum potential.*"
    )


if __name__ == "__main__":
    main()

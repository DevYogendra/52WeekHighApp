# views/momentum_view.py
# Consolidates: trend_analyzer_view, trend_shift_view, emerging_winners_view,
#               momentum_summary_view, multi_bagger_hunt_view

import datetime
import sqlite3

import pandas as pd
import plotly.express as px
import streamlit as st

from config import CACHE_TTL, DB_PATH, TABLE_HIGHS
from db_utils import (
    get_frequency_timeline,
    get_historical_market_cap,
    get_im_momentum_scores,
    get_latest_table_date,
    get_momentum_summary,
    get_persistence_scores,
)
from grid_utils import render_interactive_table
from plot_utils import market_cap_line_chart


# ── shared helpers ────────────────────────────────────────────────────────────

def _latest_date():
    return get_latest_table_date(TABLE_HIGHS)


def _week_range(date):
    monday = date - datetime.timedelta(days=date.weekday())
    return monday, monday + datetime.timedelta(days=6)


def _weekly_summary(df, start, end):
    mask = (df["date"] >= pd.to_datetime(start)) & (df["date"] <= pd.to_datetime(end))
    week_df = df.loc[mask].copy()
    if week_df.empty:
        return pd.DataFrame()
    summary = week_df.groupby("name").agg(
        hits=("date", "count"),
        market_cap_start=("market_cap", "first"),
        market_cap_end=("market_cap", "last"),
        industry=("industry", "first"),
        nse_code=("nse_code", "first"),
        bse_code=("bse_code", "first"),
    ).reset_index()
    summary["gain_pct"] = (
        100 * (summary["market_cap_end"] - summary["market_cap_start"])
        / summary["market_cap_start"].replace(0, pd.NA)
    )
    return summary


# ── tab renderers ─────────────────────────────────────────────────────────────

def _render_trend_leaders():
    df = get_momentum_summary()
    if df.empty:
        st.warning("No momentum data available.")
        return

    latest_date = _latest_date()
    if latest_date:
        st.caption(f"Latest data date: {latest_date}")

    # sidebar filters
    industries = ["All"] + sorted(df["industry"].dropna().unique().tolist())
    selected_industry = st.sidebar.selectbox("Filter by Industry", industries, key="tl_industry")
    min_hits = st.sidebar.number_input("Min hits (last 30 days)", min_value=0, max_value=30, value=1, step=1, key="tl_min_hits")

    df["hits_7"] = df["hits_7"].fillna(0).astype(int)
    df["hits_30"] = df["hits_30"].fillna(0).astype(int)
    df["hits_60"] = df["hits_60"].fillna(0).astype(int)

    df["Hits 0-7D"]  = df["hits_7"]
    df["Hits 8-30D"] = (df["hits_30"] - df["hits_7"]).clip(lower=0)
    df["Hits 31-60D"] = (df["hits_60"] - df["hits_30"]).clip(lower=0)
    df["Trend Score"] = df["Hits 0-7D"] * 3 + df["Hits 8-30D"] * 2 + df["Hits 31-60D"]
    df["Acceleration"] = ((df["Hits 0-7D"] / 7.0) - (df["Hits 8-30D"] / 23.0)).round(3)

    filtered = df[df["hits_7"] > 0]
    if selected_industry != "All":
        filtered = filtered[filtered["industry"] == selected_industry]
    filtered = filtered[filtered["hits_30"] >= min_hits]
    filtered = filtered.sort_values(["Trend Score", "Acceleration", "%_gain_mc"], ascending=[False, False, False])

    st.caption("Trend Score = 3×Hits 0-7D + 2×Hits 8-30D + 1×Hits 31-60D. Acceleration = recent daily hit rate vs prior 23 days.")

    render_interactive_table(
        filtered,
        columns=["name", "industry", "market_cap", "first_market_cap", "%_gain_mc",
                 "Hits 0-7D", "Hits 8-30D", "Hits 31-60D", "Trend Score", "Acceleration"],
        key="trend_leaders_main",
        rename_map={"name": "Company", "industry": "Industry",
                    "market_cap": "MCap", "first_market_cap": "First MCap", "%_gain_mc": "Gain %"},
        integer_cols=["Hits 0-7D", "Hits 8-30D", "Hits 31-60D", "Trend Score"],
        one_decimal_cols=["%_gain_mc"],
        two_decimal_cols=["Acceleration"],
        major_cols=["market_cap", "first_market_cap"],
        link_col="name",
        height=520,
    )

    st.download_button("Download CSV", filtered.to_csv(index=False), "trend_leaders.csv")

    with st.expander("Market-cap trend for a stock"):
        if not filtered.empty:
            selected = st.selectbox(
                "Select company",
                filtered["name"].tolist(),
                key="tl_mcap_stock",
            )
            if selected:
                hist = get_historical_market_cap()
                stock_hist = hist[hist["name"] == selected]
                if not stock_hist.empty:
                    st.plotly_chart(market_cap_line_chart(stock_hist, selected), use_container_width=True)
                else:
                    st.warning(f"No market-cap history for {selected}.")


@st.cache_data(ttl=CACHE_TTL)
def _fetch_emerging_winners(recent_days: int, min_appearances: int, min_gain_pct: int) -> pd.DataFrame:
    latest_date = get_latest_table_date(TABLE_HIGHS)
    if latest_date is None:
        return pd.DataFrame()

    recent_cutoff = latest_date - datetime.timedelta(days=recent_days - 1)
    with sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES) as conn:
        query = f"""
        SELECT
            name, industry, nse_code, bse_code,
            first_seen_date, first_market_cap,
            COUNT(*) as appearance_count,
            MAX(market_cap) as latest_market_cap
        FROM {TABLE_HIGHS}
        WHERE date BETWEEN ? AND ? AND first_seen_date >= ?
        GROUP BY name, industry, nse_code, bse_code, first_seen_date, first_market_cap
        HAVING appearance_count >= ?
           AND ((latest_market_cap - first_market_cap) * 100.0 / NULLIF(first_market_cap, 0)) >= ?
        ORDER BY ((latest_market_cap - first_market_cap) * 100.0 / NULLIF(first_market_cap, 0)) DESC
        """
        df = pd.read_sql_query(query, conn, params=(recent_cutoff, latest_date, recent_cutoff, min_appearances, min_gain_pct))

    if df.empty:
        return df

    df["Market Cap Gain (%)"] = (
        (df["latest_market_cap"] - df["first_market_cap"]) * 100 / df["first_market_cap"]
    ).round(2)
    return df.rename(columns={
        "name": "Company", "industry": "Industry",
        "first_seen_date": "First Seen", "appearance_count": "Appearances",
        "first_market_cap": "Market Cap Then", "latest_market_cap": "Market Cap Now",
    })


def _render_new_breakouts():
    latest_date = _latest_date()
    if latest_date:
        st.caption(f"Latest data date: {latest_date}")

    recent_days     = st.sidebar.slider("Lookback Window (Days)", 3, 15, 7, key="ew_days")
    min_appearances = st.sidebar.slider("Min Appearances", 1, 5, 2, key="ew_appearances")
    min_gain_pct    = st.sidebar.slider("Min MCap Gain (%)", 0, 50, 5, key="ew_gain")

    df = _fetch_emerging_winners(recent_days, min_appearances, min_gain_pct)
    if df.empty:
        st.info("No emerging winners match the selected filters.")
        return

    render_interactive_table(
        df,
        columns=["Company", "Industry", "First Seen", "Appearances",
                 "Market Cap Then", "Market Cap Now", "Market Cap Gain (%)"],
        key="new_breakouts_main",
        integer_cols=["Appearances"],
        one_decimal_cols=["Market Cap Gain (%)"],
        major_cols=["Market Cap Then", "Market Cap Now"],
        link_col="Company",
        height=460,
        fit_columns=True,
    )


def _render_weekly_shift():
    latest_date = _latest_date()
    if latest_date is None:
        st.warning("No dated highs data available.")
        return

    hist_df = get_historical_market_cap()
    if hist_df.empty:
        st.warning("No historical market cap data available.")
        return

    hist_df["date"] = pd.to_datetime(hist_df["date"])
    this_mon, this_sun = _week_range(latest_date)
    last_mon = this_mon - datetime.timedelta(days=7)
    last_sun = this_sun - datetime.timedelta(days=7)

    st.caption(f"Latest data: {latest_date} | This week: {this_mon} – {this_sun} | Last week: {last_mon} – {last_sun}")

    this_week = _weekly_summary(hist_df, this_mon, this_sun)
    last_week = _weekly_summary(hist_df, last_mon, last_sun)

    merged = pd.merge(this_week, last_week, on="name", how="outer", suffixes=("_this", "_last"))
    merged["hits_delta"] = merged["hits_this"].fillna(0) - merged["hits_last"].fillna(0)
    merged["gain_delta"] = merged["gain_pct_this"].fillna(0) - merged["gain_pct_last"].fillna(0)
    merged["nse_code"]   = merged["nse_code_this"]
    merged["bse_code"]   = merged["bse_code_this"]

    rising = merged[(merged["hits_delta"] > 0) & (merged["gain_delta"] > 0)].sort_values(
        ["hits_delta", "gain_delta"], ascending=[False, False]
    )
    losing = merged[(merged["hits_delta"] < 0) & (merged["gain_delta"] < 0)].sort_values(
        ["hits_delta", "gain_delta"], ascending=[True, True]
    )

    def _render_shift_table(frame, title, key):
        st.markdown(f"### {title} ({len(frame)})")
        render_interactive_table(
            frame,
            columns=["name", "industry_this", "market_cap_end_this",
                     "hits_last", "hits_this", "gain_pct_last", "gain_pct_this",
                     "hits_delta", "gain_delta"],
            key=key,
            rename_map={
                "name": "Company", "industry_this": "Industry",
                "market_cap_end_this": "MCap",
                "hits_last": "Hits LW", "hits_this": "Hits TW",
                "gain_pct_last": "%Gain LW", "gain_pct_this": "%Gain TW",
                "hits_delta": "Delta Hits", "gain_delta": "Delta Gain",
            },
            integer_cols=["hits_last", "hits_this", "hits_delta"],
            one_decimal_cols=["gain_pct_last", "gain_pct_this", "gain_delta"],
            major_cols=["market_cap_end_this"],
            link_col="name",
            height=320,
        )

    _render_shift_table(rising, "Rising Momentum", "weekly_shift_rising")
    _render_shift_table(losing, "Losing Momentum", "weekly_shift_losing")


def _render_persistence():
    df = get_persistence_scores()
    if df.empty:
        st.warning("No persistence data available.")
        return

    min_hits    = st.sidebar.number_input("Min hits (7 days)", min_value=0,
                                          max_value=int(df["hits_7"].max()), value=2, step=1, key="ps_hits")
    score_cutoff = st.sidebar.number_input("Min persistence score", min_value=0.0,
                                           max_value=float(df["persistence_score"].max()), value=20.0,
                                           step=1.0, key="ps_score")

    filtered = df[(df["hits_7"] >= min_hits) & (df["persistence_score"] >= score_cutoff)]
    if filtered.empty:
        st.info("No candidates match the selected filters.")
        return

    render_interactive_table(
        filtered.sort_values("persistence_score", ascending=False),
        columns=["name", "industry", "market_cap", "hits_7", "hits_30", "hits_60", "%_gain_mc", "persistence_score"],
        key="persistence_main",
        rename_map={"market_cap": "MCap (Cr)", "%_gain_mc": "Gain %", "persistence_score": "Persistence Score"},
        integer_cols=["hits_7", "hits_30", "hits_60"],
        one_decimal_cols=["%_gain_mc"],
        two_decimal_cols=["persistence_score"],
        major_cols=["market_cap"],
        link_col="name",
        height=460,
    )

    with st.expander("Weekly frequency timeline for a stock"):
        top_stock = st.selectbox("Select stock", options=filtered["name"].astype("string").tolist(), key="ps_timeline_stock")
        if top_stock:
            timeline = get_frequency_timeline(top_stock)
            if timeline.empty:
                st.warning(f"No timeline data for {top_stock}.")
            else:
                st.plotly_chart(
                    px.bar(timeline, x="week", y="frequency", title=f"Weekly 52W-high frequency: {top_stock}"),
                    use_container_width=True,
                )

    st.caption("Persistence score = 40% (7/30 hit ratio) + 30% (30/60 hit ratio) + 30% (market-cap gain).")


def _render_im_score():
    df = get_im_momentum_scores()
    if df.empty:
        st.warning("No im-momentum data available.")
        return

    emerging = df[df["novelty_score"] >= 18]
    strong   = df[(df["novelty_score"] >= 15) & (df["novelty_score"] < 18)]
    moderate = df[(df["novelty_score"] >= 12) & (df["novelty_score"] < 15)]
    noise    = df[df["novelty_score"] < 12]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("EMERGING (18-20)", len(emerging), help="First-time or rare breakouts — investigate these")
    c2.metric("STRONG (15-17)",   len(strong),   help="High priority")
    c3.metric("MODERATE (12-14)", len(moderate), help="Watch list")
    c4.metric("NOISE (<12)",      len(noise),    help="Already known / saturated")

    st.caption(
        "Novelty (0–20): rewards rare/fresh 52W-high appearances over the past 12 months. "
        "Momentum (0–10): market-cap gain since first appearance. "
        "Composite = Novelty × 0.4 + Momentum × 0.6"
    )

    tier_filter = st.sidebar.selectbox(
        "MCap tier filter",
        ["All", "SMALL", "MID", "LARGE", "MEGA"],
        key="im_tier",
    )
    min_composite = st.sidebar.slider("Min composite score", 0.0, 14.0, 6.0, step=0.5, key="im_min_score")

    filtered = df[df["im_composite"] >= min_composite]
    if tier_filter != "All" and "market_cap_tier" in filtered.columns:
        filtered = filtered[filtered["market_cap_tier"] == tier_filter]

    render_interactive_table(
        filtered,
        columns=["name", "industry", "hits_1y", "days_since_last_high",
                 "novelty_score", "momentum_score", "im_composite", "%_gain_mc"],
        key="im_score_main",
        rename_map={
            "name": "Company",
            "industry": "Industry",
            "hits_1y": "Hits 1Y",
            "days_since_last_high": "Days Since High",
            "novelty_score": "Novelty",
            "momentum_score": "Momentum",
            "im_composite": "IM Score",
            "%_gain_mc": "Gain %",
        },
        integer_cols=["hits_1y", "days_since_last_high", "novelty_score", "momentum_score"],
        two_decimal_cols=["im_composite"],
        one_decimal_cols=["%_gain_mc"],
        link_col="name",
        height=520,
    )

    st.download_button("Download CSV", filtered.to_csv(index=False), "im_scores.csv")

    with st.expander("Scoring methodology"):
        st.markdown("""
**Novelty (0–20) — Research asymmetry**

| Breakouts in 12 months | Score |
|---|---|
| 1 (first time) | 10 — EMERGING |
| 2–3 | 7 |
| 4–5 | 4 |
| 6+ | 1 — saturated |

Fresh breakout bonus (≤3 days since last high): +2 pts

**Momentum (0–10)** — derived from market-cap gain since first appearance in highs table.

**Composite = Novelty × 0.4 + Momentum × 0.6**
        """)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    st.title("Momentum Rankings")
    st.markdown("Five lenses on the same question: which stocks have momentum right now?")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Trend Leaders", "New Breakouts", "Weekly Shift", "Persistence", "IM Score"]
    )

    with tab1:
        st.subheader("Trend Leaders")
        st.caption("Stocks with the most consistent recent 52W-high hits, weighted towards the last 7 days.")
        _render_trend_leaders()

    with tab2:
        st.subheader("New Breakouts")
        st.caption("Stocks that only recently started hitting 52-week highs and are gaining momentum.")
        _render_new_breakouts()

    with tab3:
        st.subheader("Weekly Shift")
        st.caption("Week-over-week momentum changes — who is accelerating and who is fading.")
        _render_weekly_shift()

    with tab4:
        st.subheader("Persistence")
        st.caption("Stocks that keep reappearing over long lookback windows — multi-bagger candidates.")
        _render_persistence()

    with tab5:
        st.subheader("IM Score")
        st.caption("Novelty-scored breakouts — surfaces stocks before they become crowded trades.")
        _render_im_score()


if __name__ == "__main__":
    main()

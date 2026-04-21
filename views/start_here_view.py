import pandas as pd
import streamlit as st

from config import TABLE_HIGHS
from db_utils import (
    compute_industry_tailwind_stats,
    get_data_for_date,
    get_downfromhigh_data_for_date,
    get_downfromhigh_dates,
    get_fivetofiftyclub_data_for_date,
    get_fivetofiftyclub_dates,
    get_latest_table_date,
    get_momentum_summary,
    get_persistence_scores,
    get_tailwind_stocks,
    get_weekly_report_snapshot,
)
from grid_utils import render_interactive_table
from mcap_tier_utils import add_mcap_tier_col, apply_mcap_tier_filter, get_global_mcap_focus


def _render_table(df: pd.DataFrame, columns: list[str], rename_map: dict[str, str]) -> None:
    render_interactive_table(
        df,
        columns=columns,
        key=f"start_here_{'_'.join(columns)}",
        rename_map=rename_map,
        integer_cols=[
            "hits_7",
            "hits_30",
            "hits_60",
            "hits_this",
            "hits_last",
            "hits_delta",
            "Momentum Stocks",
            "Trend Score",
            "Hits 0-7D",
            "Hits 8-30D",
            "Hits 31-60D",
        ],
        one_decimal_cols=["%_gain_mc", "gain_pct_this", "gain_delta"],
        two_decimal_cols=["persistence_score", "Acceleration", "Weighted Gain %", "Avg Hits"],
        major_cols=["market_cap", "first_market_cap", "market_cap_cr"],
        link_col="name" if "name" in columns else None,
        height=260,
        fit_columns=True,
    )

def _get_trend_shift_snapshot(limit: int = 8) -> pd.DataFrame:
    snapshot = get_weekly_report_snapshot()
    if not snapshot:
        return pd.DataFrame()

    comparison = snapshot.get("comparison", pd.DataFrame())
    if comparison.empty:
        return pd.DataFrame()

    rising = comparison[comparison["status"] == "Rising"].copy()
    rising = rising.sort_values(["hits_delta", "gain_delta"], ascending=[False, False]).head(limit)
    if rising.empty:
        return rising

    return rising


def main() -> None:
    st.title("Start Here")
    st.markdown("A quick investor dashboard for where to look first and why.")
    st.caption("The app-wide MCap Focus in the sidebar shapes the company-level signal tables on this page.")

    latest_highs_date = get_latest_table_date(TABLE_HIGHS)
    if latest_highs_date is None:
        st.warning("No highs data available.")
        return

    highs_df = get_data_for_date(latest_highs_date)

    fivetofifty_dates = get_fivetofiftyclub_dates()
    latest_fivetofifty_date = pd.to_datetime(fivetofifty_dates[-1]).date() if fivetofifty_dates else None
    fivetofifty_df = (
        get_fivetofiftyclub_data_for_date(str(latest_fivetofifty_date))
        if latest_fivetofifty_date is not None
        else pd.DataFrame()
    )

    down_dates = get_downfromhigh_dates()
    latest_down_date = pd.to_datetime(down_dates[-1]).date() if down_dates else None
    down_df = (
        get_downfromhigh_data_for_date(str(latest_down_date))
        if latest_down_date is not None
        else pd.DataFrame()
    )

    momentum_df = get_momentum_summary()
    persistence_df = get_persistence_scores()
    top_trend_df = pd.DataFrame()
    top_industry_df = pd.DataFrame()

    if not momentum_df.empty:
        top_trend_df = momentum_df.copy()
        top_trend_df["hits_7"] = top_trend_df["hits_7"].fillna(0).astype(int)
        top_trend_df["hits_30"] = top_trend_df["hits_30"].fillna(0).astype(int)
        top_trend_df["hits_60"] = top_trend_df["hits_60"].fillna(0).astype(int)
        top_trend_df["Hits 0-7D"] = top_trend_df["hits_7"]
        top_trend_df["Hits 8-30D"] = (top_trend_df["hits_30"] - top_trend_df["hits_7"]).clip(lower=0)
        top_trend_df["Hits 31-60D"] = (top_trend_df["hits_60"] - top_trend_df["hits_30"]).clip(lower=0)
        top_trend_df["Trend Score"] = (
            top_trend_df["Hits 0-7D"] * 3
            + top_trend_df["Hits 8-30D"] * 2
            + top_trend_df["Hits 31-60D"]
        )
        top_trend_df["Acceleration"] = (
            (top_trend_df["Hits 0-7D"] / 7.0) - (top_trend_df["Hits 8-30D"] / 23.0)
        ).round(3)
        top_trend_df = top_trend_df[top_trend_df["hits_7"] > 0]
        top_trend_df = top_trend_df.sort_values(
            ["Trend Score", "Acceleration", "%_gain_mc"],
            ascending=[False, False, False],
        ).head(10)
        tailwind_df = get_tailwind_stocks(60, 5)
        top_industry_df = compute_industry_tailwind_stats(tailwind_df) if not tailwind_df.empty else pd.DataFrame()
        if not top_industry_df.empty:
            top_industry_df = top_industry_df.rename(
                columns={
                    "count_stocks": "Momentum Stocks",
                    "avg_hits": "Avg Hits",
                    "weighted_gain_mc": "Weighted Gain %",
                }
            ).sort_values(["Momentum Stocks", "Weighted Gain %"], ascending=[False, False]).head(8)

    top_shift_df = _get_trend_shift_snapshot()
    top_persistence_df = persistence_df.head(8) if not persistence_df.empty else pd.DataFrame()

    # MCap tier filter — applies to company-level signal tables
    selected_tiers = get_global_mcap_focus()
    if not top_trend_df.empty:
        top_trend_df = apply_mcap_tier_filter(
            add_mcap_tier_col(top_trend_df, col="market_cap"), selected_tiers
        )
    if not top_shift_df.empty:
        top_shift_df = apply_mcap_tier_filter(
            add_mcap_tier_col(top_shift_df, col="market_cap"), selected_tiers
        )
    if not top_persistence_df.empty:
        top_persistence_df = apply_mcap_tier_filter(
            add_mcap_tier_col(top_persistence_df, col="market_cap"), selected_tiers
        )

    st.caption(f"Latest highs data date: {latest_highs_date}")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Near 52W High", len(highs_df))
    col2.metric("5-50% Below High", len(fivetofifty_df))
    col3.metric("50%+ Below High", len(down_df))
    col4.metric("Active Industries", momentum_df["industry"].nunique() if not momentum_df.empty else 0)

    st.markdown("---")
    st.subheader("Suggested investor flow")
    st.markdown(
        """
        1. Start with **Weekly Report** for the shortest read on breadth, fresh names, sector leadership, and risk.
        2. Go to **Momentum Rankings -> Trend Leaders** to see the strongest persistent names.
        3. Check **Momentum Rankings -> Weekly Shift** to catch acceleration or weakening momentum.
        4. Use **Industry Tailwinds** to confirm whether the sector is helping the stock.
        5. Use **Price Position** when you want to screen names by distance from their 52W high.
        """
    )

    tab1, tab2 = st.tabs(["Top Signals", "Context"])

    with tab1:
        st.markdown("### Best Current Momentum")
        st.caption("Highest-conviction names right now. Full-width layout makes the score, acceleration, and hit columns readable.")
        _render_table(
            top_trend_df,
            ["name", "industry", "Trend Score", "Acceleration", "hits_7", "%_gain_mc"],
            {
                "name": "Company",
                "industry": "Industry",
                "hits_7": "Hits 7D",
                "%_gain_mc": "Gain %",
            },
        )

        st.markdown("### Rising This Week")
        st.caption("Weekly movers with improving hit count and market-cap trend.")
        _render_table(
            top_shift_df,
            ["name", "industry", "hits_this", "hits_delta", "gain_pct_this", "gain_delta"],
            {
                "name": "Company",
                "industry": "Industry",
                "hits_this": "Hits TW",
                "hits_delta": "Delta Hits",
                "gain_pct_this": "Gain TW %",
                "gain_delta": "Delta Gain",
            },
        )

    with tab2:
        st.markdown("### Sector Tailwinds")
        st.caption("Industries with multiple active names. This stays full width so averages and weighted gain remain visible.")
        _render_table(
            top_industry_df,
            ["industry", "Momentum Stocks", "Avg Hits", "Weighted Gain %"],
            {},
        )

        st.markdown("### Persistent Leaders")
        st.caption("Stocks that keep reappearing over the lookback windows.")
        _render_table(
            top_persistence_df,
            ["name", "industry", "hits_7", "hits_30", "persistence_score", "%_gain_mc"],
            {
                "name": "Company",
                "industry": "Industry",
                "hits_7": "Hits 7D",
                "hits_30": "Hits 30D",
                "persistence_score": "Persistence",
                "%_gain_mc": "Gain %",
            },
        )


if __name__ == "__main__":
    main()

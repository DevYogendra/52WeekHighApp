import datetime

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
    get_historical_market_cap,
    get_latest_table_date,
    get_momentum_summary,
    get_persistence_scores,
)
from grid_utils import render_interactive_table


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
        two_decimal_cols=["persistence_score", "Acceleration", "Weighted Gain %", "Avg Hits 7D"],
        major_cols=["market_cap", "first_market_cap", "market_cap_cr"],
        link_col="name" if "name" in columns else None,
        height=260,
        fit_columns=True,
    )


def _get_week_range(date: datetime.date) -> tuple[datetime.date, datetime.date]:
    weekday = date.weekday()
    monday = date - datetime.timedelta(days=weekday)
    sunday = monday + datetime.timedelta(days=6)
    return monday, sunday


def _compute_weekly_summary(df: pd.DataFrame, start_date: datetime.date, end_date: datetime.date) -> pd.DataFrame:
    mask = (df["date"] >= pd.to_datetime(start_date)) & (df["date"] <= pd.to_datetime(end_date))
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


def _get_trend_shift_snapshot(limit: int = 8) -> pd.DataFrame:
    latest_data_date = get_latest_table_date(TABLE_HIGHS)
    if latest_data_date is None:
        return pd.DataFrame()

    hist_df = get_historical_market_cap()
    if hist_df.empty:
        return pd.DataFrame()

    hist_df["date"] = pd.to_datetime(hist_df["date"])
    this_mon, this_sun = _get_week_range(latest_data_date)
    last_mon = this_mon - datetime.timedelta(days=7)
    last_sun = this_sun - datetime.timedelta(days=7)

    this_week = _compute_weekly_summary(hist_df, this_mon, this_sun)
    last_week = _compute_weekly_summary(hist_df, last_mon, last_sun)
    if this_week.empty:
        return pd.DataFrame()

    merged = pd.merge(
        this_week,
        last_week,
        on="name",
        how="outer",
        suffixes=("_this", "_last"),
    )
    merged["hits_delta"] = merged["hits_this"].fillna(0) - merged["hits_last"].fillna(0)
    merged["gain_delta"] = merged["gain_pct_this"].fillna(0) - merged["gain_pct_last"].fillna(0)
    merged["nse_code"] = merged["nse_code_this"]
    merged["bse_code"] = merged["bse_code_this"]

    rising = merged[(merged["hits_delta"] > 0) & (merged["gain_delta"] > 0)].copy()
    rising = rising.sort_values(["hits_delta", "gain_delta"], ascending=[False, False]).head(limit)
    if rising.empty:
        return rising

    rising = rising.rename(columns={"industry_this": "industry"})
    return rising


def main() -> None:
    st.title("Start Here")
    st.markdown("A quick investor dashboard for where to look first and why.")

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
        top_industry_df = compute_industry_tailwind_stats(momentum_df[momentum_df["hits_7"] >= 2].copy())
        if not top_industry_df.empty:
            top_industry_df = top_industry_df.rename(
                columns={
                    "count_stocks": "Momentum Stocks",
                    "avg_hits_7": "Avg Hits 7D",
                    "weighted_gain_mc": "Weighted Gain %",
                }
            ).sort_values(["Momentum Stocks", "Weighted Gain %"], ascending=[False, False]).head(8)

    top_shift_df = _get_trend_shift_snapshot()
    top_persistence_df = persistence_df.head(8) if not persistence_df.empty else pd.DataFrame()

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
        1. Start with `Trend Analyzer` to see the strongest persistent names.
        2. Check `Trend Shift Analyzer` to catch acceleration or weakening momentum.
        3. Use `Industry Tailwinds` to confirm whether the sector is helping the stock.
        4. Use the bucket views only after that, when you want more names to inspect.
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
            ["industry", "Momentum Stocks", "Avg Hits 7D", "Weighted Gain %"],
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

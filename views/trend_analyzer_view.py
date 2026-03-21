# views/trend_analyzer_view.py

import pandas as pd
import streamlit as st

from config import TABLE_HIGHS
from db_utils import get_momentum_summary, get_latest_table_date
from grid_utils import render_interactive_table


def main():
    st.title("📈 Trend Analyzer")
    st.markdown("Identify consistent performers using non-overlapping recent hit buckets.")

    df = get_momentum_summary()
    if df.empty:
        st.warning("No momentum data available.")
        return

    latest_data_date = get_latest_table_date(TABLE_HIGHS)
    if latest_data_date is not None:
        st.caption(f"Latest data date: {latest_data_date}")

    df["hits_7"] = df["hits_7"].fillna(0).astype(int)
    df["hits_30"] = df["hits_30"].fillna(0).astype(int)
    df["hits_60"] = df["hits_60"].fillna(0).astype(int)

    df["Hits 0-7D"] = df["hits_7"]
    df["Hits 8-30D"] = (df["hits_30"] - df["hits_7"]).clip(lower=0)
    df["Hits 31-60D"] = (df["hits_60"] - df["hits_30"]).clip(lower=0)

    df["Trend Score"] = df["Hits 0-7D"] * 3 + df["Hits 8-30D"] * 2 + df["Hits 31-60D"]
    df["Acceleration"] = (
        (df["Hits 0-7D"] / 7.0) - (df["Hits 8-30D"] / 23.0)
    ).round(3)

    df = df[df["hits_7"] > 0].sort_values(by=["Trend Score", "Acceleration", "%_gain_mc"], ascending=[False, False, False])

    st.caption("Trend Score = 3×Hits 0-7D + 2×Hits 8-30D + 1×Hits 31-60D. Acceleration compares recent daily hit rate vs the prior 23 days.")

    render_interactive_table(
        df,
        columns=[
            "name",
            "industry",
            "market_cap",
            "first_market_cap",
            "%_gain_mc",
            "Hits 0-7D",
            "Hits 8-30D",
            "Hits 31-60D",
            "Trend Score",
            "Acceleration",
        ],
        key="trend_analyzer_main",
        rename_map={
            "name": "Company",
            "industry": "Industry",
            "market_cap": "MCap",
            "first_market_cap": "First MCap",
            "%_gain_mc": "Gain %",
        },
        integer_cols=["Hits 0-7D", "Hits 8-30D", "Hits 31-60D", "Trend Score"],
        one_decimal_cols=["%_gain_mc"],
        two_decimal_cols=["Acceleration"],
        major_cols=["market_cap", "first_market_cap"],
        link_col="name",
        height=520,
    )


if __name__ == "__main__":
    main()

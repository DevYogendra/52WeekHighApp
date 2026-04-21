import html

import pandas as pd
import streamlit as st

from db_utils import (
    compute_industry_tailwind_stats,
    get_momentum_summary,
    get_weekly_report_snapshot,
)
from grid_utils import render_interactive_table
from mcap_tier_utils import (
    FOCUS_TIER_LABELS,
    add_mcap_tier_col,
    apply_mcap_tier_filter,
    get_global_mcap_focus,
)


REPORT_TIER_ORDER = FOCUS_TIER_LABELS


def _format_period(start_date, last_data_date, trading_days: int) -> str:
    start_label = pd.to_datetime(start_date).strftime("%Y-%m-%d")
    end_label = pd.to_datetime(last_data_date).strftime("%Y-%m-%d")
    day_label = "day" if trading_days == 1 else "days"
    return f"{start_label} to {end_label} ({trading_days} trading {day_label} in data)"


def _format_pct(value) -> str:
    if pd.isna(value):
        return "-"
    return f"{float(value):.1f}%"


def _ordered_tiers(selected_tiers: list[str]) -> list[str]:
    if not selected_tiers:
        return REPORT_TIER_ORDER
    return [tier for tier in REPORT_TIER_ORDER if tier in selected_tiers]


def _plain_tier_name(label: str) -> str:
    return label.split(" ", 1)[1] if " " in label else label


def _top_per_tier(
    frame: pd.DataFrame,
    selected_tiers: list[str],
    limit: int,
    tier_col: str = "mcap_tier",
) -> dict[str, pd.DataFrame]:
    ordered = _ordered_tiers(selected_tiers)
    if frame.empty or tier_col not in frame.columns:
        return {tier: pd.DataFrame() for tier in ordered}
    return {
        tier: frame[frame[tier_col] == tier].head(limit).reset_index(drop=True)
        for tier in ordered
    }


def _trend_leaders(selected_tiers: list[str], limit: int | None = None) -> pd.DataFrame:
    df = get_momentum_summary()
    if df.empty:
        return df

    df = df.copy()
    df["hits_7"] = df["hits_7"].fillna(0).astype(int)
    df["hits_30"] = df["hits_30"].fillna(0).astype(int)
    df["hits_60"] = df["hits_60"].fillna(0).astype(int)
    df["Hits 0-7D"] = df["hits_7"]
    df["Hits 8-30D"] = (df["hits_30"] - df["hits_7"]).clip(lower=0)
    df["Hits 31-60D"] = (df["hits_60"] - df["hits_30"]).clip(lower=0)
    df["Trend Score"] = (
        df["Hits 0-7D"] * 3
        + df["Hits 8-30D"] * 2
        + df["Hits 31-60D"]
    )
    df["Acceleration"] = (
        (df["Hits 0-7D"] / 7.0) - (df["Hits 8-30D"] / 23.0)
    ).round(3)
    df = df[df["hits_7"] > 0]
    df = apply_mcap_tier_filter(add_mcap_tier_col(df, col="market_cap"), selected_tiers)
    ranked = df.sort_values(
        ["Trend Score", "Acceleration", "%_gain_mc"],
        ascending=[False, False, False],
    )
    if limit is not None:
        return ranked.head(limit)
    return ranked


def _weekly_industry_comparison(this_week: pd.DataFrame, last_week: pd.DataFrame) -> pd.DataFrame:
    def _to_industry(frame: pd.DataFrame) -> pd.DataFrame:
        if frame.empty:
            return pd.DataFrame()
        working = frame.rename(
            columns={
                "hits": "hits_in_window",
                "gain_pct": "%_gain_mc",
                "market_cap_end": "market_cap",
            }
        )
        return compute_industry_tailwind_stats(working, hits_col="hits_in_window")

    current = _to_industry(this_week)
    previous = _to_industry(last_week)
    merged = pd.merge(
        current,
        previous,
        on="industry",
        how="outer",
        suffixes=("_this", "_last"),
    )
    if merged.empty:
        return merged

    for col in [
        "count_stocks_this",
        "count_stocks_last",
        "total_hits_this",
        "total_hits_last",
        "avg_hits_this",
        "avg_hits_last",
        "weighted_gain_mc_this",
        "weighted_gain_mc_last",
    ]:
        if col in merged.columns:
            merged[col] = pd.to_numeric(merged[col], errors="coerce")
    merged["stocks_delta"] = (
        merged["count_stocks_this"].fillna(0) - merged["count_stocks_last"].fillna(0)
    )
    merged["weighted_gain_delta"] = (
        merged["weighted_gain_mc_this"].fillna(0) - merged["weighted_gain_mc_last"].fillna(0)
    )
    return merged.sort_values(
        ["count_stocks_this", "weighted_gain_mc_this"],
        ascending=[False, False],
    ).reset_index(drop=True)


def _build_takeaways(
    meta: dict[str, object],
    this_week: pd.DataFrame,
    last_week: pd.DataFrame,
    leaders: pd.DataFrame,
    rising: pd.DataFrame,
    fresh: pd.DataFrame,
    industries: pd.DataFrame,
    falling: pd.DataFrame,
    dropped: pd.DataFrame,
) -> list[str]:
    breadth_delta = len(this_week) - len(last_week)
    if breadth_delta > 0:
        breadth_text = f"Breadth expanded to {len(this_week)} names from {len(last_week)} last week ({breadth_delta:+d})."
    elif breadth_delta < 0:
        breadth_text = f"Breadth contracted to {len(this_week)} names from {len(last_week)} last week ({breadth_delta:+d})."
    else:
        breadth_text = f"Breadth was unchanged at {len(this_week)} names versus the prior week."

    freshness_text = (
        f"{len(fresh)} fresh names entered the report week and {len(dropped)} dropped out."
    )

    if not leaders.empty:
        leader = leaders.iloc[0]
        leadership_text = (
            f"Top trend leader: {leader['name']} in {leader['industry']} "
            f"(Trend Score {int(leader['Trend Score'])}, Hits 7D {int(leader['hits_7'])}, "
            f"gain {_format_pct(leader['%_gain_mc'])})."
        )
    else:
        leadership_text = "No trend leaders met the current filters."

    if not industries.empty:
        sector = industries.iloc[0]
        sector_text = (
            f"Sector leadership is strongest in {sector['industry']} "
            f"with {int(sector['count_stocks_this'])} active names and "
            f"weighted weekly gain {_format_pct(sector['weighted_gain_mc_this'])}."
        )
    else:
        sector_text = "No industry cluster stood out in the selected scope."

    if not falling.empty:
        laggard = falling.iloc[0]
        risk_text = (
            f"Main fade to watch: {laggard['name']} ({laggard['industry']}) "
            f"with Delta Hits {int(laggard['hits_delta'])} and Delta Gain {_format_pct(laggard['gain_delta'])}."
        )
    elif not dropped.empty:
        risk_text = f"{len(dropped)} names disappeared from the high list versus the prior week."
    else:
        risk_text = "No clear fade pocket showed up in the week-over-week comparison."

    lines = [breadth_text, freshness_text, leadership_text, sector_text, risk_text]
    if meta.get("skipped_partial_week"):
        lines.append(
            "The latest data week was partial, so the report uses the last completed week for cleaner comparisons."
        )
    return lines


def _build_tiered_lines(
    tier_frames: dict[str, pd.DataFrame],
    formatter,
) -> dict[str, list[str]]:
    lines_by_tier: dict[str, list[str]] = {}
    for tier, frame in tier_frames.items():
        if frame.empty:
            lines_by_tier[tier] = []
            continue
        lines_by_tier[tier] = [formatter(row) for _, row in frame.iterrows()]
    return lines_by_tier


def _build_html_report(
    meta: dict[str, object],
    takeaways: list[str],
    leaders_by_tier: dict[str, pd.DataFrame],
    rising_by_tier: dict[str, pd.DataFrame],
    fresh_by_tier: dict[str, pd.DataFrame],
    industries: pd.DataFrame,
    falling_by_tier: dict[str, pd.DataFrame],
    dropped_by_tier: dict[str, pd.DataFrame],
) -> str:
    report_period = _format_period(
        meta["report_week_start"],
        meta["report_week_last_data_date"],
        meta["report_trading_days"],
    )
    compare_period = _format_period(
        meta["compare_week_start"],
        meta["compare_week_last_data_date"],
        meta["compare_trading_days"],
    )

    metadata_items = [
        f"Report week: {report_period}",
        f"Prior week: {compare_period}",
        f"Latest highs data date: {meta['latest_data_date']}",
    ]
    if meta.get("skipped_partial_week"):
        metadata_items.append(
            f"Skipped partial week starting {meta['skipped_week_start']} "
            f"(latest data in that week: {meta['skipped_week_last_data_date']})"
        )

    def _list_html(items: list[str]) -> str:
        if not items:
            return "<p>None</p>"
        li = "".join(f"<li>{html.escape(item)}</li>" for item in items)
        return f"<ul>{li}</ul>"

    def _section_html(title: str, items: list[str]) -> str:
        body = _list_html(items)
        return f"<section><h2>{html.escape(title)}</h2>{body}</section>"

    def _tiered_section_html(title: str, tier_frames: dict[str, pd.DataFrame], formatter) -> str:
        subsections = []
        for tier, lines in _build_tiered_lines(tier_frames, formatter).items():
            subsections.append(
                f"<div class=\"tier-block\"><h3>{html.escape(_plain_tier_name(tier))}</h3>{_list_html(lines)}</div>"
            )
        body = "".join(subsections) if subsections else "<p>None</p>"
        return f"<section><h2>{html.escape(title)}</h2>{body}</section>"

    sections = [
        _tiered_section_html(
            "Trend Leaders By Tier",
            leaders_by_tier,
            lambda row: (
                f"{row['name']} ({row['industry']}): Trend Score {int(row['Trend Score'])}, "
                f"Hits 7D {int(row['hits_7'])}, gain {_format_pct(row['%_gain_mc'])}"
            ),
        ),
        _tiered_section_html(
            "Rising Momentum By Tier",
            rising_by_tier,
            lambda row: (
                f"{row['name']} ({row['industry']}): Hits TW {int(row['hits_this'])}, "
                f"Delta Hits {int(row['hits_delta'])}, Delta Gain {_format_pct(row['gain_delta'])}"
            ),
        ),
        _tiered_section_html(
            "Fresh This Week By Tier",
            fresh_by_tier,
            lambda row: (
                f"{row['name']} ({row['industry']}): Hits TW {int(row['hits_this'])}, "
                f"weekly gain {_format_pct(row['gain_pct_this'])}"
            ),
        ),
        _section_html(
            "Industry Leadership",
            [
                (
                f"{row['industry']}: Stocks {int(row['count_stocks_this'])}, "
                f"Delta Stocks {int(row['stocks_delta'])}, "
                f"Weighted Gain {_format_pct(row['weighted_gain_mc_this'])}"
                )
                for _, row in industries.head(5).iterrows()
            ],
        ),
        _tiered_section_html(
            "Risk Watch By Tier",
            falling_by_tier,
            lambda row: (
                f"{row['name']} ({row['industry']}): Delta Hits {int(row['hits_delta'])}, "
                f"Delta Gain {_format_pct(row['gain_delta'])}"
            ),
        ),
        _tiered_section_html(
            "Dropped From The List By Tier",
            dropped_by_tier,
            lambda row: (
                f"{row['name']} ({row['industry']}): Hits LW {int(row['hits_last'])}, "
                f"prior-week gain {_format_pct(row['gain_pct_last'])}"
            ),
        ),
    ]

    metadata_html = _list_html(metadata_items)
    takeaways_html = _list_html(takeaways)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>52WeekHighApp Weekly Report</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f3eb;
      --panel: #fffdf8;
      --ink: #1f2937;
      --muted: #5b6472;
      --accent: #0f766e;
      --border: #d8d2c4;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: linear-gradient(180deg, #efe7d7 0%, var(--bg) 220px);
      color: var(--ink);
      font-family: Georgia, "Times New Roman", serif;
      line-height: 1.55;
    }}
    main {{
      max-width: 920px;
      margin: 0 auto;
      padding: 40px 20px 56px;
    }}
    header, section {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 22px 24px;
      box-shadow: 0 10px 30px rgba(31, 41, 55, 0.06);
    }}
    header {{ margin-bottom: 18px; }}
    section {{ margin-top: 18px; }}
    h1, h2 {{
      margin: 0 0 12px;
      line-height: 1.2;
    }}
    h3 {{
      margin: 0 0 10px;
      font-size: 1rem;
      color: #374151;
    }}
    h1 {{
      font-size: 2rem;
      color: #111827;
    }}
    h2 {{
      font-size: 1.2rem;
      color: var(--accent);
    }}
    p, li {{
      font-size: 1rem;
    }}
    .lede {{
      margin: 10px 0 0;
      color: var(--muted);
    }}
    ul {{
      margin: 0;
      padding-left: 1.2rem;
    }}
    li + li {{
      margin-top: 6px;
    }}
    .tier-block + .tier-block {{
      margin-top: 18px;
      padding-top: 18px;
      border-top: 1px solid var(--border);
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>52WeekHighApp Weekly Report</h1>
      <p class="lede">A concise week-over-week market summary generated from the app's completed-week data.</p>
      {metadata_html}
    </header>
    <section>
      <h2>Key Takeaways</h2>
      {takeaways_html}
    </section>
    {''.join(sections)}
  </main>
</body>
</html>
"""

def _render_company_table(
    title: str,
    frame: pd.DataFrame,
    columns: list[str],
    key: str,
    rename_map: dict[str, str],
    integer_cols: list[str],
    one_decimal_cols: list[str],
    major_cols: list[str] | None = None,
) -> None:
    st.markdown(f"### {title}")
    render_interactive_table(
        frame,
        columns=columns,
        key=key,
        rename_map=rename_map,
        integer_cols=integer_cols,
        one_decimal_cols=one_decimal_cols,
        major_cols=major_cols or [],
        link_col="name",
        height=260,
        fit_columns=True,
    )


def main() -> None:
    st.title("Weekly Report")
    st.markdown("A concise week-over-week summary so you can see the market story without reading every table.")

    snapshot = get_weekly_report_snapshot()
    if not snapshot:
        st.warning("Not enough weekly data is available to build the report yet.")
        return

    selected_tiers = get_global_mcap_focus()
    rows_per_tier = 5
    st.caption("The app-wide MCap Focus in the sidebar sets which tiers appear in this report.")

    meta = snapshot["meta"]
    this_week = apply_mcap_tier_filter(
        add_mcap_tier_col(snapshot["this_week"], col="market_cap_end"),
        selected_tiers,
    )
    last_week = apply_mcap_tier_filter(
        add_mcap_tier_col(snapshot["last_week"], col="market_cap_end"),
        selected_tiers,
    )
    comparison = apply_mcap_tier_filter(
        add_mcap_tier_col(snapshot["comparison"], col="market_cap"),
        selected_tiers,
    )
    leaders = _trend_leaders(selected_tiers)
    industries = _weekly_industry_comparison(this_week, last_week)
    if not industries.empty:
        industries = industries[industries["count_stocks_this"].fillna(0) > 0]
    industries = industries.head(rows_per_tier)

    fresh = comparison[comparison["status"] == "New"].copy()
    fresh = fresh.sort_values(["hits_this", "gain_pct_this"], ascending=[False, False])

    rising = comparison[comparison["status"] == "Rising"].copy()
    rising = rising.sort_values(["hits_delta", "gain_delta"], ascending=[False, False])

    falling = comparison[comparison["status"] == "Falling"].copy()
    falling = falling.sort_values(["hits_delta", "gain_delta"], ascending=[True, True])

    dropped = comparison[comparison["status"] == "Dropped"].copy()
    dropped = dropped.sort_values(["hits_last", "gain_pct_last"], ascending=[False, False])

    leaders_by_tier = _top_per_tier(leaders, selected_tiers, rows_per_tier)
    fresh_by_tier = _top_per_tier(fresh, selected_tiers, rows_per_tier)
    rising_by_tier = _top_per_tier(rising, selected_tiers, rows_per_tier)
    falling_by_tier = _top_per_tier(falling, selected_tiers, rows_per_tier)
    dropped_by_tier = _top_per_tier(dropped, selected_tiers, rows_per_tier)

    report_period = _format_period(
        meta["report_week_start"],
        meta["report_week_last_data_date"],
        meta["report_trading_days"],
    )
    compare_period = _format_period(
        meta["compare_week_start"],
        meta["compare_week_last_data_date"],
        meta["compare_trading_days"],
    )

    if meta.get("skipped_partial_week"):
        st.info(
            f"Latest highs data is {meta['latest_data_date']}. "
            f"The week starting {meta['skipped_week_start']} is still partial, "
            f"so this report uses the last completed week instead."
        )

    st.caption(f"Report week: {report_period} | Prior week: {compare_period}")

    breadth_delta = len(this_week) - len(last_week)
    active_industries_this = int(this_week["industry"].nunique()) if not this_week.empty else 0
    active_industries_last = int(last_week["industry"].nunique()) if not last_week.empty else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("52W High Breadth", len(this_week), delta=f"{breadth_delta:+d} vs prior")
    col2.metric("Active Industries", active_industries_this, delta=f"{active_industries_this - active_industries_last:+d}")
    col3.metric("Fresh Names", len(fresh))
    col4.metric("Dropped Names", len(dropped))

    takeaways = _build_takeaways(
        meta,
        this_week,
        last_week,
        leaders,
        rising,
        fresh,
        industries,
        falling,
        dropped,
    )

    html_report = _build_html_report(
        meta,
        takeaways,
        leaders_by_tier,
        rising_by_tier,
        fresh_by_tier,
        industries,
        falling_by_tier,
        dropped_by_tier,
    )

    download_col1, download_col2 = st.columns(2)
    download_col1.download_button(
        "Download Weekly Report (.html)",
        data=html_report,
        file_name=f"weekly_report_{meta['report_week_last_data_date']}.html",
        mime="text/html",
    )
    download_col2.download_button(
        "Download Weekly Comparison (.csv)",
        data=comparison.to_csv(index=False),
        file_name=f"weekly_comparison_{meta['report_week_last_data_date']}.csv",
        mime="text/csv",
    )

    st.subheader("Key Takeaways")
    st.markdown("\n".join([f"- {line}" for line in takeaways]))

    st.markdown("### Industry Leadership")
    render_interactive_table(
        industries,
        columns=["industry", "count_stocks_this", "stocks_delta", "avg_hits_this", "weighted_gain_mc_this"],
        key="weekly_report_industries",
        rename_map={
            "industry": "Industry",
            "count_stocks_this": "Stocks",
            "stocks_delta": "Delta Stocks",
            "avg_hits_this": "Avg Hits",
            "weighted_gain_mc_this": "Weighted Gain %",
        },
        integer_cols=["count_stocks_this", "stocks_delta"],
        one_decimal_cols=["weighted_gain_mc_this"],
        two_decimal_cols=["avg_hits_this"],
        height=240,
    )

    st.subheader("Tier Navigator")
    st.caption("Choose a tier once below. All stock sections update together, with Mega shown first.")

    ordered_tiers = _ordered_tiers(selected_tiers)
    if not ordered_tiers:
        st.info("Select at least one market-cap tier to view the stock sections.")
        return

    tier_tabs = st.tabs([_plain_tier_name(tier) for tier in ordered_tiers])
    for tab, tier in zip(tier_tabs, ordered_tiers):
        tier_slug = _plain_tier_name(tier).lower()
        with tab:
            st.caption(f"Showing up to {rows_per_tier} names for {_plain_tier_name(tier)} cap.")

            _render_company_table(
                "Trend Leaders",
                leaders_by_tier[tier],
                ["name", "industry", "mcap_tier", "hits_7", "Trend Score", "Acceleration", "%_gain_mc"],
                f"weekly_report_leaders_{tier_slug}",
                {
                    "name": "Company",
                    "industry": "Industry",
                    "mcap_tier": "Tier",
                    "hits_7": "Hits 7D",
                    "%_gain_mc": "Gain %",
                },
                ["hits_7", "Trend Score"],
                ["Acceleration", "%_gain_mc"],
                [],
            )

            _render_company_table(
                "Rising Momentum",
                rising_by_tier[tier],
                ["name", "industry", "mcap_tier", "hits_last", "hits_this", "hits_delta", "gain_delta"],
                f"weekly_report_rising_{tier_slug}",
                {
                    "name": "Company",
                    "industry": "Industry",
                    "mcap_tier": "Tier",
                    "hits_last": "Hits LW",
                    "hits_this": "Hits TW",
                    "hits_delta": "Delta Hits",
                    "gain_delta": "Delta Gain",
                },
                ["hits_last", "hits_this", "hits_delta"],
                ["gain_delta"],
                [],
            )

            _render_company_table(
                "Fresh This Week",
                fresh_by_tier[tier],
                ["name", "industry", "mcap_tier", "hits_this", "gain_pct_this", "market_cap_end_this"],
                f"weekly_report_fresh_{tier_slug}",
                {
                    "name": "Company",
                    "industry": "Industry",
                    "mcap_tier": "Tier",
                    "hits_this": "Hits TW",
                    "gain_pct_this": "Gain TW %",
                    "market_cap_end_this": "MCap",
                },
                ["hits_this"],
                ["gain_pct_this"],
                ["market_cap_end_this"],
            )

            with st.expander("Risk Watch", expanded=False):
                _render_company_table(
                    "Falling Momentum",
                    falling_by_tier[tier],
                    ["name", "industry", "mcap_tier", "hits_last", "hits_this", "hits_delta", "gain_delta"],
                    f"weekly_report_falling_{tier_slug}",
                    {
                        "name": "Company",
                        "industry": "Industry",
                        "mcap_tier": "Tier",
                        "hits_last": "Hits LW",
                        "hits_this": "Hits TW",
                        "hits_delta": "Delta Hits",
                        "gain_delta": "Delta Gain",
                    },
                    ["hits_last", "hits_this", "hits_delta"],
                    ["gain_delta"],
                    [],
                )

                _render_company_table(
                    "Dropped From The List",
                    dropped_by_tier[tier],
                    ["name", "industry", "mcap_tier", "hits_last", "gain_pct_last", "market_cap_end_last"],
                    f"weekly_report_dropped_{tier_slug}",
                    {
                        "name": "Company",
                        "industry": "Industry",
                        "mcap_tier": "Tier",
                        "hits_last": "Hits LW",
                        "gain_pct_last": "Gain LW %",
                        "market_cap_end_last": "MCap",
                    },
                    ["hits_last"],
                    ["gain_pct_last"],
                    ["market_cap_end_last"],
                )


if __name__ == "__main__":
    main()

import pandas as pd
from matplotlib import cm
from matplotlib.colors import Normalize, to_hex
import re

from db_utils import format_decimal_columns, format_major_columns


COMMON_RENAME_MAP = {
    "date": "Date",
    "first_seen_date": "First Seen",
    "name": "Name",
    "current_price": "Price",
    "market_cap": "MCap",
    "first_market_cap": "First MCap",
    "Δ% MCap": "Δ% MCap",
    "down_from_52w_high": "↓52W High%",
    "sales": "Sales",
    "opm": "OPM%",
    "opm_last_year": "OPM LY%",
    "operating_profit": "Op Profit",
    "trade_receivables": "Receivables",
    "trade_payables": "Payables",
    "inventory": "Inventory",
    "pe": "P/E",
    "pbv": "P/BV",
    "peg": "PEG",
    "earnings_yield": "Earnings Yield",
    "roa": "ROA",
    "roe": "ROE",
    "other_income": "Oth Income",
    "debt_to_equity": "D/E",
    "change_in_dii_holding": "Δ DII",
    "change_in_fii_holding": "Δ FII",
    "nse_code": "NSE",
    "bse_code": "BSE",
}

FOCUSED_COLS = [
    "date", "name", "current_price", "market_cap", "Δ% MCap",
    "down_from_52w_high", "pe", "pbv", "earnings_yield", "roe",
    "change_in_fii_holding", "nse_code", "bse_code",
]

DETAILED_COLS = [
    "date", "first_seen_date", "name",
    "current_price", "market_cap", "first_market_cap", "Δ% MCap",
    "sales", "opm", "opm_last_year", "operating_profit", "trade_receivables", "trade_payables", "inventory",
    "pe", "pbv", "peg", "earnings_yield",
    "roa", "roe", "other_income",
    "debt_to_equity", "down_from_52w_high",
    "change_in_dii_holding", "change_in_fii_holding",
    "nse_code", "bse_code",
]

_TAG_RE = re.compile(r"<[^>]+>")

BUCKET_ONE_DECIMAL_COLS = [
    "Î”% MCap",
    "down_from_52w_high",
    "change_in_dii_holding",
    "change_in_fii_holding",
    "roa",
    "roe",
    "opm",
    "opm_last_year",
    "debt_to_equity",
]
BUCKET_TWO_DECIMAL_COLS = ["pe", "pbv", "peg", "earnings_yield"]
BUCKET_MAJOR_COLS = [
    "current_price",
    "market_cap",
    "first_market_cap",
    "sales",
    "operating_profit",
    "trade_receivables",
    "trade_payables",
    "inventory",
]


def highlight_valuation_gradient(row):
    def get_style(val, vmin, vmax):
        if pd.isna(val):
            return None
        try:
            val = float(val)
        except (ValueError, TypeError):
            return None

        norm = Normalize(vmin=vmin, vmax=vmax)
        cmap = cm.get_cmap("RdYlGn_r")
        rgba = cmap(norm(min(val, vmax)))
        bg_color = to_hex(rgba)
        r, g, b = rgba[:3]
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        text_color = "#000000" if luminance > 0.6 else "#FFFFFF"
        return f"background-color: {bg_color}; color: {text_color}; font-weight: bold;"

    styles = []
    for col in row.index:
        if col == "P/E":
            styles.append(get_style(row[col], vmin=0, vmax=60) or "")
        elif col == "P/BV":
            styles.append(get_style(row[col], vmin=0, vmax=12) or "")
        else:
            styles.append("")
    return styles


def compute_mcap_change(df):
    df = df.copy()
    for col in ["market_cap", "first_market_cap"]:
        if col not in df.columns:
            df[col] = pd.NA
    df["Δ% MCap"] = (
        100 * (df["market_cap"] - df["first_market_cap"])
        / df["first_market_cap"].replace(0, pd.NA)
    )
    return df


def load_first_caps(get_historical_market_cap):
    hist_df = get_historical_market_cap()
    hist_df["date"] = pd.to_datetime(hist_df["date"])
    return (
        hist_df.sort_values(["name", "date"])
        .groupby("name", as_index=False)
        .first()[["name", "market_cap", "date"]]
        .rename(columns={"market_cap": "first_market_cap", "date": "first_seen_date"})
    )


def style_display_df(display_df):
    display_df = format_major_columns(
        display_df,
        ["Price", "MCap", "First MCap", "Sales", "Op Profit", "Receivables", "Payables", "Inventory"],
    )
    display_df = format_decimal_columns(
        display_df,
        one_decimal_cols=["Δ% MCap", "↓52W High%", "Δ DII", "Δ FII", "ROA", "ROE", "OPM%", "OPM LY%", "D/E"],
        two_decimal_cols=["P/E", "P/BV", "PEG", "Earnings Yield"],
    )
    return display_df


def sort_display_df(display_df, sort_by, sort_options):
    sort_col, ascending = sort_options[sort_by]
    if sort_col not in display_df.columns:
        return display_df

    sort_series = pd.to_numeric(display_df[sort_col], errors="coerce")
    if sort_series.notna().any():
        return (
            display_df.assign(_sort_key=sort_series)
            .sort_values(by="_sort_key", ascending=ascending, na_position="last")
            .drop(columns="_sort_key")
        )

    return display_df.sort_values(by=sort_col, ascending=ascending, na_position="last")


def prepare_display_df(df, columns, sort_by, sort_options, include_industry=False, rename_map=None):
    return prepare_display_df_for_mode(
        df,
        columns,
        sort_by,
        sort_options,
        include_industry=include_industry,
        rename_map=rename_map,
        render_links=False,
    )


def prepare_display_df_for_mode(
    df,
    columns,
    sort_by,
    sort_options,
    include_industry=False,
    rename_map=None,
    render_links=True,
):
    working = df.copy()
    for col in columns:
        if col not in working.columns:
            working[col] = None

    selected_cols = columns + (["industry"] if include_industry else [])
    display_df = working[selected_cols].copy()
    if include_industry and "industry" in display_df.columns:
        display_df = display_df.drop(columns=["industry"])

    display_df = display_df.rename(columns=rename_map or COMMON_RENAME_MAP)
    if "Name" in display_df.columns:
        display_df["Name"] = display_df["Name"].map(
            lambda value: "" if pd.isna(value) else _TAG_RE.sub("", str(value))
        )
    display_df = style_display_df(display_df)
    display_df = sort_display_df(display_df, sort_by, sort_options)
    return display_df


def prepare_grid_df(df, columns, sort_by, sort_options, include_industry=False, rename_map=None):
    working = df.copy()
    for col in columns:
        if col not in working.columns:
            working[col] = None

    selected_cols = columns + (["industry"] if include_industry else [])
    display_df = working[selected_cols].copy()
    if include_industry and "industry" in display_df.columns:
        display_df = display_df.drop(columns=["industry"])

    active_rename_map = rename_map or COMMON_RENAME_MAP
    reverse_rename_map = {value: key for key, value in active_rename_map.items()}
    sort_col, ascending = sort_options[sort_by]
    raw_sort_col = reverse_rename_map.get(sort_col, sort_col)

    if raw_sort_col in display_df.columns:
        sort_series = pd.to_numeric(display_df[raw_sort_col], errors="coerce")
        if sort_series.notna().any():
            display_df = (
                display_df.assign(_sort_key=sort_series)
                .sort_values(by="_sort_key", ascending=ascending, na_position="last")
                .drop(columns="_sort_key")
            )
        else:
            display_df = display_df.sort_values(by=raw_sort_col, ascending=ascending, na_position="last")

    return display_df

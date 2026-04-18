import re
from datetime import date, datetime
from typing import Iterable

import pandas as pd
import streamlit as st


_ANCHOR_RE = re.compile(r'<a\s+href="([^"]+)"[^>]*>(.*?)</a>', re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return _TAG_RE.sub("", str(value)).strip()


def _extract_link(value: object) -> tuple[str, str | None]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "", None
    text = _strip_html(value)
    match = _ANCHOR_RE.search(str(value))
    if match:
        return text or match.group(2), match.group(1)
    return text or str(value), None


_NA_VALUES = {"", "nan", "none", "na", "<na>"}


def _build_screener_url(row: pd.Series) -> str | None:
    nse = str(row.get("nse_code", "")).strip()
    bse = str(row.get("bse_code", "")).strip()
    nse = "" if nse.lower() in _NA_VALUES else nse
    bse = "" if bse.lower() in _NA_VALUES else bse
    # BSE codes arrive as floats (e.g. "543920.0") — strip the decimal
    if bse and "." in bse:
        try:
            bse = str(int(float(bse)))
        except (ValueError, OverflowError):
            bse = ""
    code = nse or bse
    return f"https://www.screener.in/company/{code}/" if code else None


def render_interactive_table(
    df: pd.DataFrame,
    *,
    columns: list[str],
    key: str,
    rename_map: dict[str, str] | None = None,
    integer_cols: list[str] | None = None,
    one_decimal_cols: list[str] | None = None,
    two_decimal_cols: list[str] | None = None,
    major_cols: list[str] | None = None,
    link_col: str | None = None,
    height: int = 360,
    fit_columns: bool = False,   # kept for API compatibility, not used
    max_rows: int = 1000,
) -> None:
    if df.empty:
        st.info("No matching data available.")
        return

    rename_map     = rename_map or {}
    integer_cols   = integer_cols or []
    one_decimal_cols = one_decimal_cols or []
    two_decimal_cols = two_decimal_cols or []
    major_cols     = major_cols or []

    if len(df) > max_rows:
        st.warning(
            f"Showing first {max_rows:,} of {len(df):,} rows to keep the page responsive. "
            "Narrow the filters for more precise results."
        )
        df = df.head(max_rows).copy()

    # Select available columns only
    avail = [c for c in columns if c in df.columns]
    working = df[avail].copy()

    # Build URL column from link_col (extracts href from HTML anchor or falls back to nse/bse)
    _URL_COL = "__url__"
    if link_col and link_col in working.columns:
        texts, urls = [], []
        for _, row in df.loc[working.index].iterrows():
            text, url = _extract_link(row.get(link_col))
            texts.append(text)
            urls.append(url or _build_screener_url(row))
        working[link_col] = texts
        working[_URL_COL] = urls
    else:
        _URL_COL = None

    # Normalize: strip HTML from object cols, format datetime cols
    for col in working.columns:
        if col == _URL_COL:
            continue
        if pd.api.types.is_datetime64_any_dtype(working[col]):
            working[col] = pd.to_datetime(working[col], errors="coerce").dt.strftime("%Y-%m-%d")
        elif working[col].dtype == "object":
            working[col] = working[col].map(
                lambda v: _strip_html(v) if isinstance(v, str) else v
            )

    working = working.rename(columns=rename_map)

    # ── column_config ────────────────────────────────────────────────────────
    col_cfg: dict[str, st.column_config.Column] = {}

    for raw in integer_cols:
        display = rename_map.get(raw, raw)
        if display in working.columns:
            col_cfg[display] = st.column_config.NumberColumn(format="%d")

    for raw in one_decimal_cols:
        display = rename_map.get(raw, raw)
        if display in working.columns:
            col_cfg[display] = st.column_config.NumberColumn(format="%.1f")

    for raw in two_decimal_cols:
        display = rename_map.get(raw, raw)
        if display in working.columns:
            col_cfg[display] = st.column_config.NumberColumn(format="%.2f")

    for raw in major_cols:
        display = rename_map.get(raw, raw)
        if display in working.columns:
            col_cfg[display] = st.column_config.NumberColumn(format="%.0f")

    if _URL_COL and _URL_COL in working.columns:
        col_cfg[_URL_COL] = st.column_config.LinkColumn("↗", display_text="↗", width="small")

    # ── column order: URL column immediately after the link text column ──────
    display_order = [c for c in working.columns if c != _URL_COL]
    if _URL_COL and _URL_COL in working.columns:
        renamed_link = rename_map.get(link_col, link_col) if link_col else None
        if renamed_link and renamed_link in display_order:
            idx = display_order.index(renamed_link)
            display_order.insert(idx + 1, _URL_COL)
        else:
            display_order.insert(0, _URL_COL)

    st.dataframe(
        working,
        width="stretch",
        hide_index=True,
        height=height,
        column_config=col_cfg,
        column_order=display_order,
    )

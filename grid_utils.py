import re
from datetime import date, datetime
from typing import Iterable

import pandas as pd
import streamlit as st

try:
    from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

    AGGRID_AVAILABLE = True
except ImportError:
    AgGrid = GridOptionsBuilder = JsCode = None
    AGGRID_AVAILABLE = False


_ANCHOR_RE = re.compile(r'<a\s+href="([^"]+)"[^>]*>(.*?)</a>', re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return _TAG_RE.sub("", str(value)).strip()


def _extract_link(value: object) -> tuple[str, str | None]:
    if value is None or pd.isna(value):
        return "", None

    text = _strip_html(value)
    match = _ANCHOR_RE.search(str(value))
    if match:
        return text or match.group(2), match.group(1)
    return text or str(value), None


def _build_screener_url(row: pd.Series) -> str | None:
    nse = str(row.get("nse_code", "")).strip()
    bse = str(row.get("bse_code", "")).strip()
    code = nse or bse
    return f"https://www.screener.in/company/{code}/" if code else None


def _is_date_like(value: object) -> bool:
    return isinstance(value, (pd.Timestamp, datetime, date))


def _normalize_object_value(value: object) -> object:
    if value is None or pd.isna(value):
        return None
    if _is_date_like(value):
        return pd.to_datetime(value).strftime("%Y-%m-%d")
    if isinstance(value, str):
        return _strip_html(value)
    return value


def _normalize_for_grid(df: pd.DataFrame, *, link_col: str | None = None, url_field: str | None = None) -> pd.DataFrame:
    normalized = df.copy()
    for col in normalized.columns:
        if url_field and col == url_field:
            continue
        if pd.api.types.is_datetime64_any_dtype(normalized[col]):
            normalized[col] = pd.to_datetime(normalized[col], errors="coerce").dt.strftime("%Y-%m-%d")
            continue
        if normalized[col].dtype == "object":
            normalized[col] = normalized[col].map(_normalize_object_value)
    return normalized


def _js_number_formatter(min_digits: int, max_digits: int, integer: bool = False) -> "JsCode":
    digits = (
        ""
        if integer
        else f", {{ minimumFractionDigits: {min_digits}, maximumFractionDigits: {max_digits} }}"
    )
    return JsCode(
        f"""
        function(params) {{
            if (params.value === null || params.value === undefined || params.value === "") {{
                return "-";
            }}
            const numericValue = Number(params.value);
            if (Number.isNaN(numericValue)) {{
                return params.value;
            }}
            return numericValue.toLocaleString(undefined{digits});
        }}
        """
    )


def _js_major_formatter() -> "JsCode":
    return JsCode(
        """
        function(params) {
            if (params.value === null || params.value === undefined || params.value === "") {
                return "-";
            }
            const numericValue = Number(params.value);
            if (Number.isNaN(numericValue)) {
                return params.value;
            }
            const absValue = Math.abs(numericValue);
            if (absValue >= 1) {
                return numericValue.toLocaleString(undefined, {
                    minimumFractionDigits: 0,
                    maximumFractionDigits: 0
                });
            }
            return numericValue.toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
        }
        """
    )


def _format_for_fallback(
    df: pd.DataFrame,
    integer_cols: Iterable[str],
    one_decimal_cols: Iterable[str],
    two_decimal_cols: Iterable[str],
    major_cols: Iterable[str],
) -> pd.DataFrame:
    formatted = df.copy()

    for col in integer_cols:
        if col in formatted.columns:
            formatted[col] = pd.to_numeric(formatted[col], errors="coerce").map(
                lambda value: "-" if pd.isna(value) else f"{int(value)}"
            )

    for col in one_decimal_cols:
        if col in formatted.columns:
            formatted[col] = pd.to_numeric(formatted[col], errors="coerce").map(
                lambda value: "-" if pd.isna(value) else f"{value:.1f}"
            )

    for col in two_decimal_cols:
        if col in formatted.columns:
            formatted[col] = pd.to_numeric(formatted[col], errors="coerce").map(
                lambda value: "-" if pd.isna(value) else f"{value:.2f}"
            )

    for col in major_cols:
        if col in formatted.columns:
            formatted[col] = pd.to_numeric(formatted[col], errors="coerce").map(
                lambda value: "-"
                if pd.isna(value)
                else (f"{value:,.0f}" if abs(value) >= 1 else f"{value:,.2f}")
            )

    return formatted


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
    fit_columns: bool = False,
    max_rows: int = 1000,
) -> None:
    if df.empty:
        st.info("No matching data available.")
        return

    rename_map = rename_map or {}
    integer_cols = integer_cols or []
    one_decimal_cols = one_decimal_cols or []
    two_decimal_cols = two_decimal_cols or []
    major_cols = major_cols or []

    source_count = len(df)
    if source_count > max_rows:
        st.warning(f"Showing first {max_rows:,} of {source_count:,} rows to keep the page responsive. Narrow the filters for more precise results.")
        df = df.head(max_rows).copy()

    working = df.loc[:, columns].copy()
    url_field = None

    if link_col and link_col in working.columns:
        url_field = f"__link__{link_col}"
        link_texts: list[str] = []
        link_urls: list[str | None] = []
        for _, row in df.loc[working.index].iterrows():
            text, url = _extract_link(row.get(link_col))
            link_texts.append(text)
            link_urls.append(url or _build_screener_url(row))
        working[link_col] = link_texts
        working[url_field] = link_urls

    working = _normalize_for_grid(working, link_col=link_col, url_field=url_field)
    working = working.rename(columns=rename_map)

    if not AGGRID_AVAILABLE:
        fallback_df = working.copy()
        if link_col and link_col in columns:
            renamed_link_col = rename_map.get(link_col, link_col)
            fallback_df[renamed_link_col] = fallback_df[renamed_link_col].map(_strip_html)
        fallback_df = _format_for_fallback(
            fallback_df,
            integer_cols=[rename_map.get(col, col) for col in integer_cols],
            one_decimal_cols=[rename_map.get(col, col) for col in one_decimal_cols],
            two_decimal_cols=[rename_map.get(col, col) for col in two_decimal_cols],
            major_cols=[rename_map.get(col, col) for col in major_cols],
        )
        if url_field and url_field in fallback_df.columns:
            fallback_df = fallback_df.drop(columns=[url_field])
        st.info("Install `streamlit-aggrid` for multi-sort and per-column filters. Showing Streamlit fallback table.")
        st.dataframe(fallback_df, use_container_width=True, hide_index=True)
        return

    gb = GridOptionsBuilder.from_dataframe(working)
    gb.configure_default_column(
        sortable=True,
        filter=True,
        floatingFilter=True,
        resizable=True,
        suppressMenu=False,
        minWidth=110,
        flex=1,
        wrapHeaderText=True,
        autoHeaderHeight=True,
    )
    gb.configure_grid_options(alwaysMultiSort=True, animateRows=False, pagination=True, paginationPageSize=50)

    for col in integer_cols:
        gb.configure_column(
            rename_map.get(col, col),
            type=["numericColumn", "numberColumnFilter"],
            valueFormatter=_js_number_formatter(0, 0, integer=True),
        )

    for col in one_decimal_cols:
        gb.configure_column(
            rename_map.get(col, col),
            type=["numericColumn", "numberColumnFilter"],
            valueFormatter=_js_number_formatter(1, 1),
        )

    for col in two_decimal_cols:
        gb.configure_column(
            rename_map.get(col, col),
            type=["numericColumn", "numberColumnFilter"],
            valueFormatter=_js_number_formatter(2, 2),
        )

    for col in major_cols:
        gb.configure_column(
            rename_map.get(col, col),
            type=["numericColumn", "numberColumnFilter"],
            valueFormatter=_js_major_formatter(),
        )

    if link_col and url_field:
        renamed_link_col = rename_map.get(link_col, link_col)
        gb.configure_column(renamed_link_col, pinned="left")
        gb.configure_column(url_field, hide=True)

    grid_options = gb.build()
    AgGrid(
        working,
        gridOptions=grid_options,
        allow_unsafe_jscode=True,
        fit_columns_on_grid_load=fit_columns,
        height=height,
        theme="streamlit",
        key=key,
    )

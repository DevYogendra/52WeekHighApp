"""
valuation/financials_sensitivity.py — sensitivity grid generators for Bank / NBFC valuation.

All rate inputs are decimals (0.16 = 16%).
"""

from __future__ import annotations

import pandas as pd

from valuation.financials_models import (
    justified_pb_single_stage,
    justified_pb_two_stage,
)


def _fmt(val: float | None) -> str:
    if val is None or val != val:  # None or NaN
        return "—"
    return f"{val:.2f}x"


def _color_pb(val):
    """Streamlit styler: colour P/B cells green → red."""
    try:
        v = float(str(val).replace("x", ""))
        if v < 1.5:   return "background-color:#d4edda;color:#155724"
        elif v < 2.5: return "background-color:#fff3cd;color:#856404"
        elif v < 4.0: return "background-color:#fde8d8;color:#7d3c0f"
        else:         return "background-color:#f8d7da;color:#721c24"
    except (TypeError, ValueError):
        return ""


# ── Table 1: ROE × CoE → justified P/B ───────────────────────────────────────

def sensitivity_roe_coe(
    g: float,
    roe_values: list[float] | None = None,
    coe_values: list[float] | None = None,
) -> pd.DataFrame:
    """
    Rows = ROE, Columns = CoE, Values = single-stage justified P/B.
    """
    roe_values = roe_values or [0.10, 0.12, 0.14, 0.16, 0.18, 0.20, 0.22, 0.25]
    coe_values = coe_values or [0.10, 0.11, 0.12, 0.13, 0.14, 0.15, 0.16, 0.18]

    rows = []
    for roe in roe_values:
        row = {}
        for coe in coe_values:
            pb = justified_pb_single_stage(roe, coe, g)
            row[f"CoE {coe*100:.0f}%"] = _fmt(pb)
        rows.append(row)

    df = pd.DataFrame(rows, index=[f"ROE {r*100:.0f}%" for r in roe_values])
    df.index.name = "ROE \\ CoE"
    return df


# ── Table 2: ROE × Growth → justified P/B ────────────────────────────────────

def sensitivity_roe_growth(
    coe: float,
    roe_values: list[float] | None = None,
    g_values: list[float] | None = None,
) -> pd.DataFrame:
    """
    Rows = ROE, Columns = Growth, Values = single-stage justified P/B.
    """
    roe_values = roe_values or [0.10, 0.12, 0.14, 0.16, 0.18, 0.20, 0.22, 0.25]
    g_values   = g_values   or [0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 0.12]

    rows = []
    for roe in roe_values:
        row = {}
        for g in g_values:
            pb = justified_pb_single_stage(roe, coe, g)
            row[f"g {g*100:.0f}%"] = _fmt(pb)
        rows.append(row)

    df = pd.DataFrame(rows, index=[f"ROE {r*100:.0f}%" for r in roe_values])
    df.index.name = "ROE \\ Growth"
    return df


# ── Table 3: Fade Years × Terminal ROE → justified P/B ───────────────────────

def sensitivity_fade_terminal_roe(
    roe_high: float,
    coe: float,
    g_high: float,
    g_terminal: float,
    fade_year_values: list[int] | None = None,
    terminal_roe_values: list[float] | None = None,
) -> pd.DataFrame:
    """
    Rows = fade years, Columns = terminal ROE, Values = two-stage justified P/B.
    """
    fade_year_values    = fade_year_values    or [3, 5, 7, 8, 10, 12, 15]
    terminal_roe_values = terminal_roe_values or [0.10, 0.12, 0.13, 0.14, 0.15, 0.16, 0.18]

    rows = []
    for y in fade_year_values:
        row = {}
        for t_roe in terminal_roe_values:
            pb = justified_pb_two_stage(roe_high, coe, g_high, y, t_roe, g_terminal)
            row[f"ROE_t {t_roe*100:.0f}%"] = _fmt(pb)
        rows.append(row)

    df = pd.DataFrame(rows, index=[f"{y}y" for y in fade_year_values])
    df.index.name = "Fade \\ Terminal ROE"
    return df

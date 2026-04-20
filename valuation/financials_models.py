"""
valuation/financials_models.py — core math for Bank / NBFC valuation.

All functions return None for invalid / degenerate inputs rather than raising.
Inputs are plain floats (not percentages): ROE 0.16 means 16%.
"""

from __future__ import annotations

import math


# ── Growth ────────────────────────────────────────────────────────────────────

def sustainable_growth_rate(roe: float, retention: float) -> float:
    """g = ROE × Retention."""
    return roe * retention


# ── Single-stage justified P/B ────────────────────────────────────────────────

def justified_pb_single_stage(roe: float, coe: float, g: float) -> float | None:
    """
    P/B = (ROE - g) / (CoE - g)

    Returns None when CoE <= g (growing perpetuity breaks) or ROE <= 0.
    """
    if coe <= g or roe <= 0:
        return None
    return (roe - g) / (coe - g)


# ── Derived justified P/E ─────────────────────────────────────────────────────

def justified_pe_from_pb(justified_pb: float, roe: float) -> float | None:
    """P/E = P/B / ROE  (ROE expressed as decimal, e.g. 0.16)."""
    if not justified_pb or roe <= 0:
        return None
    return justified_pb / roe


# ── Book value compounding ────────────────────────────────────────────────────

def next_book_value(book_value: float, growth: float) -> float:
    """Book value at end of next period: B × (1 + g)."""
    return book_value * (1 + growth)


# ── Residual income / two-stage P/B ──────────────────────────────────────────

def residual_income_value(
    book_value_per_share: float,
    roe_high: float,
    coe: float,
    g_high: float,
    years: int,
    roe_terminal: float,
    g_terminal: float,
) -> float | None:
    """
    Intrinsic price via residual income (RI) model:

        P0 = B0 + Σ(t=1..n) [ (ROE_t - CoE) × B_{t-1} ] / (1+CoE)^t
           + Terminal RI value

    Terminal RI = (ROE_terminal - CoE) × B_n / (CoE - g_terminal)
    discounted back n periods.

    Returns None for degenerate inputs.
    """
    if book_value_per_share <= 0 or roe_high <= 0 or coe <= 0:
        return None
    if coe <= g_terminal:
        return None

    bv = book_value_per_share
    pv_ri = 0.0
    for t in range(1, years + 1):
        ri = (roe_high - coe) * bv
        pv_ri += ri / (1 + coe) ** t
        bv = bv * (1 + g_high)

    # Terminal value at end of year `years`
    if coe <= g_terminal:
        return None
    tv = (roe_terminal - coe) * bv / (coe - g_terminal)
    pv_tv = tv / (1 + coe) ** years

    return book_value_per_share + pv_ri + pv_tv


def justified_pb_two_stage(
    roe_high: float,
    coe: float,
    g_high: float,
    years: int,
    roe_terminal: float,
    g_terminal: float,
) -> float | None:
    """
    Two-stage justified P/B using the RI model with B0 = 1 (unit book value).

    Dividing by B0=1 gives P/B directly.
    """
    val = residual_income_value(1.0, roe_high, coe, g_high, years, roe_terminal, g_terminal)
    return val  # already P/B since B0 = 1


# ── Fade model ────────────────────────────────────────────────────────────────

def linear_fade_series(start: float, end: float, years: int) -> list[float]:
    """Linear interpolation from start to end over `years` steps (inclusive of both ends)."""
    if years <= 1:
        return [start]
    return [start + (end - start) * i / (years - 1) for i in range(years)]


def justified_pb_fade_model(
    roe_start: float,
    roe_end: float,
    g_start: float,
    g_end: float,
    coe: float,
    years: int,
) -> float | None:
    """
    Fade model: ROE and growth both fade linearly from start → end over `years`.
    Uses RI framework with B0 = 1.
    """
    if years < 1 or coe <= 0 or roe_start <= 0:
        return None

    roe_path = linear_fade_series(roe_start, roe_end, years)
    g_path = linear_fade_series(g_start, g_end, years)

    bv = 1.0
    pv_ri = 0.0
    for t, (roe_t, g_t) in enumerate(zip(roe_path, g_path), start=1):
        ri = (roe_t - coe) * bv
        pv_ri += ri / (1 + coe) ** t
        bv = bv * (1 + g_t)

    # Terminal: use end-state assumptions in perpetuity
    g_terminal = g_path[-1]
    roe_terminal = roe_path[-1]
    if coe <= g_terminal:
        return None
    tv = (roe_terminal - coe) * bv / (coe - g_terminal)
    pv_tv = tv / (1 + coe) ** years

    return 1.0 + pv_ri + pv_tv


# ── Reverse valuation ─────────────────────────────────────────────────────────

def implied_roe_from_pb(current_pb: float, coe: float, g: float) -> float | None:
    """
    Invert single-stage P/B formula:
        P/B = (ROE - g) / (CoE - g)
        ROE = P/B × (CoE - g) + g
    """
    if current_pb <= 0 or coe <= g:
        return None
    return current_pb * (coe - g) + g


def implied_growth_from_pb(current_pb: float, roe: float, coe: float) -> float | None:
    """
    Invert single-stage P/B for g:
        P/B × (CoE - g) = ROE - g
        P/B × CoE - P/B × g = ROE - g
        g × (1 - P/B) = ROE - P/B × CoE
        g = (ROE - P/B × CoE) / (1 - P/B)
    Returns None when denominator is zero or result is nonsensical.
    """
    if current_pb <= 0 or roe <= 0:
        return None
    denom = 1 - current_pb
    if abs(denom) < 1e-9:
        return None
    g = (roe - current_pb * coe) / denom
    if g < 0 or g >= coe:
        return None
    return g


def implied_fade_years(
    current_pb: float,
    roe_high: float,
    coe: float,
    g_high: float,
    roe_terminal: float,
    g_terminal: float,
    max_years: int = 30,
) -> int | None:
    """
    Search for the fade duration (1..max_years) where two-stage justified P/B
    is closest to `current_pb`. Returns the best-fit year count.
    """
    if current_pb <= 0:
        return None
    best_years = None
    best_diff = math.inf
    for y in range(1, max_years + 1):
        pb = justified_pb_two_stage(roe_high, coe, g_high, y, roe_terminal, g_terminal)
        if pb is None:
            continue
        diff = abs(pb - current_pb)
        if diff < best_diff:
            best_diff = diff
            best_years = y
    return best_years

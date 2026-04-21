"""Shared Market Cap tier utilities used across all views."""

from __future__ import annotations

import pandas as pd
import streamlit as st

# Thresholds in ₹ Crores  (label, inclusive_min, exclusive_max)
MCAP_TIERS: list[tuple[str, float, float]] = [
    ("🔴 Micro",  0,          1_000),
    ("🟠 Small",  1_000,      5_000),
    ("🟡 Mid",    5_000,     25_000),
    ("🟢 Large", 25_000,   1_00_000),
    ("🔵 Mega", 1_00_000, float("inf")),
]
TIER_LABELS: list[str] = [t[0] for t in MCAP_TIERS]
FOCUS_TIER_LABELS: list[str] = list(reversed(TIER_LABELS))
GLOBAL_MCAP_FOCUS_KEY = "global_mcap_focus"


def get_mcap_tier(value) -> str:
    """Return emoji-prefixed tier label for a ₹Cr value. NA / negative → Micro."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return TIER_LABELS[0]
    if pd.isna(v) or v < 0:
        return TIER_LABELS[0]
    for label, lo, hi in MCAP_TIERS:
        if lo <= v < hi:
            return label
    return TIER_LABELS[-1]  # Mega (≥ 1,00,000 Cr)


def add_mcap_tier_col(
    df: pd.DataFrame,
    col: str = "market_cap",
    out_col: str = "mcap_tier",
) -> pd.DataFrame:
    """Return df with a new `out_col` containing tier labels derived from `col`.

    Safe: if `col` is missing, every row gets Micro.
    Does not mutate the original dataframe.
    """
    df = df.copy()
    if col in df.columns:
        df[out_col] = pd.to_numeric(df[col], errors="coerce").apply(get_mcap_tier)
    else:
        df[out_col] = TIER_LABELS[0]
    return df


def render_mcap_sidebar_filter(key: str) -> list[str]:
    """Render a multiselect in the sidebar; returns the currently selected tier labels.

    Defaults to all tiers selected (i.e. no filtering).
    """
    return st.sidebar.multiselect(
        "MCap Tier",
        options=TIER_LABELS,
        default=TIER_LABELS,
        key=key,
    )


def render_global_mcap_focus_sidebar() -> list[str]:
    """Render the shared app-wide market-cap focus control."""
    return st.sidebar.multiselect(
        "MCap Focus",
        options=FOCUS_TIER_LABELS,
        default=FOCUS_TIER_LABELS,
        key=GLOBAL_MCAP_FOCUS_KEY,
        help="Applies across the research views until you change it.",
    )


def get_global_mcap_focus() -> list[str]:
    """Return the current app-wide MCap focus selection."""
    if GLOBAL_MCAP_FOCUS_KEY not in st.session_state:
        return FOCUS_TIER_LABELS.copy()
    return list(st.session_state[GLOBAL_MCAP_FOCUS_KEY])


def apply_mcap_tier_filter(
    df: pd.DataFrame,
    selected_tiers: list[str],
    tier_col: str = "mcap_tier",
) -> pd.DataFrame:
    """Filter df to rows whose `tier_col` is in `selected_tiers`.

    No-op if all tiers are selected or if `tier_col` is missing.
    """
    if not selected_tiers or len(selected_tiers) == len(TIER_LABELS):
        return df
    if tier_col not in df.columns:
        return df
    return df[df[tier_col].isin(selected_tiers)]

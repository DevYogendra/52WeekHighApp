"""
valuation/financials_defaults.py — subtype default assumptions for Bank / NBFC valuation.

All rate fields are decimals (0.16 = 16%). Growth fields too.
"""

from __future__ import annotations

# ── Subtype registry ──────────────────────────────────────────────────────────

SUBTYPES = [
    "Private Bank",
    "PSU Bank",
    "Small Finance Bank",
    "Retail NBFC",
    "HFC",
    "Gold Loan NBFC",
    "Vehicle Finance NBFC",
    "Consumer Finance NBFC",
    "MFI",
    "Other",
]

_DEFAULTS: dict[str, dict] = {
    "Private Bank": {
        "base_coe": 0.13,
        "default_roe": 0.16,
        "default_retention": 0.75,
        "default_fade_years": 8,
        "terminal_roe": 0.14,
        "terminal_growth": 0.06,
    },
    "PSU Bank": {
        "base_coe": 0.155,
        "default_roe": 0.13,
        "default_retention": 0.70,
        "default_fade_years": 4,
        "terminal_roe": 0.11,
        "terminal_growth": 0.05,
    },
    "Small Finance Bank": {
        "base_coe": 0.16,
        "default_roe": 0.17,
        "default_retention": 0.78,
        "default_fade_years": 5,
        "terminal_roe": 0.13,
        "terminal_growth": 0.055,
    },
    "Retail NBFC": {
        "base_coe": 0.145,
        "default_roe": 0.18,
        "default_retention": 0.78,
        "default_fade_years": 7,
        "terminal_roe": 0.15,
        "terminal_growth": 0.06,
    },
    "HFC": {
        "base_coe": 0.14,
        "default_roe": 0.16,
        "default_retention": 0.75,
        "default_fade_years": 6,
        "terminal_roe": 0.14,
        "terminal_growth": 0.055,
    },
    "Gold Loan NBFC": {
        "base_coe": 0.14,
        "default_roe": 0.20,
        "default_retention": 0.70,
        "default_fade_years": 7,
        "terminal_roe": 0.16,
        "terminal_growth": 0.055,
    },
    "Vehicle Finance NBFC": {
        "base_coe": 0.145,
        "default_roe": 0.17,
        "default_retention": 0.75,
        "default_fade_years": 6,
        "terminal_roe": 0.14,
        "terminal_growth": 0.055,
    },
    "Consumer Finance NBFC": {
        "base_coe": 0.15,
        "default_roe": 0.18,
        "default_retention": 0.78,
        "default_fade_years": 5,
        "terminal_roe": 0.14,
        "terminal_growth": 0.055,
    },
    "MFI": {
        "base_coe": 0.18,
        "default_roe": 0.19,
        "default_retention": 0.80,
        "default_fade_years": 3,
        "terminal_roe": 0.13,
        "terminal_growth": 0.05,
    },
    "Other": {
        "base_coe": 0.14,
        "default_roe": 0.15,
        "default_retention": 0.75,
        "default_fade_years": 6,
        "terminal_roe": 0.13,
        "terminal_growth": 0.055,
    },
}

# Map industries from the existing highs DB → subtype
INDUSTRY_TO_SUBTYPE: dict[str, str] = {
    "Private Sector Bank": "Private Bank",
    "Public Sector Bank": "PSU Bank",
    "Other Bank": "PSU Bank",
    "Small Finance Bank": "Small Finance Bank",
    "Non Banking Financial Company (NBFC)": "Retail NBFC",
    "Housing Finance Company": "HFC",
    "Microfinance": "MFI",
    "Financial Institution": "Other",
    "Financial Products Distributor": "Other",
}


def get_defaults(subtype: str) -> dict:
    """Return default assumption dict for the given subtype (falls back to 'Other')."""
    return _DEFAULTS.get(subtype, _DEFAULTS["Other"]).copy()


def industry_to_subtype(industry: str) -> str:
    """Map a DB industry label to the closest subtype string."""
    return INDUSTRY_TO_SUBTYPE.get(industry, "Other")

import configparser
import os
from pathlib import Path

_BASE = Path(__file__).parent

# Database configuration
DB_PATH = str(_BASE / "highs.db")

# Cache configuration (TTL in seconds)
CACHE_TTL = 3600  # 1 hour

# Database table names
TABLE_HIGHS = "highs"
TABLE_FIVETOFIFTYCLUB = "fivetofiftyclub"
TABLE_DOWNFROMHIGH = "downfromhigh"

# Screener.in configuration
SCREENER_URL_TEMPLATE = "https://www.screener.in/company/{code}/"

# Data processing configuration
INVALID_CODES = {"", "NA", "<NA>", "<N/A>", "N/A", "NONE", "NAN"}
STANDARD_COLUMNS = ["bse_code", "nse_code", "industry", "name"]
COLUMN_TYPES = {
    "bse_code": "Int64",
    "nse_code": "string",
    "industry": "string",
    "name": "string",
}

# Chart configuration
PLOT_HEIGHT = 600
PLOT_COLOR_SCALE = "RdYlGn"

# Rolling window configurations (days)
ROLLING_WINDOWS = [7, 30, 60]

# ── ETL / Data collection ──────────────────────────────────────────────────────

# Directory paths
DOWNLOAD_DIR = _BASE / "screener_downloads"
ARCHIVE_DIR  = _BASE / "__screener_downloads"

# Logging
ETL_LOG_FILE    = str(_BASE / "etl.log")
LOG_FORMAT      = "%(asctime)s [%(levelname)s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Credentials (env vars take priority; fallback to config.local.ini via load_config())
SCREENER_USERNAME = os.getenv("SCREENER_USERNAME", "")
SCREENER_PASSWORD = os.getenv("SCREENER_PASSWORD", "")

# Column aliases — normalise varied Screener.in CSV headers to consistent DB names
COLUMN_ALIASES = {
    "price_to_earning": "pe",
    "p_e": "pe",
    "price_to_book_value": "pbv",
    "peg_ratio": "peg",
    "roa_pct": "roa",
    "return_on_assets": "roa",
    "roe_pct": "roe",
    "return_on_equity": "roe",
    "debt_to_equity": "debt_to_equity",
    "cash_eq": "cash_equivalents",
    "face_value_rs": "face_value",
    "dividend_yield_pct": "dividend_yield",
    "market_cap": "market_cap",
    "market_capitalization": "market_cap",
    "current_price": "current_price",
    "industry_group": "industry_group",
    "operating_profit_margin": "opm",
    "operating_profit_margin_ly": "opm_last_year",
    "other_income": "other_income",
    "down_from_52w_high": "down_from_52w_high",
}

# ETL jobs — one per Screener screen
ETL_JOBS = [
    {"subfolder": "52weekhigh",  "table": TABLE_HIGHS,          "processed": "processed_files"},
    {"subfolder": "downfromhigh","table": TABLE_DOWNFROMHIGH,    "processed": "processed_files_down"},
    {"subfolder": "5to50club",   "table": TABLE_FIVETOFIFTYCLUB, "processed": "processed_files_5to50"},
]


def load_config() -> configparser.ConfigParser:
    """Load config.local.ini from the project root. Raises if missing."""
    cfg = configparser.ConfigParser()
    local = _BASE / "config.local.ini"
    if not local.exists():
        raise RuntimeError(
            "Missing config.local.ini. Copy config.example.ini → config.local.ini and fill in your values."
        )
    cfg.read(local)
    return cfg


def ensure_directories_exist() -> None:
    """Create screener_downloads and archive directories if they don't exist."""
    for d in [DOWNLOAD_DIR, ARCHIVE_DIR,
              DOWNLOAD_DIR / "52weekhigh",
              DOWNLOAD_DIR / "downfromhigh",
              DOWNLOAD_DIR / "5to50club"]:
        d.mkdir(parents=True, exist_ok=True)


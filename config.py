from pathlib import Path

# Database configuration
DB_PATH = str(Path(__file__).parent / "highs.db")

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


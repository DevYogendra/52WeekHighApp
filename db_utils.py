import datetime
import sqlite3
import pandas as pd
import streamlit as st
from config import DB_PATH

DB_PATH = "highs.db"

def get_fivetofiftyclub_dates():
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT DISTINCT date FROM fivetofiftyclub ORDER BY date"
    df = pd.read_sql(query, conn)
    conn.close()
    return df["date"].tolist()

def get_fivetofiftyclub_data_for_date(date_str):
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM fivetofiftyclub WHERE date = ?"
    df = pd.read_sql(query, conn, params=(date_str,))
    conn.close()
    return df

def get_downfromhigh_dates():
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT DISTINCT date FROM downfromhigh ORDER BY date"
    df = pd.read_sql(query, conn)
    conn.close()
    return df["date"].tolist()

def get_downfromhigh_data_for_date(date_str):
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM downfromhigh WHERE date = ?"
    df = pd.read_sql(query, conn, params=(date_str,))
    conn.close()
    return df

# ----------------------------------------------------------------------
# 🔗  Convenience: add clickable links for Screener.in
# ----------------------------------------------------------------------
def add_screener_links(df: pd.DataFrame) -> pd.DataFrame:
    def is_valid(code):
        try:
            if pd.isna(code):
                return False
            code = str(code).strip().upper()
            return code not in {"", "NA", "<NA>", "<N/A>", "N/A", "NONE", "NAN"}
        except:
            return False
        
    def make_link(row):
        name = row.get("name", "")
        nse = str(row.get("nse_code", "")).strip()
        bse = str(row.get("bse_code", "")).strip()

        # Prefer NSE if available and non-empty
        if is_valid(nse):
            return f'<a href="https://www.screener.in/company/{nse}/" target="_blank">{name}</a>'
        elif is_valid(bse):
            return f'<a href="https://www.screener.in/company/{bse}/" target="_blank">{name}</a>'
        else:
            print(f"⚠️ No NSE/BSE code for {name}")
            return name  # fallback to plain name if no codes

    df = df.copy()
    df["name"] = df.apply(make_link, axis=1)
    return df


# ----------------------------------------------------------------------
# 📄  Cached data helpers
# ----------------------------------------------------------------------
@st.cache_data
def get_momentum_summary() -> pd.DataFrame:
    import datetime
    today = datetime.date.today()
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)

    def _hit_counts(days: int) -> pd.DataFrame:
        since = today - datetime.timedelta(days=days)
        q = f"""
            SELECT name, COUNT(*) AS hits_{days}
            FROM highs
            WHERE date >= ?
            GROUP BY name
        """
        return pd.read_sql(q, conn, params=(since,)).set_index("name")

    # Rolling hit counts
    counts7  = _hit_counts(7)
    counts30 = _hit_counts(30)
    counts60 = _hit_counts(60)

    # Latest snapshot for each stock
    latest = pd.read_sql(
        """
        SELECT h1.*
        FROM highs h1
        JOIN (
            SELECT name, MAX(date) AS max_date
            FROM highs
            GROUP BY name
        ) h2 ON h1.name = h2.name AND h1.date = h2.max_date
        """,
        conn,
    ).set_index("name")

    # Add missing columns if needed (due to old rows)
    for col in ["market_cap", "first_market_cap", "first_seen_date"]:
        if col not in latest.columns:
            latest[col] = pd.NA

    latest["%_gain_mc"] = (
        100 * (latest["market_cap"] - latest["first_market_cap"])
        / latest["first_market_cap"].replace(0, pd.NA)
    )

    required_cols = [
        "nse_code", "bse_code", "industry", "market_cap",
        "first_market_cap", "first_seen_date", "%_gain_mc"
    ]
    for col in required_cols:
        if col not in latest.columns:
            latest[col] = pd.NA

    df = latest[required_cols]
    df = df.join(counts7).join(counts30).join(counts60)

    # Type hygiene
    if "bse_code" in df.columns:
        df["bse_code"] = pd.to_numeric(df["bse_code"], errors="coerce").astype("Int64")
    if "nse_code" in df.columns:
        df["nse_code"] = df["nse_code"].astype("string")
    if "industry" in df.columns:
        df["industry"] = df["industry"].astype("string")

    conn.close()
    return df.reset_index()


@st.cache_data
def get_historical_market_cap() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    df = pd.read_sql("SELECT * FROM highs", conn)
    
    df["date"] = pd.to_datetime(df["date"])

    if "bse_code" in df.columns:
        df["bse_code"] = pd.to_numeric(df["bse_code"], errors="coerce").astype("Int64")

    if "nse_code" in df.columns:
        df["nse_code"] = df["nse_code"].astype("string")

    if "industry" in df.columns:
        df["industry"] = df["industry"].astype("string")

    if "name" in df.columns:
        df["name"] = df["name"].astype("string")

    conn.close()
    return df


@st.cache_data
def get_all_dates() -> list[datetime.date]:
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    df = pd.read_sql("SELECT DISTINCT date FROM highs ORDER BY date", conn)
    conn.close()
    return pd.to_datetime(df["date"]).dt.date.tolist()


@st.cache_data
def get_data_for_date(selected_date: str | datetime.date) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    df = pd.read_sql("SELECT * FROM highs WHERE date = ?", conn, params=(selected_date,))
    conn.close()

    if "bse_code" in df.columns:
        df["bse_code"] = pd.to_numeric(df["bse_code"], errors="coerce").astype("Int64")

    for col in ["nse_code", "industry", "name"]:
        if col in df.columns:
            df[col] = df[col].astype("string")

    return df


@st.cache_data
def get_sparkline_data() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    df = pd.read_sql("SELECT name, date FROM highs", conn)
    conn.close()

    df["date"] = pd.to_datetime(df["date"])
    df["value"] = 1  # presence flag
    return df

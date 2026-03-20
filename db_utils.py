import datetime
import sqlite3
import pandas as pd
import streamlit as st
from config import DB_PATH, CACHE_TTL, TABLE_HIGHS, TABLE_FIVETOFIFTYCLUB, TABLE_DOWNFROMHIGH, INVALID_CODES, COLUMN_TYPES

def get_fivetofiftyclub_dates():
    """Fetch distinct dates from fivetofiftyclub table."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            query = f"SELECT DISTINCT date FROM {TABLE_FIVETOFIFTYCLUB} ORDER BY date"
            df = pd.read_sql(query, conn)
            return df["date"].tolist()
    except sqlite3.Error as e:
        st.error(f"Database error: {e}")
        return []

def get_fivetofiftyclub_data_for_date(date_str: str) -> pd.DataFrame:
    """Fetch fivetofiftyclub data for a specific date."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            query = f"SELECT * FROM {TABLE_FIVETOFIFTYCLUB} WHERE date = ?"
            df = pd.read_sql(query, conn, params=(date_str,))
            return df
    except sqlite3.Error as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame()

def get_downfromhigh_dates():
    """Fetch distinct dates from downfromhigh table."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            query = f"SELECT DISTINCT date FROM {TABLE_DOWNFROMHIGH} ORDER BY date"
            df = pd.read_sql(query, conn)
            return df["date"].tolist()
    except sqlite3.Error as e:
        st.error(f"Database error: {e}")
        return []

def get_downfromhigh_data_for_date(date_str: str) -> pd.DataFrame:
    """Fetch downfromhigh data for a specific date."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            query = f"SELECT * FROM {TABLE_DOWNFROMHIGH} WHERE date = ?"
            df = pd.read_sql(query, conn, params=(date_str,))
            return df
    except sqlite3.Error as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame()

# ----------------------------------------------------------------------
# 🔗  Convenience: add clickable links for Screener.in
# ----------------------------------------------------------------------
def add_screener_links(df: pd.DataFrame) -> pd.DataFrame:
    def is_valid(code):
        try:
            if pd.isna(code):
                return False
            code = str(code).strip().upper()
            return code not in INVALID_CODES
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
            st.warning(f"⚠️ No NSE/BSE code for {name}")
            return name  # fallback to plain name if no codes

    df = df.copy()
    df["name"] = df.apply(make_link, axis=1)
    return df


# ----------------------------------------------------------------------
# 📄  Cached data helpers
# ----------------------------------------------------------------------
def _apply_standard_types(df: pd.DataFrame) -> pd.DataFrame:
    """Apply standard type conversions to dataframe columns."""
    if "bse_code" in df.columns:
        df["bse_code"] = pd.to_numeric(df["bse_code"], errors="coerce").astype("Int64")
    if "nse_code" in df.columns:
        df["nse_code"] = df["nse_code"].astype("string")
    if "industry" in df.columns:
        df["industry"] = df["industry"].astype("string")
    if "name" in df.columns:
        df["name"] = df["name"].astype("string")
    return df


@st.cache_data(ttl=CACHE_TTL)
def get_momentum_summary() -> pd.DataFrame:
    """Compute momentum summary with rolling hit counts (1 hour cache TTL)."""
    try:
        today = datetime.date.today()
        with sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES) as conn:
            def _hit_counts(days: int) -> pd.DataFrame:
                since = today - datetime.timedelta(days=days)
                q = f"""
                    SELECT name, COUNT(*) AS hits_{days}
                    FROM {TABLE_HIGHS}
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
                f"""
                SELECT h1.*
                FROM {TABLE_HIGHS} h1
                JOIN (
                    SELECT name, MAX(date) AS max_date
                    FROM {TABLE_HIGHS}
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
        df = _apply_standard_types(df)
        
        return df.reset_index()
    except sqlite3.Error as e:
        st.error(f"Database error fetching momentum summary: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL)
def get_persistence_scores() -> pd.DataFrame:
    """Compute persistence scores for multi-bagger candidate ranking."""
    df = get_momentum_summary()
    if df.empty:
        return df

    # Safe division: avoid zero / NaN
    df["hits_7"] = df["hits_7"].fillna(0).astype(int)
    df["hits_30"] = df["hits_30"].fillna(0).astype(int)
    df["hits_60"] = df["hits_60"].fillna(0).astype(int)

    df["freq_ratio_7_30"] = df.apply(lambda row: row["hits_7"] / max(row["hits_30"], 1), axis=1)
    df["freq_ratio_30_60"] = df.apply(lambda row: row["hits_30"] / max(row["hits_60"], 1), axis=1)
    df["gain_mc"] = df["%_gain_mc"].fillna(0).astype(float)

    df["persistence_score"] = (
        40 * df["freq_ratio_7_30"].clip(upper=10) +
        30 * df["freq_ratio_30_60"].clip(upper=10) +
        30 * (df["gain_mc"].clip(lower=-100, upper=300) / 100)
    )

    df["persistence_score"] = df["persistence_score"].clip(lower=0).round(2)

    return df.sort_values(by="persistence_score", ascending=False).reset_index(drop=True)


@st.cache_data(ttl=CACHE_TTL)
def get_frequency_timeline(stock_name: str, weeks: int = 12) -> pd.DataFrame:
    """Get weekly 52W-high frequency trend for a given stock."""
    df = get_historical_market_cap()
    if df.empty or "date" not in df.columns:
        return pd.DataFrame()

    stock_df = df[df["name"].astype(str).str.lower() == str(stock_name).strip().lower()].copy()
    if stock_df.empty:
        return pd.DataFrame()

    stock_df["week"] = stock_df["date"].dt.to_period("W").dt.start_time
    weekly = (
        stock_df.groupby("week").agg(
            frequency=("date", "count"),
            market_cap_last=("market_cap", "last")
        ).reset_index()
    )

    weekly = weekly.sort_values("week").tail(weeks)
    weekly["week"] = pd.to_datetime(weekly["week"])  # datetime index for plotting

    return weekly


@st.cache_data(ttl=CACHE_TTL)
def get_historical_market_cap() -> pd.DataFrame:
    """Fetch historical market cap data with caching (TTL from config)."""
    try:
        with sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES) as conn:
            df = pd.read_sql(f"SELECT * FROM {TABLE_HIGHS}", conn)
        
        df["date"] = pd.to_datetime(df["date"])
        df = _apply_standard_types(df)
        return df
    except sqlite3.Error as e:
        st.error(f"Database error fetching historical market cap: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL)
def get_all_dates() -> list[datetime.date]:
    """Fetch all distinct dates with caching (TTL from config)."""
    try:
        with sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES) as conn:
            df = pd.read_sql(f"SELECT DISTINCT date FROM {TABLE_HIGHS} ORDER BY date", conn)
        return pd.to_datetime(df["date"]).dt.date.tolist()
    except sqlite3.Error as e:
        st.error(f"Database error fetching dates: {e}")
        return []


@st.cache_data(ttl=CACHE_TTL)
def get_data_for_date(selected_date: str | datetime.date) -> pd.DataFrame:
    """Fetch data for a specific date with caching (TTL from config)."""
    try:
        with sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES) as conn:
            df = pd.read_sql(f"SELECT * FROM {TABLE_HIGHS} WHERE date = ?", conn, params=(selected_date,))
        return _apply_standard_types(df)
    except sqlite3.Error as e:
        st.error(f"Database error fetching data for {selected_date}: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL)
def get_sparkline_data() -> pd.DataFrame:
    """Fetch sparkline data with caching (TTL from config)."""
    try:
        with sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES) as conn:
            df = pd.read_sql(f"SELECT name, date FROM {TABLE_HIGHS}", conn)
        df["date"] = pd.to_datetime(df["date"])
        df["value"] = 1  # presence flag
        return df
    except sqlite3.Error as e:
        st.error(f"Database error fetching sparkline data: {e}")
        return pd.DataFrame()

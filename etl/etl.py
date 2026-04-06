"""
etl.py

Processes CSV exports from Screener.in and populates highs.db.
Supports incremental loading (default) and full rebuild.

Run:
    python etl/etl.py                  # incremental from screener_downloads/
    python etl/etl.py --rebuild        # wipe and reload from archive + live
    python etl/etl.py --source archive # load from __screener_downloads/ only
"""

import argparse
import datetime
import logging
import os
import shutil
import sqlite3
import sys
from pathlib import Path

import pandas as pd

# Make root-level config and db_utils importable from this subfolder
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import (  # noqa: E402
    ARCHIVE_DIR,
    COLUMN_ALIASES,
    DB_PATH,
    DOWNLOAD_DIR,
    ETL_JOBS,
    ETL_LOG_FILE,
    LOG_DATE_FORMAT,
    LOG_FORMAT,
    ensure_directories_exist,
)
# ── Logging ───────────────────────────────────────────────────────────────────

log = logging.getLogger("ETL")
log.setLevel(logging.INFO)
if log.hasHandlers():
    log.handlers.clear()

_file_handler = logging.FileHandler(ETL_LOG_FILE)
_file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
log.addHandler(_file_handler)

_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
log.addHandler(_console_handler)

import datetime as _dt
sqlite3.register_adapter(_dt.date, lambda d: d.isoformat())
sqlite3.register_converter("DATE", lambda s: _dt.date.fromisoformat(s.decode("utf-8")))
del _dt

JOBS = ETL_JOBS


# ── Helpers ───────────────────────────────────────────────────────────────────

def normalize(col: str) -> str:
    """Normalise a CSV column name to a DB-safe identifier."""
    return (
        col.strip()
           .lower()
           .replace(" ", "_")
           .replace("/", "")
           .replace("%", "pct")
           .replace("(", "")
           .replace(")", "")
           .replace(".", "")
    )


def get_superset_columns(folder: Path) -> set:
    """Scan all CSVs in folder and return the union of normalised column names."""
    all_cols: set = set()
    for f in folder.glob("*.csv"):
        try:
            df = pd.read_csv(f, engine="python", nrows=1)
            for col in df.columns:
                norm = normalize(col)
                all_cols.add(COLUMN_ALIASES.get(norm, norm))
        except Exception as exc:
            log.warning("Skipping bad file %s: %s", f.name, exc)
    return all_cols


def evolve_table_schema(
    conn: sqlite3.Connection, df: pd.DataFrame, allowed_cols: set, table_name: str
) -> None:
    """Add any new columns to the table that appear in df but not yet in the schema."""
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}
    for col in df.columns:
        n = COLUMN_ALIASES.get(normalize(col), normalize(col))
        if n not in allowed_cols or n in existing:
            continue
        dtype = "TEXT" if df[col].dtype == object else "REAL"
        try:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {n} {dtype}")
            log.info("[%s] Added column: %s (%s)", table_name, n, dtype)
        except Exception as exc:
            log.error("[%s] Error adding column %s: %s", table_name, n, exc)
    conn.commit()


# ── Core ingestion ────────────────────────────────────────────────────────────

def ingest_csv_folder(source_path: Path, table_name: str, processed_table: str) -> None:
    """Load all unprocessed CSVs in source_path into table_name."""
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)

    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            date DATE, name TEXT, first_seen_date DATE, first_market_cap REAL
        )
    """)
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {processed_table} (date TEXT PRIMARY KEY)
    """)
    conn.commit()

    allowed_cols = get_superset_columns(source_path)

    for csv_file in sorted(source_path.glob("*.csv")):
        date_str = csv_file.stem.split("_")[-1]
        try:
            file_date = datetime.date.fromisoformat(date_str)
        except ValueError:
            log.warning("[%s] Skipping file with invalid date: %s", table_name, csv_file.name)
            continue

        if conn.execute(f"SELECT 1 FROM {processed_table} WHERE date = ?", (date_str,)).fetchone():
            log.info("[%s] Already processed: %s", table_name, csv_file.name)
            continue

        log.info("[%s] Processing: %s", table_name, csv_file.name)
        try:
            df = pd.read_csv(csv_file, engine="python")
        except Exception as exc:
            log.error("[%s] Failed reading %s: %s", table_name, csv_file.name, exc)
            continue

        df.columns = df.columns.str.strip()
        df["date"] = file_date
        evolve_table_schema(conn, df, allowed_cols, table_name)

        failed = False
        conn.execute("BEGIN")
        for _, row in df.iterrows():
            name = row.get("Name")
            if pd.isna(name):
                continue

            mc_raw = row.get("Market Capitalization") or row.get("market_cap") or row.get("Market cap")
            try:
                mc = float(mc_raw)
            except (ValueError, TypeError):
                continue

            result = conn.execute(
                f"SELECT date, CAST(market_cap AS REAL) FROM {table_name} "
                "WHERE name = ? ORDER BY date ASC, rowid ASC LIMIT 1",
                (name,),
            ).fetchone()
            first_seen_date, first_market_cap = result if result else (file_date, mc)

            row_data = {}
            for k, v in row.items():
                n = COLUMN_ALIASES.get(normalize(k), normalize(k))
                if n in allowed_cols:
                    row_data[n] = v
            row_data.update({
                "date": file_date,
                "name": name,
                "first_seen_date": first_seen_date,
                "first_market_cap": first_market_cap,
            })

            cols = ", ".join(row_data.keys())
            placeholders = ", ".join(["?"] * len(row_data))
            try:
                conn.execute(f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})", list(row_data.values()))
            except Exception as exc:
                log.error("[%s] Error inserting %s: %s", table_name, name, exc)
                failed = True
                break

        if failed:
            conn.rollback()
            log.error("[%s] Rolled back — leaving unprocessed: %s", table_name, date_str)
            continue

        conn.execute(f"INSERT INTO {processed_table} (date) VALUES (?)", (date_str,))
        conn.commit()
        log.info("[%s] Done: %s", table_name, date_str)

    conn.close()


def move_to_archive(source_root: Path) -> None:
    """Move processed CSVs from source_root into the archive directory."""
    if source_root.resolve() == Path(ARCHIVE_DIR).resolve():
        log.info("Source is already archive — skipping move step.")
        return
    for job in JOBS:
        src = source_root / job["subfolder"]
        dst = Path(ARCHIVE_DIR) / job["subfolder"]
        if not src.exists():
            continue
        dst.mkdir(parents=True, exist_ok=True)
        for f in src.glob("*.csv"):
            try:
                shutil.move(str(f), str(dst / f.name))
                log.info("Archived: %s", f.name)
            except Exception as exc:
                log.error("Failed to archive %s: %s", f.name, exc)


def rebuild_database() -> None:
    db_file = Path(DB_PATH)
    if db_file.exists():
        db_file.unlink()
        log.info("Deleted existing database: %s", db_file)


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load Screener CSV exports into highs.db.")
    parser.add_argument(
        "--source", choices=["live", "archive"], default=None,
        help="live=screener_downloads (default), archive=__screener_downloads",
    )
    parser.add_argument(
        "--rebuild", action="store_true",
        help="Delete highs.db and reload from archive then live.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_directories_exist()

    if args.source == "archive":
        source_roots = [Path(ARCHIVE_DIR)]
    elif args.rebuild:
        source_roots = [Path(ARCHIVE_DIR), Path(DOWNLOAD_DIR)]
    else:
        source_roots = [Path(DOWNLOAD_DIR)]

    log.info("=" * 60)
    log.info("ETL starting | sources=%s | rebuild=%s", source_roots, args.rebuild)
    log.info("=" * 60)

    try:
        if args.rebuild:
            rebuild_database()

        for root in source_roots:
            log.info("Source root: %s", root)
            for job in JOBS:
                folder = root / job["subfolder"]
                if not folder.exists():
                    log.warning("Folder not found: %s", folder)
                    continue
                ingest_csv_folder(folder, job["table"], job["processed"])
            move_to_archive(root)

        log.info("=" * 60)
        log.info("ETL complete")
        log.info("=" * 60)

    except Exception as exc:
        log.error("ETL failed: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
daily_screen_exports.py

Fetches the three Screener.in screens as CSV files and saves them into
screener_downloads/<subfolder>/screener_YYYY-MM-DD.csv.

Credentials are read from (in order of priority):
  1. Environment variables: SCREENER_USERNAME, SCREENER_PASSWORD
  2. config.local.ini [credentials] username / password

Run:
    python etl/daily_screen_exports.py
"""

import configparser
import os
import sys
import time
from datetime import datetime
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

# Make root-level config importable from this subfolder
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import DOWNLOAD_DIR, ensure_directories_exist  # noqa: E402

BASE_URL = "https://www.screener.in"

SCREENS = [
    {"title": "52WeekHigh5%",          "id": "2702802", "folder": "52weekhigh"},
    {"title": "atleast50downfromhigh",  "id": "2984566", "folder": "downfromhigh"},
    {"title": "The5To50ClubFromTop",    "id": "2985269", "folder": "5to50club"},
]


def load_credentials() -> tuple[str, str]:
    """Return (username, password) from env or config.local.ini."""
    username = os.getenv("SCREENER_USERNAME", "")
    password = os.getenv("SCREENER_PASSWORD", "")
    if username and password:
        return username, password

    local_config = Path(__file__).resolve().parent.parent / "config.local.ini"
    if not local_config.exists():
        raise RuntimeError(
            "No credentials found. Set SCREENER_USERNAME / SCREENER_PASSWORD env vars, "
            "or create config.local.ini (copy config.example.ini)."
        )
    cfg = configparser.ConfigParser()
    cfg.read(local_config)
    username = cfg.get("credentials", "username", fallback="").strip()
    password = cfg.get("credentials", "password", fallback="").strip()
    if not username or not password:
        raise RuntimeError("config.local.ini is missing [credentials] username / password.")
    return username, password


def _make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": BASE_URL,
    })
    return session


def login(session: requests.Session, username: str, password: str) -> None:
    login_url = f"{BASE_URL}/login/"
    resp = session.get(login_url, timeout=15)
    resp.raise_for_status()
    csrf = session.cookies.get("csrftoken")
    headers = {"X-CSRFToken": csrf, "Referer": login_url} if csrf else {}
    resp = session.post(
        login_url,
        data={"username": username, "password": password},
        headers=headers,
        allow_redirects=True,
        timeout=15,
    )
    resp.raise_for_status()
    if "login" in resp.url:
        raise RuntimeError("Login failed — check credentials or account status.")
    print("Login successful.")


def fetch_screen_csv(session: requests.Session, screen_id: str) -> pd.DataFrame:
    url = f"{BASE_URL}/api/export/screen/{screen_id}/"
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    return pd.read_csv(StringIO(resp.text))


def main() -> None:
    ensure_directories_exist()
    username, password = load_credentials()
    session = _make_session()
    login(session, username, password)

    date_str = datetime.today().strftime("%Y-%m-%d")

    for screen in SCREENS:
        print(f"\nFetching: {screen['title']}")
        try:
            df = fetch_screen_csv(session, screen["id"])
            dest = DOWNLOAD_DIR / screen["folder"]
            dest.mkdir(parents=True, exist_ok=True)
            csv_path = dest / f"screener_{date_str}.csv"
            df.to_csv(csv_path, index=False, encoding="utf-8")
            print(f"  Saved {len(df)} rows → {csv_path}")
        except Exception as exc:
            print(f"  Failed: {exc}")
        time.sleep(1)

    print("\nDone.")


if __name__ == "__main__":
    main()

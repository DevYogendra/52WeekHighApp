"""
screener_fetch.py — fetch public company data from screener.in (no login required).

Rate-limited to 1 request/second to be a polite client.
Results are cached in-process so repeated calls for the same symbol are free.

Public API:
  search_companies(query)              -> list[dict]
  fetch_company_data(symbol, ...)      -> CompanyData
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from functools import lru_cache

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.screener.in"
_MIN_INTERVAL = 1.0  # seconds between requests
_last_request_time: float = 0.0

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def _throttled_get(url: str, timeout: int = 15) -> requests.Response:
    """GET with a 1 req/s rate limit."""
    global _last_request_time
    elapsed = time.monotonic() - _last_request_time
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    resp = requests.get(url, headers=_HEADERS, timeout=timeout)
    _last_request_time = time.monotonic()
    return resp


@dataclass
class CompanyData:
    symbol: str
    name: str
    current_price: float | None = None
    stock_pe: float | None = None
    roce_current: float | None = None
    roe_current: float | None = None
    market_cap_cr: float | None = None
    book_value: float | None = None
    eps_current: float | None = None
    eps_cagr_pct: float | None = None        # annualised EPS growth over history
    roce_history: dict[str, float] = field(default_factory=dict)
    eps_history: dict[str, float] = field(default_factory=dict)
    net_profit_history: dict[str, float] = field(default_factory=dict)
    error: str | None = None


@lru_cache(maxsize=64)
def search_companies(query: str) -> tuple[dict, ...]:
    """Return cached tuple of {id, name, symbol, url} dicts matching query."""
    url = f"{BASE_URL}/api/company/search/?q={requests.utils.quote(query)}"
    try:
        resp = _throttled_get(url)
        resp.raise_for_status()
        out = []
        for item in resp.json():
            parts = item.get("url", "").strip("/").split("/")
            symbol = parts[1] if len(parts) >= 2 else ""
            out.append({
                "id": item.get("id"),
                "name": item.get("name", ""),
                "symbol": symbol,
                "url": item.get("url", ""),
            })
        return tuple(out)
    except Exception as exc:
        return ({"error": str(exc)},)


def _parse_number(text: str) -> float | None:
    """Strip ₹, commas, %, Cr. and return float."""
    cleaned = re.sub(r"[₹,\s]", "", text)
    cleaned = cleaned.replace("Cr.", "").replace("%", "").strip()
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _parse_top_ratios(soup: BeautifulSoup) -> dict[str, float | None]:
    """
    Extract key ratios from the #top-ratios list.
    Values may sit directly in .value text OR inside a nested .number span
    (screener.in uses both patterns depending on the company/page).
    """
    out: dict[str, float | None] = {}
    ratios_ul = soup.find(id="top-ratios")
    if not ratios_ul:
        return out
    for li in ratios_ul.find_all("li"):
        name_el = li.find(class_="name")
        if not name_el:
            continue
        key = name_el.get_text(strip=True)
        # Prefer the nested .number span; fall back to full .value text
        num_el = li.find(class_="number")
        val_el = li.find(class_="value")
        raw = (num_el or val_el)
        out[key] = _parse_number(raw.get_text(strip=True)) if raw else None
    return out


def _parse_table_rows(section) -> tuple[list[str], list[dict]]:
    """Return (year_headers, rows) from a screener section table."""
    if not section:
        return [], []
    table = section.find("table")
    if not table:
        return [], []
    rows = table.find_all("tr")
    if not rows:
        return [], []

    headers: list[str] = []
    data_rows: list[dict] = []
    for i, row in enumerate(rows):
        cells = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
        if not cells:
            continue
        if i == 0:
            headers = cells[1:]
        else:
            label = cells[0].rstrip("+").strip()
            data_rows.append({"__label__": label, **dict(zip(headers, cells[1:]))})
    return headers, data_rows


def _eps_cagr(history: dict[str, float]) -> float | None:
    """
    Annualised EPS CAGR from first to last positive value in history.
    Returns None if fewer than 2 positive values or sign changes dominate.
    """
    positives = [(k, v) for k, v in history.items() if v and v > 0]
    if len(positives) < 2:
        return None
    first_val = positives[0][1]
    last_val = positives[-1][1]
    n_years = max(len(positives) - 1, 1)
    cagr = (last_val / first_val) ** (1 / n_years) - 1
    # Sanity cap: ignore implausible values from single-period spikes
    if cagr > 2.0 or cagr < -0.5:
        return None
    return round(cagr * 100, 1)


@lru_cache(maxsize=64)
def fetch_company_data(symbol: str, consolidated: bool = True) -> CompanyData:
    """Fetch and parse company data. Results are cached for the process lifetime."""
    variant = "consolidated" if consolidated else "standalone"
    url = f"{BASE_URL}/company/{symbol}/{variant}/"
    cd = CompanyData(symbol=symbol, name=symbol)

    try:
        resp = _throttled_get(url)
        if resp.status_code == 404 and consolidated:
            resp = _throttled_get(f"{BASE_URL}/company/{symbol}/")
        resp.raise_for_status()
    except Exception as exc:
        cd.error = str(exc)
        return cd

    soup = BeautifulSoup(resp.text, "html.parser")

    h1 = soup.find("h1")
    if h1:
        cd.name = h1.get_text(strip=True)

    top = _parse_top_ratios(soup)
    cd.current_price = top.get("Current Price")
    cd.stock_pe = top.get("Stock P/E")
    cd.roce_current = top.get("ROCE")
    cd.roe_current = top.get("ROE")
    cd.book_value = top.get("Book Value")
    cd.market_cap_cr = top.get("Market Cap")

    if cd.current_price and cd.stock_pe and cd.stock_pe > 0:
        cd.eps_current = round(cd.current_price / cd.stock_pe, 2)

    # Historical ROCE
    ratios_section = soup.find(id="ratios")
    years, ratio_rows = _parse_table_rows(ratios_section)
    for row in ratio_rows:
        if "ROCE" in row.get("__label__", ""):
            for yr in years:
                val = _parse_number(row.get(yr, ""))
                if val is not None:
                    cd.roce_history[yr] = val

    # EPS and Net Profit (P&L has its own year columns)
    pl_section = soup.find(id="profit-loss")
    pl_years, pl_rows = _parse_table_rows(pl_section)
    for row in pl_rows:
        label = row.get("__label__", "")
        if label == "EPS in Rs":
            for yr in pl_years:
                val = _parse_number(row.get(yr, ""))
                if val is not None:
                    cd.eps_history[yr] = val
            if cd.eps_history:
                cd.eps_current = list(cd.eps_history.values())[-1]
        elif "Net Profit" in label:
            for yr in pl_years:
                val = _parse_number(row.get(yr, ""))
                if val is not None:
                    cd.net_profit_history[yr] = val

    cd.eps_cagr_pct = _eps_cagr(cd.eps_history)
    return cd

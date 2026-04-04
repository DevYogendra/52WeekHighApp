"""
automate.py

Daily pipeline orchestrator — runs in one repo (52WeekHighApp).

Steps:
  1. Fetch today's Screener.in CSVs  (daily_screen_exports.py)
  2. Load CSVs into highs.db          (etl.py)
  3. Git pull / add / commit / push

Run:
    python etl/automate.py
    python etl/automate.py --skip-downloads   # reuse today's CSVs already on disk
    python etl/automate.py --no-git           # skip git operations
    python etl/automate.py --dev              # skip downloads + git (local testing)

Credentials / config:
    Set SCREENER_USERNAME and SCREENER_PASSWORD as env vars,
    or create config.local.ini (copy config.example.ini).
"""

import argparse
import configparser
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent  # 52WeekHighApp root

# ── Logging ───────────────────────────────────────────────────────────────────

LOG_FILE = _ROOT / "run.log"


def setup_logging() -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S")

    fh = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
    fh.setFormatter(fmt)

    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)

    if root.hasHandlers():
        root.handlers.clear()
    root.addHandler(fh)
    root.addHandler(ch)


# ── Config ────────────────────────────────────────────────────────────────────

def _load_local_config() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    local = _ROOT / "config.local.ini"
    if local.exists():
        cfg.read(local)
    return cfg


_cfg = _load_local_config()
PYTHON_CMD  = _cfg.get("automation", "python_cmd",   fallback=sys.executable)
REPO_BRANCH = _cfg.get("automation", "repo_branch",  fallback="").strip()


# ── Subprocess helper ─────────────────────────────────────────────────────────

def _utf8_env() -> dict:
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


def run(cmd: str, check: bool = True) -> None:
    logging.info("Running: %s", cmd)
    result = subprocess.run(
        cmd, shell=True, cwd=str(_ROOT),
        capture_output=True, text=True, env=_utf8_env(),
    )
    if result.stdout:
        logging.info("[STDOUT]\n%s", result.stdout.rstrip())
    if result.stderr:
        logging.warning("[STDERR]\n%s", result.stderr.rstrip())
    if result.returncode != 0:
        msg = f"Command failed (code {result.returncode}): {cmd}"
        if check:
            logging.error(msg)
            sys.exit(result.returncode)
        logging.info("%s (ignored)", msg)


def get_current_branch() -> str:
    result = subprocess.run(
        "git branch --show-current", shell=True, cwd=str(_ROOT),
        capture_output=True, text=True, env=_utf8_env(),
    )
    return result.stdout.strip()


def ensure_branch(expected: str) -> None:
    if not expected:
        return
    current = get_current_branch()
    if current != expected:
        logging.error("Expected branch '%s' but on '%s'. Aborting.", expected, current)
        sys.exit(1)
    logging.info("On branch '%s' ✓", current)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Daily 52WeekHighApp data pipeline.")
    parser.add_argument("--skip-downloads", action="store_true",
                        help="Skip fetching new CSVs (reuse what's on disk).")
    parser.add_argument("--no-git", action="store_true",
                        help="Skip git pull/add/commit/push.")
    parser.add_argument("--dev", action="store_true",
                        help="Dev mode: skip downloads and git.")
    args = parser.parse_args()

    skip_downloads = args.skip_downloads or args.dev
    skip_git       = args.no_git or args.dev

    logging.info("=" * 60)
    logging.info("Pipeline started at %s", datetime.now().isoformat(timespec="seconds"))
    logging.info("skip_downloads=%s  skip_git=%s", skip_downloads, skip_git)
    logging.info("=" * 60)

    # Step 1 — Fetch CSVs
    if skip_downloads:
        logging.info("Step 1: Skipping downloads.")
    else:
        logging.info("Step 1: Fetching Screener.in exports…")
        run(f"{PYTHON_CMD} etl/daily_screen_exports.py")

    # Step 2 — ETL into highs.db
    logging.info("Step 2: Running ETL…")
    run(f"{PYTHON_CMD} etl/etl.py")

    # Step 3 — Git
    if skip_git:
        logging.info("Step 3: Skipping git operations.")
    else:
        logging.info("Step 3: Git operations…")
        ensure_branch(REPO_BRANCH)
        run("git pull")
        run("git add *")
        run('git commit -m "Today"', check=False)
        run("git push")

    logging.info("=" * 60)
    logging.info("Pipeline complete.")
    logging.info("=" * 60)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    setup_logging()
    main()

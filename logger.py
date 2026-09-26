"""
logger.py
---------
Handles all logging:
  - Writes one row per trade attempt to logs/trades.csv
  - Recomputes summary.json (win rate, loss rate, etc.) after every trade
  - Pushes the logs folder to GitHub (if enabled in config.py)

You should not need to edit this file.
"""

import os
import csv
import json
import subprocess
from datetime import datetime, timezone

import config

CSV_FIELDS = [
    "timestamp_utc",
    "strategy",
    "single_asset",
    "single_side",
    "single_price",
    "combo_price",
    "combo_status",       # quoted / no_quote / void
    "total_cost",
    "expected_roi",
    "decision",            # ENTERED / SKIPPED
    "skip_reason",
    "stop_loss_level",
    "outcome",             # win / loss / pending / n_a
    "net_pnl",
]


def _ensure_log_dir():
    os.makedirs(config.LOG_DIR, exist_ok=True)


def _csv_path():
    return os.path.join(config.LOG_DIR, config.TRADE_LOG_FILE)


def log_trade(row: dict):
    """
    Appends one row to trades.csv. `row` should contain keys matching
    (a subset of) CSV_FIELDS -- missing keys are left blank.
    """
    _ensure_log_dir()
    path = _csv_path()
    file_exists = os.path.isfile(path)

    row = dict(row)  # copy
    row.setdefault("timestamp_utc", datetime.now(timezone.utc).isoformat())

    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in CSV_FIELDS})


def _read_all_trades():
    path = _csv_path()
    if not os.path.isfile(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def recompute_summary():
    """
    Reads the full trade log and writes summary.json with:
      - win rate, loss rate, entry pnl, total trades
      - probability of at least one co-directional outcome being true
    """
    trades = _read_all_trades()
    entered = [t for t in trades if t["decision"] == "ENTERED"]
    wins = [t for t in entered if t["outcome"] == "win"]
    losses = [t for t in entered if t["outcome"] == "loss"]
    decided = wins + losses  # excludes "pending"

    total_trades = len(entered)
    win_rate = (len(wins) / len(decided)) if decided else 0.0
    loss_rate = (len(losses) / len(decided)) if decided else 0.0

    def safe_float(v):
        try:
            return float(v)
        except (ValueError, TypeError):
            return 0.0

    entry_pnl = sum(safe_float(t.get("net_pnl")) for t in entered)

    # Co-directional outcome = combo leg won (i.e. both assets moved the
    # same direction), regardless of which strategy/single leg was used.
    combo_wins = [t for t in entered if t.get("combo_status") == "quoted" and t.get("outcome") == "win"]
    co_directional_rate = (len(combo_wins) / total_trades) if total_trades else 0.0

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_trades": total_trades,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(win_rate, 4),
        "loss_rate": round(loss_rate, 4),
        "entry_pnl": round(entry_pnl, 4),
        "probability_co_directional_outcome": round(co_directional_rate, 4),
    }

    _ensure_log_dir()
    with open(os.path.join(config.LOG_DIR, config.SUMMARY_FILE), "w") as f:
        json.dump(summary, f, indent=2)

    return summary


def push_to_github():
    """
    Commits and pushes the logs folder back into the repo.

    When this runs inside GitHub Actions (which is how this project is
    meant to run -- see SETUP.md), the workflow file itself configures
    git's identity and authentication using GitHub's built-in token, so
    this function just needs to add/commit/push like normal.
    """
    if not config.PUSH_TO_GITHUB:
        return

    try:
        subprocess.run(["git", "add", config.LOG_DIR], check=True)
        subprocess.run(
            ["git", "commit", "-m", config.GIT_COMMIT_MESSAGE],
            check=False,  # don't fail if there's nothing new to commit
        )
        subprocess.run(["git", "push"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"[WARN] GitHub push failed: {e}")

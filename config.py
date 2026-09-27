"""
config.py
---------
All settings for the daemon live here.

IMPORTANT — this repo is PUBLIC:
Your Kalshi API Key ID and private key must NEVER be written into this
file or committed to the repo, since anyone on the internet could see
them. Instead, they are stored as encrypted "GitHub Secrets" and loaded
here from environment variables at run time. See SETUP.md Step 6 for
exactly how to set those secrets up -- you never paste real credentials
into any file in this project.
"""

import os

# ── YOUR KALSHI CREDENTIALS (loaded from GitHub Secrets, never hardcoded) ──
KALSHI_API_KEY_ID = os.environ.get("KALSHI_API_KEY_ID", "")
# The private key's actual PEM text (not a file path) is loaded from a
# secret too, and written to a temp file at run time -- see kalshi_client.py.
KALSHI_PRIVATE_KEY_PEM = os.environ.get("KALSHI_PRIVATE_KEY_PEM", "")

# ── ENVIRONMENT ──────────────────────────────────────────────────────────
# We use REAL market data (real prices, real liquidity) but never place
# real orders. This is "paper trading on live data."
API_BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
# ^ This is the current production endpoint. Do not point this at demo.

# ── MARKETS ──────────────────────────────────────────────────────────────
BTC_SERIES_TICKER = "KXBTC15M"   # Bitcoin 15-minute markets
ETH_SERIES_TICKER = "KXETH15M"   # Ethereum 15-minute markets

# ── COMBO COLLECTION ─────────────────────────────────────────────────────
# The fixed "family name" for the BTC+ETH 15-min combo on Kalshi. This is
# NOT a specific market ticker -- it's used to look up/create the specific
# combo market for today's live windows. Run find_collection_ticker.py
# once to discover this value, then paste it here.
COMBO_COLLECTION_TICKER = "KXMVECROSSCATEGORY-SHARD1-R"

# ── ENTRY RULES ──────────────────────────────────────────────────────────
# Only enter a trade if (single leg price + combo leg price) is at or
# below this amount. Otherwise the trade is SKIPPED (but still logged).
MAX_TOTAL_ENTRY_COST = 0.80

# ── STOP-LOSS RECOVERY LADDER ────────────────────────────────────────────
# The daemon will paper-test EACH of these recovery levels in parallel,
# so you can later see which one performs best. These are dollar prices
# at which a losing single leg is "sold" instead of left to expire at $0.
STOP_LOSS_LEVELS = [0.40, 0.35, 0.30, 0.25, 0.20, 0.15, 0.10, 0.05]

# ── LIQUIDITY MONITORING ──────────────────────────────────────────────────
# How often (in seconds) to check the single-leg order book depth
# during the 15-minute trade window.
DEPTH_POLL_INTERVAL_SECONDS = 30

# ── RFQ (combo pricing) SETTINGS ─────────────────────────────────────────
RFQ_MAX_WAIT_SECONDS = 20        # how long to wait for a maker to quote back
RFQ_CONFIRM_WAIT_SECONDS = 4     # HVM gives makers 3s to confirm; we pad to 4
RFQ_MAX_RETRIES = 2              # how many times to retry a failed/void RFQ
RFQ_CONTRACT_SIZE = 1            # number of contracts per combo RFQ (paper units)

# ── LOGGING ────────────────────────────────────────────────────────────
LOG_DIR = "logs"
TRADE_LOG_FILE = "trades.csv"
SUMMARY_FILE = "summary.json"

# ── GITHUB PUSH ──────────────────────────────────────────────────────────
# If True, the daemon will git add/commit/push the logs folder after
# every run. Requires this folder to already be a git repo with a remote
# set up (see SETUP.md).
PUSH_TO_GITHUB = True
GIT_COMMIT_MESSAGE = "Update trade logs"

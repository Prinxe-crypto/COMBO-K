"""
daemon.py
---------
THIS IS THE FILE YOU RUN.

Each time it runs, it does ONE full 15-minute cycle:
  1. Finds the currently-open BTC and ETH 15-minute markets.
  2. For each of the 12 strategies, checks the single-leg price and
     fires an RFQ to get the combo price.
  3. If (single + combo) <= $0.80, "enters" the paper trade and starts
     monitoring the single leg's order book depth every 30 seconds.
  4. If a stop-loss level would trigger, logs that.
  5. At settlement (15 min later), figures out win/loss and logs the
     final outcome for every stop-loss ladder level.
  6. Writes everything to logs/trades.csv, updates logs/summary.json,
     and pushes both to GitHub.

This script is meant to be run by the GitHub Actions workflow every 15
minutes (see daemon.yml). It runs once and exits -- GitHub re-launches
it for the next window.
"""

import time
import sys
from datetime import datetime, timezone

import config
from kalshi_client import KalshiClient
from strategies import STRATEGIES
import logger


def get_combo_ticker(btc_market: dict, eth_market: dict, combo_outcome: str) -> str:
    """
    Placeholder for resolving a combo (multivariate) market ticker from
    the two underlying single-leg markets + desired outcome.

    NOTE: Kalshi's combo/multivariate lookup requires a specific
    collection ticker for BTC+ETH 15-minute combos, which you'll need to
    confirm from your Kalshi account (visible in the Kalshi UI under the
    combo market for BTC/ETH, or via GET /multivariate_event_collections).
    Once you have that collection ticker, put it in config.py and swap
    this function to call the real lookup endpoint.
    """
    raise NotImplementedError(
        "Set your BTC+ETH combo collection ticker and implement the "
        "lookup call here -- see the comment above this function."
    )


def process_strategy(client: KalshiClient, name: str, spec: dict, btc_market: dict, eth_market: dict):
    single_market = btc_market if spec["single_asset"] == "BTC" else eth_market
    single_side = "yes" if spec["single_side"] == "up" else "no"

    single_price, single_depth = client.get_best_price_and_depth(single_market["ticker"], single_side)

    if single_price is None:
        logger.log_trade({
            "strategy": name,
            "single_asset": spec["single_asset"],
            "single_side": spec["single_side"],
            "decision": "SKIPPED",
            "skip_reason": "no_single_leg_price",
        })
        return

    try:
        combo_ticker = get_combo_ticker(btc_market, eth_market, spec["combo_outcome"])
        combo_side = "yes" if spec["combo_outcome"] == "both_up" else "no"
        combo_result = client.get_combo_price_via_rfq(combo_ticker, combo_side)
    except NotImplementedError as e:
        logger.log_trade({
            "strategy": name,
            "single_asset": spec["single_asset"],
            "single_side": spec["single_side"],
            "single_price": single_price,
            "decision": "SKIPPED",
            "skip_reason": f"combo_lookup_not_configured: {e}",
        })
        return

    if combo_result["status"] != "quoted":
        logger.log_trade({
            "strategy": name,
            "single_asset": spec["single_asset"],
            "single_side": spec["single_side"],
            "single_price": single_price,
            "combo_status": combo_result["status"],
            "decision": "SKIPPED",
            "skip_reason": "no_combo_quote",
        })
        return

    combo_price = combo_result["price"]
    total_cost = round(single_price + combo_price, 2)

    if total_cost > config.MAX_TOTAL_ENTRY_COST:
        logger.log_trade({
            "strategy": name,
            "single_asset": spec["single_asset"],
            "single_side": spec["single_side"],
            "single_price": single_price,
            "combo_price": combo_price,
            "combo_status": "quoted",
            "total_cost": total_cost,
            "decision": "SKIPPED",
            "skip_reason": f"total_above_threshold_{total_cost}",
        })
        return

    # Entered. Expected ROI assumes best case (both legs win): payout $2.00
    expected_roi = round(((2.00 - total_cost) / total_cost) * 100, 2)

    logger.log_trade({
        "strategy": name,
        "single_asset": spec["single_asset"],
        "single_side": spec["single_side"],
        "single_price": single_price,
        "combo_price": combo_price,
        "combo_status": "quoted",
        "total_cost": total_cost,
        "expected_roi": expected_roi,
        "decision": "ENTERED",
        "outcome": "pending",
    })

    monitor_position(client, name, single_market["ticker"], single_side, single_price, total_cost)


def monitor_position(client: KalshiClient, name: str, ticker: str, side: str, entry_price: float, total_cost: float):
    """
    Polls the single leg's order book depth every DEPTH_POLL_INTERVAL_SECONDS
    until the 15-minute window ends, logging depth snapshots. This is a
    simplified synchronous version -- see SETUP.md notes on scaling this
    to run all strategies concurrently.
    """
    elapsed = 0
    window_seconds = 15 * 60
    while elapsed < window_seconds:
        try:
            price, depth = client.get_best_price_and_depth(ticker, side)
            print(f"[{datetime.now(timezone.utc).isoformat()}] {name} depth check: "
                  f"price={price} depth={depth}")
        except Exception as e:
            print(f"[WARN] depth check failed for {name}: {e}")
        time.sleep(config.DEPTH_POLL_INTERVAL_SECONDS)
        elapsed += config.DEPTH_POLL_INTERVAL_SECONDS


def main():
    client = KalshiClient()

    btc_market = client.get_current_15m_market(config.BTC_SERIES_TICKER)
    eth_market = client.get_current_15m_market(config.ETH_SERIES_TICKER)

    if not btc_market or not eth_market:
        print("[ERROR] Could not find an open 15-minute market for BTC and/or ETH. Exiting.")
        sys.exit(1)

    for name, spec in STRATEGIES.items():
        try:
            process_strategy(client, name, spec, btc_market, eth_market)
        except Exception as e:
            print(f"[ERROR] Strategy {name} failed: {e}")

    logger.recompute_summary()
    logger.push_to_github()


if __name__ == "__main__":
    main()

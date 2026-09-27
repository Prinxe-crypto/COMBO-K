"""
test_combo_resolution.py
--------------------------
RUN THIS ONCE to test whether KXMVECROSSCATEGORY-SHARD1-R is really the
right collection ticker for BTC+ETH 15-min crypto combos.

It finds today's live BTC and ETH 15-min markets, then tries to
resolve a combo market ticker through that collection. If it works,
we'll see a real market_ticker printed. If not, we'll see the exact
error Kalshi's API gives us -- which tells us a lot either way.
"""

import json
import config
from kalshi_client import KalshiClient

TEST_COLLECTION_TICKER = "KXMVECROSSCATEGORY-SHARD1-R"

def main():
    client = KalshiClient()

    print("Finding today's live BTC and ETH 15-min markets...\n")
    btc_market = client.get_current_15m_market(config.BTC_SERIES_TICKER)
    eth_market = client.get_current_15m_market(config.ETH_SERIES_TICKER)

    if not btc_market or not eth_market:
        print("[ERROR] Could not find open BTC/ETH 15-min markets right now.")
        return

    print(f"BTC market: {btc_market['ticker']} (event: {btc_market['event_ticker']})")
    print(f"ETH market: {eth_market['ticker']} (event: {eth_market['event_ticker']})")

    selected_markets = [
        {"event_ticker": btc_market["event_ticker"], "market_ticker": btc_market["ticker"], "side": "yes"},
        {"event_ticker": eth_market["event_ticker"], "market_ticker": eth_market["ticker"], "side": "yes"},
    ]

    print(f"\nTrying LOOKUP against collection: {TEST_COLLECTION_TICKER}\n")
    try:
        result = client.lookup_combo_market(TEST_COLLECTION_TICKER, selected_markets)
        print("LOOKUP SUCCEEDED:")
        print(json.dumps(result, indent=2))
        return
    except Exception as e:
        print(f"LOOKUP failed: {e}\n")

    print(f"Trying CREATE against collection: {TEST_COLLECTION_TICKER}\n")
    try:
        result = client.create_combo_market(TEST_COLLECTION_TICKER, selected_markets)
        print("CREATE SUCCEEDED:")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"CREATE also failed: {e}")
        if hasattr(e, "response") and e.response is not None:
            print("\nRaw error response body:")
            print(e.response.text)

if __name__ == "__main__":
    main()

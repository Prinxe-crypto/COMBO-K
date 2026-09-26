⁷"""
find_collection_ticker.py
--------------------------
RUN THIS ONCE, MANUALLY, to find the exact "collection ticker" name for
the BTC+ETH 15-minute combo family on Kalshi.

This checks both the collections listing and the separate multivariate
events endpoint, filtering both down to crypto-related matches.
"""

import json
from kalshi_client import KalshiClient

KEYWORDS = ["BTC", "ETH", "CRYPTO", "BITCOIN", "ETHEREUM", "15M", "15MIN"]

def main():
    client = KalshiClient()
    collections = client.list_multivariate_collections()
    print(f"\nTotal collections on Kalshi: {len(collections)}\n")

    matches = []
    for c in collections:
        haystack = " ".join([
            str(c.get("collection_ticker", "")),
            str(c.get("title", "")),
            str(c.get("series_ticker", "")),
            str(c.get("description", "")),
        ]).upper()
        if any(k in haystack for k in KEYWORDS):
            matches.append(c)

    print(f"Crypto/BTC/ETH-related matches found: {len(matches)}\n")
    for c in matches:
        print("-" * 50)
        print(f"collection_ticker : {c.get('collection_ticker')}")
        print(f"title             : {c.get('title')}")
        print(f"series_ticker     : {c.get('series_ticker')}")
        print(f"description       : {c.get('description')}")

    if not matches:
        print("No matches found in collections. Printing first 5 raw entries so we can see the naming pattern used:\n")
        print(json.dumps(collections[:5], indent=2))

    # Also check the separate /events/multivariate endpoint, in case crypto
    # combos live there instead of in the collections listing.
    print("\n" + "=" * 60)
    print("Checking /events/multivariate (a different endpoint)...")
    print("=" * 60 + "\n")
    events = client.list_multivariate_collections()
    print(f"Total multivariate events found: {len(events)}\n")

    event_matches = []
    for e in events:
        haystack = " ".join([
            str(e.get("event_ticker", "")),
            str(e.get("title", "")),
            str(e.get("series_ticker", "")),
            str(e.get("category", "")),
        ]).upper()
        if any(k in haystack for k in KEYWORDS):
            event_matches.append(e)

    print(f"Crypto/BTC/ETH-related event matches: {len(event_matches)}\n")
    for e in event_matches:
        print("-" * 50)
        print(f"event_ticker  : {e.get('event_ticker')}")
        print(f"title         : {e.get('title')}")
        print(f"series_ticker : {e.get('series_ticker')}")
        print(f"category      : {e.get('category')}")

    if not event_matches:
        print("No matches here either. Printing first 3 raw entries:\n")
        print(json.dumps(events[:3], indent=2))

if __name__ == "__main__":
    main()

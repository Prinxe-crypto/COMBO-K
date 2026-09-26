"""
find_collection_ticker.py
--------------------------
RUN THIS ONCE, MANUALLY, to find the exact "collection ticker" name for
the BTC+ETH 15-minute combo family on Kalshi.

This filters the full list of Kalshi's combo collections down to only
ones that look crypto-related, so we don't have to scroll through 1000+
sports prop-bet collections to find it.
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
        print("No matches found. Printing first 5 raw entries so we can see the naming pattern used:\n")
        print(json.dumps(collections[:5], indent=2))

if __name__ == "__main__":
    main()

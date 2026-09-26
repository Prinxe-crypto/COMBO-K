"""
find_collection_ticker.py
--------------------------
RUN THIS ONCE, MANUALLY, to find the exact "collection ticker" name for
the BTC+ETH 15-minute combo family on Kalshi.

This is NOT part of the daemon's regular 15-minute cycle -- it's a
one-time lookup tool. Run it via its own GitHub Actions workflow
(find_collection_ticker.yml), read the printed list, find the one that
looks like the crypto 15-min combo, then paste that name into config.py
as COMBO_COLLECTION_TICKER.
"""

import json
from kalshi_client import KalshiClient

def main():
    client = KalshiClient()
    collections = client.list_multivariate_collections()

    print(f"\nFound {len(collections)} collection(s):\n")
    for c in collections:
        print("-" * 50)
        print(f"collection_ticker : {c.get('collection_ticker')}")
        print(f"title             : {c.get('title')}")
        print(f"series_ticker     : {c.get('series_ticker')}")
        print(f"description       : {c.get('description')}")

    print("\n\nFULL RAW JSON (in case the above is empty or unclear):\n")
    print(json.dumps(collections, indent=2))

if __name__ == "__main__":
    main()

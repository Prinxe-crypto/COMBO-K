"""
kalshi_client.py
----------------
Handles everything related to talking to Kalshi's real API:
  - Signing requests (Kalshi requires every request to be cryptographically
    signed with your private key — this proves it's really you).
  - Fetching market prices and order books for the single-leg BTC/ETH markets.
  - Resolving combo (multivariate) market tickers.
  - Firing RFQs (Request for Quote) to get a price for the combo leg.

You should not need to edit this file. Everything you'd want to change
lives in config.py.
"""

import time
import base64
import json
import requests
from datetime import datetime, timezone

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

import config


class KalshiClient:
    def __init__(self):
        self.base_url = config.API_BASE_URL
        self.api_key_id = config.KALSHI_API_KEY_ID
        if not self.api_key_id or not config.KALSHI_PRIVATE_KEY_PEM:
            raise RuntimeError(
                "Missing Kalshi credentials. Make sure KALSHI_API_KEY_ID and "
                "KALSHI_PRIVATE_KEY_PEM are set as GitHub Secrets and passed "
                "into the workflow as environment variables (see SETUP.md)."
            )
        self.private_key = self._load_private_key(config.KALSHI_PRIVATE_KEY_PEM)

    # ── AUTH ──────────────────────────────────────────────────────────
    def _load_private_key(self, pem_text: str):
        return serialization.load_pem_private_key(pem_text.encode("utf-8"), password=None)

    def _sign(self, timestamp_ms: str, method: str, path: str) -> str:
        """
        Kalshi requires a signature over: timestamp + method + path
        (NOT the full URL, and NOT query parameters).
        """
        message = f"{timestamp_ms}{method}{path}".encode("utf-8")
        signature = self.private_key.sign(
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH,
            ),
            hashes.SHA256(),
        )
        return base64.b64encode(signature).decode("utf-8")

    def _headers(self, method: str, path: str) -> dict:
        timestamp_ms = str(int(time.time() * 1000))
        # Kalshi signs the FULL path including "/trade-api/v2", not just
        # the part after it -- e.g. "/trade-api/v2/markets", not "/markets".
        # self.base_url already ends in "/trade-api/v2", so we rebuild the
        # full path here for signing purposes only.
        full_path_for_signing = "/trade-api/v2" + path
        signature = self._sign(timestamp_ms, method, full_path_for_signing)
        return {
            "KALSHI-ACCESS-KEY": self.api_key_id,
            "KALSHI-ACCESS-TIMESTAMP": timestamp_ms,
            "KALSHI-ACCESS-SIGNATURE": signature,
            "Content-Type": "application/json",
        }

    def _get(self, path: str, params: dict = None) -> dict:
        headers = self._headers("GET", path)
        resp = requests.get(self.base_url + path, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, body: dict) -> dict:
        headers = self._headers("POST", path)
        resp = requests.post(self.base_url + path, headers=headers, json=body, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _put(self, path: str, body: dict = None) -> dict:
        headers = self._headers("PUT", path)
        resp = requests.put(self.base_url + path, headers=headers, json=body or {}, timeout=10)
        resp.raise_for_status()
        return resp.json()

    # ── SINGLE-LEG MARKET DATA (public order book, read-only) ──────────
    def get_current_15m_market(self, series_ticker: str) -> dict:
        """
        Finds the currently-open 15-minute market for a given series
        (e.g. KXBTC15M), i.e. the one whose window we're inside right now.
        """
        path = "/markets"
        data = self._get(path, params={"series_ticker": series_ticker, "status": "open", "limit": 5})
        markets = data.get("markets", [])
        if not markets:
            return None
        # Return the soonest-closing open market — that's the active 15m window
        markets.sort(key=lambda m: m.get("close_time", ""))
        return markets[0]

    def get_orderbook(self, ticker: str) -> dict:
        """Returns the live public order book for a single-leg market."""
        path = f"/markets/{ticker}/orderbook"
        return self._get(path)

    def get_best_price_and_depth(self, ticker: str, side: str = "yes") -> tuple:
        """
        Returns (best_price_dollars, contracts_available) for a given side
        ('yes' or 'no') of a single-leg market.
        """
        book = self.get_orderbook(ticker).get("orderbook", {})
        levels = book.get(side, [])
        if not levels:
            return None, 0
        # Kalshi order book levels are typically [price_cents, size]
        best_price_cents, size = levels[0][0], levels[0][1]
        return best_price_cents / 100.0, size

    # ── MULTIVARIATE COLLECTIONS (resolving the combo market ticker) ─────
    def list_multivariate_collections(self) -> list:
        """
        Returns ALL combo 'collections' (families) available on Kalshi,
        following pagination via the cursor field until exhausted.
        """
        all_collections = []
        cursor = None
        while True:
            params = {"cursor": cursor} if cursor else None
            data = self._get("/multivariate_event_collections", params=params)
            # Kalshi's real field name is "multivariate_contracts" (confirmed from docs)
            all_collections.extend(data.get("multivariate_contracts", []))
            cursor = data.get("cursor")
            if not cursor:
                break
        return all_collections

    def lookup_combo_market(self, collection_ticker: str, selected_markets: list) -> dict:
        """
        Resolves the specific combo market ticker for a given set of
        underlying markets (e.g. today's live BTC + ETH 15-min windows).
        selected_markets: list of {"event_ticker": ..., "market_ticker": ...}
        Returns {"event_ticker": ..., "market_ticker": ...}
        Raises an HTTP error (404) if this exact combination has never
        been looked up/created before -- in that case, use create_combo_market.
        """
        path = f"/multivariate_event_collections/{collection_ticker}/lookup"
        return self._put(path, {"selected_markets": selected_markets})

    def create_combo_market(self, collection_ticker: str, selected_markets: list) -> dict:
        """
        Same as lookup_combo_market, but creates the combo market fresh if
        it doesn't exist yet. selected_markets here can include a "side"
        field per market (e.g. "yes"/"no") depending on the collection.
        """
        path = f"/multivariate_event_collections/{collection_ticker}"
        return self._post(path, {"selected_markets": selected_markets})

    def resolve_combo_ticker(self, collection_ticker: str, selected_markets: list) -> str:
        """
        Tries lookup first (cheaper/faster); falls back to create if this
        exact combination hasn't been resolved before (404).
        """
        try:
            result = self.lookup_combo_market(collection_ticker, selected_markets)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                result = self.create_combo_market(collection_ticker, selected_markets)
            else:
                raise
        return result["market_ticker"]

    # ── COMBO PRICING VIA RFQ ────────────────────────────────────────────
    def create_rfq(self, combo_ticker: str, contracts: int) -> dict:
        path = "/communications/rfqs"
        body = {"market_ticker": combo_ticker, "contracts_fp": contracts, "rest_remainder": False}
        return self._post(path, body)

    def get_rfq_quotes(self, rfq_id: str) -> list:
        path = f"/communications/rfqs/{rfq_id}/quotes"
        data = self._get(path)
        return data.get("quotes", [])

    def accept_quote(self, rfq_id: str, quote_id: str, side: str) -> dict:
        path = f"/communications/rfqs/{rfq_id}/quotes/{quote_id}/accept"
        return self._put(path, {"side": side})

    def confirm_quote_status(self, rfq_id: str, quote_id: str) -> dict:
        """Checks whether a maker has confirmed an accepted quote yet."""
        path = f"/communications/rfqs/{rfq_id}/quotes/{quote_id}"
        return self._get(path)

    def get_combo_price_via_rfq(self, combo_ticker: str, side: str = "yes") -> dict:
        """
        Fires an RFQ, waits for quotes, and returns pricing info WITHOUT
        accepting anything — used for the "get combo price at entry" step.

        Returns a dict:
          {"status": "quoted", "price": 0.29, "rfq_id": ..., "quote_id": ...}
          {"status": "no_quote"}
        """
        rfq = self.create_rfq(combo_ticker, config.RFQ_CONTRACT_SIZE)
        rfq_id = rfq.get("rfq_id") or rfq.get("id")

        waited = 0
        poll_step = 1
        while waited < config.RFQ_MAX_WAIT_SECONDS:
            quotes = self.get_rfq_quotes(rfq_id)
            if quotes:
                best = min(
                    quotes,
                    key=lambda q: q.get(f"{side}_bid", 999) if q.get(f"{side}_bid", 0) > 0 else 999,
                )
                price_cents = best.get(f"{side}_bid", 0)
                if price_cents > 0:
                    return {
                        "status": "quoted",
                        "price": price_cents / 100.0,
                        "rfq_id": rfq_id,
                        "quote_id": best.get("quote_id"),
                    }
            time.sleep(poll_step)
            waited += poll_step

        return {"status": "no_quote", "rfq_id": rfq_id}

    def try_accept_and_confirm(self, rfq_id: str, quote_id: str, side: str) -> str:
        """
        Attempts to accept a quote and waits to see if the maker confirms.
        Returns one of: "confirmed", "void"
        (In paper mode we never actually want the real fill to matter --
        we just want to know whether it WOULD have confirmed, for logging.)
        """
        self.accept_quote(rfq_id, quote_id, side)
        waited = 0
        while waited < config.RFQ_CONFIRM_WAIT_SECONDS:
            status = self.confirm_quote_status(rfq_id, quote_id)
            if status.get("status") == "confirmed":
                return "confirmed"
            time.sleep(0.5)
            waited += 0.5
        return "void"

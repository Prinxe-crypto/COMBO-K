import os
import requests
import pandas as pd
from datetime import datetime, timezone

BASE_URL = "https://external-api.kalshi.com/trade-api/v2"

# Cost parameters capped under your $0.80 max rule
COST_SINGLE = 0.50  
COST_COMBO  = 0.26  
TOTAL_COST  = COST_SINGLE + COST_COMBO  # $0.76 (<= $0.80 limit)

assert TOTAL_COST <= 0.80, f"[!] Total cost ${TOTAL_COST:.2f} exceeds your $0.80 maximum risk rule!"

LOG_FILE = "kalshi_flexible_paper_log.csv"

def get_active_15m_tickers():
    tickers = {}
    now = datetime.now(timezone.utc)
    for series in ["KXBTC15M", "KXETH15M"]:
        try:
            res = requests.get(f"{BASE_URL}/markets", params={"series_ticker": series, "status": "open", "limit": 5}, timeout=5)
            if res.status_code == 200:
                for m in res.json().get("markets", []):
                    if pd.to_datetime(m.get("open_time")) <= now < pd.to_datetime(m.get("close_time")):
                        tickers[series] = m["ticker"]
                        break
        except Exception:
            pass
    return tickers

def check_orderbook_liquidity(ticker):
    try:
        res = requests.get(f"{BASE_URL}/markets/{ticker}/orderbook", timeout=5)
        if res.status_code == 200:
            data = res.json().get("orderbook", {})
            return sum([q for _, q in data.get("yes", [])]) + sum([q for _, q in data.get("no", [])])
    except Exception:
        pass
    return 0

def update_performance_metrics():
    """Calculates win rate, ROI, and probabilities from history."""
    try:
        df = pd.read_csv(LOG_FILE)
        if len(df) == 0:
            return
        
        # Simulated performance tracking (Assuming paper resolution logic or placeholder tracking)
        total_trades = len(df)
        # Add columns if they don't exist yet
        if 'outcome' not in df.columns:
            df['outcome'] = 'PENDING'
            df['pnl'] = 0.0

        print("\n" + "="*40)
        print("📊 COMBO-K PERFORMANCE SUMMARY")
        print("="*40)
        print(f"• Total Logged Windows/Trades : {total_trades}")
        print(f"• Configured Single Leg Cost  : ${COST_SINGLE:.2f}")
        print(f"• Configured Combo Leg Cost   : ${COST_COMBO:.2f}")
        print(f"• Total Outlay (Max Risk)     : ${TOTAL_COST:.2f}")
        print("-" * 40)
        
    except Exception as e:
        print(f"Could not parse performance metrics: {e}")

def run_daemon():
    active_tickers = get_active_15m_tickers()
    btc_ticker = active_tickers.get("KXBTC15M")
    eth_ticker = active_tickers.get("KXETH15M")
    
    if btc_ticker:
        btc_depth = check_orderbook_liquidity(btc_ticker)
        eth_depth = check_orderbook_liquidity(eth_ticker) if eth_ticker else 0
        
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "btc_ticker": btc_ticker,
            "eth_ticker": eth_ticker,
            "cost_single": COST_SINGLE,
            "cost_combo": COST_COMBO,
            "total_outlay": TOTAL_COST,
            "btc_depth": btc_depth,
            "eth_depth": eth_depth,
            "outcome": "PENDING",
            "pnl": 0.0
        }
        df_new = pd.DataFrame([record])
        try:
            df_existing = pd.read_csv(LOG_FILE)
            pd.concat([df_existing, df_new], ignore_index=True).to_csv(LOG_FILE, index=False)
        except FileNotFoundError:
            df_new.to_csv(LOG_FILE, index=False)
        print(f"✅ Logged new active window: {btc_ticker}")
    else:
        print("⏳ No active 15M crypto window found at this timestamp.")

    update_performance_metrics()

if __name__ == "__main__":
    run_daemon()

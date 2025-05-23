import time
import argparse
import numpy as np
import pandas as pd
from utils import get_config
from websocket_manager import WebsocketManager
from market_order import place_market_order

# === パラメータ設定（最適化済） ===
WINDOW = 30
BB_TP = 0.015
BB_SL = 0.005
SPIKE_TP = 0.01
SPIKE_SL = 0.005
TREND_TP = 0.015
TREND_SL = 0.01

Z_SCORE_INTERVAL = 300  # 5分ごとに評価

# === State management ===
prices = []
position = None
entry_price = 0.0
entry_time = 0.0
last_check_time = 0
active_tp = 0.0
active_sl = 0.0
max_hold = 0
bars_held = 0
strategy_label = ""

# === Calculation functions ===
def calculate_zscore(prices, window):
    series = pd.Series(prices[-window:])
    if len(series) < window or series.std() == 0:
        return 0.0
    return (series.iloc[-1] - series.mean()) / series.std()

def calculate_sma(prices, period):
    if len(prices) < period:
        return None
    return pd.Series(prices[-period:]).mean()

# === WebSocket handling ===
def on_allmids(ws_msg, coin, sz):
    global prices, position, entry_price, entry_time
    global last_check_time, active_tp, active_sl, max_hold, bars_held, strategy_label

    now = time.time()
    if now - last_check_time < Z_SCORE_INTERVAL:
        return
    last_check_time = now

    try:
        mids = ws_msg["data"]["mids"]
        price = float(mids.get("HYPE", 0))

        if price == 0:
            print("⚠️ Invalid HYPE price")
            return

        prices.append(price)
        if len(prices) > WINDOW:
            prices = prices[-WINDOW:]

        z = calculate_zscore(prices, WINDOW)
        sma_short = calculate_sma(prices, 20)
        sma_long = calculate_sma(prices, 60)

        sma_short_str = f"{sma_short:.6f}" if sma_short is not None else "N/A"
        sma_long_str = f"{sma_long:.6f}" if sma_long is not None else "N/A"
        print(f"\n📉 Price: {price:.6f} | Z: {z:.3f} | SMA20: {sma_short_str}, SMA60: {sma_long_str}")

        # === Exit Check ===
        if position:
            pnl = (price - entry_price) / entry_price if position == "long" else (entry_price - price) / entry_price
            bars_held += 1
            if pnl >= active_tp or pnl <= -active_sl or bars_held >= max_hold:
                print(f"💰 Exit ({strategy_label}) | PnL: {pnl*100:.2f}%")
                place_market_order(coin="HYPE", is_buy=(position == "short"), sz=sz)
                position = None
                entry_price = 0.0
                bars_held = 0
                return

        # === Entry Check ===
        if not position:
            # Bollinger Band Reversal
            mid = calculate_sma(prices, 20)
            std = pd.Series(prices[-20:]).std()
            lower = mid - 2 * std if mid and std else None
            if lower and price < lower:
                print("🎯 Entry: BB Reversal")
                place_market_order(coin="HYPE", is_buy=True, sz=sz)
                position = "long"
                entry_price = price
                active_tp = BB_TP
                active_sl = BB_SL
                max_hold = 3
                bars_held = 0
                strategy_label = "BB Reversal"

            # Spike Rebound
            elif len(prices) >= 2:
                ret = (prices[-1] - prices[-2]) / prices[-2]
                if ret <= -0.02:
                    print("🎯 Entry: Spike Rebound (Long)")
                    place_market_order(coin="HYPE", is_buy=True, sz=sz)
                    position = "long"
                    entry_price = price
                    active_tp = SPIKE_TP
                    active_sl = SPIKE_SL
                    max_hold = 3
                    bars_held = 0
                    strategy_label = "Spike Long"
                elif ret >= 0.02:
                    print("🎯 Entry: Spike Rebound (Short)")
                    place_market_order(coin="HYPE", is_buy=False, sz=sz)
                    position = "short"
                    entry_price = price
                    active_tp = SPIKE_TP
                    active_sl = SPIKE_SL
                    max_hold = 3
                    bars_held = 0
                    strategy_label = "Spike Short"

            # Trend Break
            elif sma_short and sma_long:
                if sma_short > sma_long:
                    print("📈 Entry: Trend Break (Long)")
                    place_market_order(coin="HYPE", is_buy=True, sz=sz)
                    position = "long"
                    entry_price = price
                    active_tp = TREND_TP
                    active_sl = TREND_SL
                    max_hold = 4
                    bars_held = 0
                    strategy_label = "Trend Long"
                elif sma_short < sma_long:
                    print("📉 Entry: Trend Break (Short)")
                    place_market_order(coin="HYPE", is_buy=False, sz=sz)
                    position = "short"
                    entry_price = price
                    active_tp = TREND_TP
                    active_sl = TREND_SL
                    max_hold = 4
                    bars_held = 0
                    strategy_label = "Trend Short"

    except Exception as e:
        print(f"❌ Error: {e}")

# === Main process ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sz", type=float, required=True, help="Trading size (e.g., 0.01)")
    args = parser.parse_args()

    print("🚀 Launching Multi-Strategy HYPE Bot")
    base_url = "wss://api.hyperliquid.xyz/ws"
    websocket = WebsocketManager(base_url, lambda msg: on_allmids(msg, "HYPE", args.sz))
    websocket.start()
    sub = {"type": "allMids"}
    websocket.subscribe(sub, lambda msg: on_allmids(msg, "HYPE", args.sz))

    while True:
        time.sleep(5)

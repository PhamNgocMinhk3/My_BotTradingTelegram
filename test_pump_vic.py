"""Debug pump analysis for VICUSDT - find why pump_data is empty"""
import os
import sys
import traceback
import numpy as np

from dotenv import load_dotenv
load_dotenv()

from binance_client import BinanceClient

api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_API_SECRET')
binance = BinanceClient(api_key, api_secret)

symbol = "VICUSDT"
print(f"=== DEBUG PUMP ANALYSIS FOR {symbol} ===\n")

# Step 1: get_klines
print("[1] get_klines 5m...")
try:
    df_5m = binance.get_klines(symbol, '5m', limit=100)
    if df_5m is None:
        print(f"  ❌ df_5m is None!")
    else:
        print(f"  ✅ type={type(df_5m)}, len={len(df_5m)}")
        print(f"  columns={list(df_5m.columns)}")
        print(f"  dtypes:\n{df_5m.dtypes}")
        print(f"  Last row:\n{df_5m.iloc[-1]}")
        print(f"  close dtype: {df_5m['close'].dtype}")
        print(f"  volume dtype: {df_5m['volume'].dtype}")
except Exception as e:
    print(f"  ❌ ERROR: {e}")
    traceback.print_exc()

print("\n[2] get_klines 1h...")
try:
    df_1h = binance.get_klines(symbol, '1h', limit=50)
    if df_1h is None:
        print(f"  ❌ df_1h is None!")
    else:
        print(f"  ✅ type={type(df_1h)}, len={len(df_1h)}")
except Exception as e:
    print(f"  ❌ ERROR: {e}")
    traceback.print_exc()

# Step 2: Test each pump indicator individually
print("\n[3] Volume Spike 5m...")
try:
    if df_5m is not None and len(df_5m) >= 20:
        vol_cur_5m = float(df_5m['volume'].iloc[-1])
        vol_avg_5m = float(df_5m['volume'].rolling(20).mean().iloc[-1])
        vol_spike = vol_cur_5m / vol_avg_5m if vol_avg_5m > 0 else 0
        print(f"  ✅ cur={vol_cur_5m}, avg={vol_avg_5m}, spike={vol_spike:.2f}x")
    else:
        print(f"  ❌ Not enough data: df_5m={df_5m is not None}, len={len(df_5m) if df_5m is not None else 0}")
except Exception as e:
    print(f"  ❌ ERROR: {e}")
    traceback.print_exc()

print("\n[4] Price changes...")
try:
    current_price_raw = float(df_5m['close'].iloc[-1])
    p5m = float(df_5m['close'].iloc[-2])
    p30m = float(df_5m['close'].iloc[-7]) if len(df_5m) >= 7 else p5m
    p1h = float(df_5m['close'].iloc[-13]) if len(df_5m) >= 13 else p5m
    chg_5m = ((current_price_raw - p5m) / p5m) * 100
    chg_30m = ((current_price_raw - p30m) / p30m) * 100
    chg_1h = ((current_price_raw - p1h) / p1h) * 100
    print(f"  ✅ price={current_price_raw}, 5m={chg_5m:+.2f}%, 30m={chg_30m:+.2f}%, 1h={chg_1h:+.2f}%")
except Exception as e:
    print(f"  ❌ ERROR: {e}")
    traceback.print_exc()

print("\n[5] RSI 5m...")
try:
    delta = df_5m['close'].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi_s = 100 - (100 / (1 + rs))
    rsi_5m = float(rsi_s.iloc[-1])
    print(f"  ✅ RSI 5m={rsi_5m:.1f}")
    print(f"  rsi_s type: {type(rsi_s)}, last 5 vals: {[float(x) for x in rsi_s.tail(5)]}")
except Exception as e:
    print(f"  ❌ ERROR: {e}")
    traceback.print_exc()

print("\n[6] OBV...")
try:
    obv_vals = (np.sign(df_5m['close'].diff().fillna(0)) * df_5m['volume']).cumsum()
    obv_now = float(obv_vals.iloc[-1])
    obv_10 = float(obv_vals.iloc[-10]) if len(obv_vals) >= 10 else 0
    print(f"  ✅ OBV now={obv_now:,.0f}, 10ago={obv_10:,.0f}, trend={'INFLOW' if obv_now > obv_10 else 'OUTFLOW'}")
except Exception as e:
    print(f"  ❌ ERROR: {e}")
    traceback.print_exc()

print("\n[7] Buy pressure...")
try:
    greens = sum(1 for i in range(len(df_5m)-20, len(df_5m))
                if float(df_5m['close'].iloc[i]) > float(df_5m['open'].iloc[i]))
    print(f"  ✅ greens={greens}/20, ratio={greens/20*100:.0f}%")
except Exception as e:
    print(f"  ❌ ERROR: {e}")
    traceback.print_exc()

print("\n[8] Order Book...")
try:
    depth = binance.get_order_book(symbol)
    if depth is None:
        print(f"  ❌ depth is None!")
    else:
        print(f"  type={type(depth)}")
        print(f"  keys={list(depth.keys()) if isinstance(depth, dict) else 'NOT DICT'}")
        if isinstance(depth, dict):
            bids = depth.get('bids', [])
            asks = depth.get('asks', [])
            print(f"  bids count={len(bids)}, asks count={len(asks)}")
            if bids:
                print(f"  first bid: {bids[0]}")
            if asks:
                print(f"  first ask: {asks[0]}")
            
            bid_vol = sum(float(b[1]) for b in bids[:20])
            ask_vol = sum(float(a[1]) for a in asks[:20])
            ob_ratio = bid_vol / ask_vol if ask_vol > 0 else 0
            print(f"  ✅ bid_vol={bid_vol:,.0f}, ask_vol={ask_vol:,.0f}, ratio={ob_ratio:.1f}x")
except Exception as e:
    print(f"  ❌ ERROR: {e}")
    traceback.print_exc()

print("\n=== DONE ===")

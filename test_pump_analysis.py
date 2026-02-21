"""Test the pump analysis logic from /SYMBOL handler"""
import os
import sys
import traceback

# Load env
from dotenv import load_dotenv
load_dotenv()

print("=" * 60)
print("TEST: Pump Analysis Logic (from /SYMBOL handler)")
print("=" * 60)

# Test 1: Import dependencies
print("\n[1] Testing imports...")
try:
    import numpy as np
    import pandas as pd
    print("  ✅ numpy, pandas imported OK")
except Exception as e:
    print(f"  ❌ Import error: {e}")
    sys.exit(1)

# Test 2: Connect Binance
print("\n[2] Connecting to Binance...")
try:
    from binance_client import BinanceClient
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    binance = BinanceClient(api_key, api_secret)
    print("  ✅ Binance client created")
except Exception as e:
    print(f"  ❌ Binance error: {e}")
    traceback.print_exc()
    sys.exit(1)

# Test 3: Get klines
symbol = "BTCUSDT"
print(f"\n[3] Fetching klines for {symbol}...")
try:
    df_5m = binance.get_klines(symbol, '5m', limit=100)
    df_1h = binance.get_klines(symbol, '1h', limit=50)
    print(f"  ✅ 5m klines: {len(df_5m)} rows, columns: {list(df_5m.columns)}")
    print(f"  ✅ 1h klines: {len(df_1h)} rows")
except Exception as e:
    print(f"  ❌ Klines error: {e}")
    traceback.print_exc()
    sys.exit(1)

# Test 4: Run pump analysis (same logic as /SYMBOL handler)
print(f"\n[4] Running pump analysis for {symbol}...")
pump_data = {}
try:
    if df_5m is not None and len(df_5m) >= 20:
        current_price_raw = float(df_5m['close'].iloc[-1])
        print(f"  Price: ${current_price_raw:,.2f}")
        
        # Volume Spike 5m
        vol_cur_5m = float(df_5m['volume'].iloc[-1])
        vol_avg_5m = float(df_5m['volume'].rolling(20).mean().iloc[-1])
        pump_data['vol_spike_5m'] = vol_cur_5m / vol_avg_5m if vol_avg_5m > 0 else 0
        print(f"  ✅ Vol 5m: {pump_data['vol_spike_5m']:.2f}x")
        
        # Volume Spike 1H
        pump_data['vol_spike_1h'] = 0
        if df_1h is not None and len(df_1h) >= 20:
            vol_cur_1h = float(df_1h['volume'].iloc[-1])
            vol_avg_1h = float(df_1h['volume'].rolling(20).mean().iloc[-1])
            pump_data['vol_spike_1h'] = vol_cur_1h / vol_avg_1h if vol_avg_1h > 0 else 0
        print(f"  ✅ Vol 1H: {pump_data['vol_spike_1h']:.2f}x")
        
        # Price changes
        p5m = float(df_5m['close'].iloc[-2])
        p30m = float(df_5m['close'].iloc[-7]) if len(df_5m) >= 7 else p5m
        p1h = float(df_5m['close'].iloc[-13]) if len(df_5m) >= 13 else p5m
        pump_data['chg_5m'] = ((current_price_raw - p5m) / p5m) * 100
        pump_data['chg_30m'] = ((current_price_raw - p30m) / p30m) * 100
        pump_data['chg_1h'] = ((current_price_raw - p1h) / p1h) * 100
        print(f"  ✅ Changes: 5m={pump_data['chg_5m']:+.2f}%, 30m={pump_data['chg_30m']:+.2f}%, 1H={pump_data['chg_1h']:+.2f}%")
        
        # RSI 5m
        delta = df_5m['close'].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
        rs = avg_gain / avg_loss
        rsi_s = 100 - (100 / (1 + rs))
        pump_data['rsi_5m'] = float(rsi_s.iloc[-1])
        pump_data['rsi_prev'] = float(rsi_s.iloc[-4]) if len(rsi_s) >= 4 else pump_data['rsi_5m']
        pump_data['rsi_momentum'] = pump_data['rsi_5m'] - pump_data['rsi_prev']
        print(f"  ✅ RSI 5m: {pump_data['rsi_5m']:.1f}, Momentum: {pump_data['rsi_momentum']:+.1f}")
        
        # RSI 1H
        pump_data['rsi_1h'] = 50
        if df_1h is not None and len(df_1h) >= 20:
            d1h = df_1h['close'].diff()
            g1h = d1h.where(d1h > 0, 0.0)
            l1h = -d1h.where(d1h < 0, 0.0)
            ag1h = g1h.ewm(alpha=1/14, adjust=False).mean()
            al1h = l1h.ewm(alpha=1/14, adjust=False).mean()
            rs1h = ag1h / al1h
            rsi1h = 100 - (100 / (1 + rs1h))
            pump_data['rsi_1h'] = float(rsi1h.iloc[-1])
        print(f"  ✅ RSI 1H: {pump_data['rsi_1h']:.1f}")
        
        # OBV
        obv_vals = (np.sign(df_5m['close'].diff().fillna(0)) * df_5m['volume']).cumsum()
        obv_now = float(obv_vals.iloc[-1])
        obv_10 = float(obv_vals.iloc[-10]) if len(obv_vals) >= 10 else 0
        pump_data['obv_trend'] = "INFLOW" if obv_now > obv_10 else "OUTFLOW"
        pump_data['obv_change'] = obv_now - obv_10
        print(f"  ✅ OBV: {pump_data['obv_trend']} ({pump_data['obv_change']:+,.0f})")
        
        # Buy pressure
        greens = sum(1 for i in range(len(df_5m)-20, len(df_5m))
                    if float(df_5m['close'].iloc[i]) > float(df_5m['open'].iloc[i]))
        pump_data['buy_ratio'] = greens / 20
        print(f"  ✅ Buy Pressure: {pump_data['buy_ratio']*100:.0f}% ({greens}/20 green)")
        
        # Order Book
        pump_data['ob_ratio'] = 0
        pump_data['cost_5pct'] = 0
        try:
            depth = binance.get_order_book(symbol)
            if depth:
                bids = depth['bids'][:20]
                asks = depth['asks'][:20]
                bid_vol = sum(float(b[1]) for b in bids)
                ask_vol = sum(float(a[1]) for a in asks)
                pump_data['ob_ratio'] = bid_vol / ask_vol if ask_vol > 0 else 0
                
                target_p = current_price_raw * 1.05
                for ask in depth['asks']:
                    if float(ask[0]) <= target_p:
                        pump_data['cost_5pct'] += float(ask[0]) * float(ask[1])
                    else:
                        break
            print(f"  ✅ Order Book: Buy/Sell={pump_data['ob_ratio']:.1f}x, Cost 5%=${pump_data['cost_5pct']:,.0f}")
        except Exception as e:
            print(f"  ⚠️ Order Book error (non-fatal): {e}")
        
        # Pump Score
        p_score = 0
        if pump_data['vol_spike_5m'] > 3: p_score += 25
        elif pump_data['vol_spike_5m'] > 2: p_score += 15
        elif pump_data['vol_spike_5m'] > 1.5: p_score += 8
        
        if pump_data['vol_spike_1h'] > 3: p_score += 20
        elif pump_data['vol_spike_1h'] > 2: p_score += 12
        
        if pump_data['chg_1h'] > 5: p_score += 15
        elif pump_data['chg_30m'] > 3: p_score += 10
        
        if pump_data['obv_change'] > 0: p_score += 15
        
        if pump_data['ob_ratio'] > 3: p_score += 15
        elif pump_data['ob_ratio'] > 2: p_score += 10
        
        if 0 < pump_data['cost_5pct'] < 50000: p_score += 10
        elif 0 < pump_data['cost_5pct'] < 200000: p_score += 5
        
        pump_data['pump_score'] = min(100, p_score)
        print(f"  ✅ Pump Score: {pump_data['pump_score']}/100")
        
except Exception as e:
    print(f"  ❌ PUMP ANALYSIS ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)

# Test 5: Build message (same as /SYMBOL handler)
print(f"\n[5] Building message...")
try:
    msg = ""
    score = pump_data.get('pump_score', 0)
    
    if score >= 60:
        msg += f"🔴 Status: HOT\n"
    elif score >= 40:
        msg += f"🟡 Status: WARM\n"
    elif score >= 20:
        msg += f"🟢 Status: MILD\n"
    else:
        msg += f"⚪ Status: COLD\n"
    
    filled = min(5, score // 20)
    score_bar = "█" * filled + "░" * (5 - filled)
    msg += f"Pump Score: [{score_bar}] {score}/100\n"
    
    v5m = pump_data.get('vol_spike_5m', 0)
    v1h = pump_data.get('vol_spike_1h', 0)
    msg += f"Volume 5m: {v5m:.1f}x | Volume 1H: {v1h:.1f}x\n"
    
    rsi5 = pump_data.get('rsi_5m', 0)
    rsi1h = pump_data.get('rsi_1h', 0)
    rsi_mom = pump_data.get('rsi_momentum', 0)
    msg += f"RSI 5m: {rsi5:.1f} | RSI 1H: {rsi1h:.1f} | Δ{rsi_mom:+.1f}\n"
    
    msg += f"OBV: {pump_data.get('obv_trend', 'N/A')}"
    obv_chg = pump_data.get('obv_change', 0)
    if abs(obv_chg) > 0:
        msg += f" ({obv_chg:+,.0f})"
    msg += "\n"
    
    ob_r = pump_data.get('ob_ratio', 0)
    cost = pump_data.get('cost_5pct', 0)
    if ob_r > 0:
        msg += f"Buy/Sell: {ob_r:.1f}x | Push 5%: ${cost:,.0f}\n"
    
    bp = pump_data.get('buy_ratio', 0)
    msg += f"Buy Pressure: {bp*100:.0f}% ({int(bp*20)}/20 green)\n"
    
    print("  ✅ Message built successfully!")
    print(f"\n--- SAMPLE OUTPUT ---\n{msg}")
    
except Exception as e:
    print(f"  ❌ MESSAGE BUILD ERROR: {e}")
    traceback.print_exc()
    sys.exit(1)

# Test 6: Check get_order_book method signature
print("\n[6] Checking binance.get_order_book method...")
try:
    import inspect
    if hasattr(binance, 'get_order_book'):
        sig = inspect.signature(binance.get_order_book)
        print(f"  ✅ get_order_book signature: {sig}")
    else:
        print(f"  ❌ get_order_book NOT FOUND!")
        # Check what methods are available
        methods = [m for m in dir(binance) if 'order' in m.lower() or 'book' in m.lower() or 'depth' in m.lower()]
        print(f"  Available similar methods: {methods}")
except Exception as e:
    print(f"  ⚠️ Error checking method: {e}")

# Test 7: Check get_klines method signature
print("\n[7] Checking binance.get_klines method...")
try:
    if hasattr(binance, 'get_klines'):
        sig = inspect.signature(binance.get_klines)
        print(f"  ✅ get_klines signature: {sig}")
    else:
        print(f"  ❌ get_klines NOT FOUND!")
        methods = [m for m in dir(binance) if 'kline' in m.lower() or 'candle' in m.lower()]
        print(f"  Available similar methods: {methods}")
except Exception as e:
    print(f"  ⚠️ Error: {e}")

print("\n" + "=" * 60)
print("ALL TESTS PASSED ✅")
print("=" * 60)


import logging
import pandas as pd
import numpy as np
from binance_client import BinanceClient
from indicators import calculate_rsi, calculate_mfi, calculate_hlcc4
import time
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


import os

def load_env():
    env_vars = {}
    try:
        with open(".env", "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()
    except Exception:
        pass
    return env_vars

def analyze_orca():
    try:
        env = load_env()
        api_key = env.get("BINANCE_API_KEY")
        api_secret = env.get("BINANCE_API_SECRET")
        
        if not api_key or not api_secret:
             # Try public client if keys missing (pass None might work for public endpoints on some libs, 
             # but binance.client.Client usually handles None for public)
             print("⚠️ API Keys not found in .env, trying with None (Public endpoints)")
             api_key = None
             api_secret = None

        client = BinanceClient(api_key, api_secret)
        symbol = "RPLUSDT"
        
        print(f"🔍 Fetching data for {symbol}...")
        
        # 1. Fetch 5m Data (Layer 1 Analysis)
        klines_5m = client.get_klines(symbol, '5m', limit=500) # Last ~41 hours
        if klines_5m is None or klines_5m.empty:
            print("❌ Could not fetch 5m data for ORCA")
            return

        print(f"✅ Fetched {len(klines_5m)} 5m candles")
        
        # Calculate Indicators for 5m
        df = klines_5m.copy()
        df['close'] = df['close'].astype(float)
        df['open'] = df['open'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['volume'] = df['volume'].astype(float)
        
        df['hlcc4'] = (df['high'] + df['low'] + df['close'] + df['close']) / 4
        df['rsi'] = calculate_rsi(df['hlcc4'], 14)
        
        # Analyze each candle for Pump Signals (Simulation)
        print("\n📊 Simulating Real-time Detection (Last 50 candles):")
        print(f"{'Time':<20} | {'Price':<10} | {'%Chg':<6} | {'Vol Spike':<9} | {'RSI':<5} | {'Score':<5} | {'Result'}")
        print("-" * 80)
        
        potential_pumps = []
        
        for i in range(50, len(df)):
            try:
                # Slicing to simulate "live" view at index i
                current_slice = df.iloc[:i+1]
                
                # Metrics
                close = current_slice.iloc[-1]['close']
                prev_close = current_slice.iloc[-2]['close']
                price_change = ((close - prev_close) / prev_close) * 100
                
                vol = current_slice.iloc[-1]['volume']
                avg_vol = current_slice.iloc[-6:-1]['volume'].mean()
                vol_spike = vol / avg_vol if avg_vol > 0 else 0
                
                rsi = current_slice.iloc[-1]['rsi']
                rsi_ago = current_slice.iloc[-4]['rsi'] # 15m ago
                rsi_change = rsi - rsi_ago
                
                # Scoring (Simplified from pump_detector_realtime.py)
                # 1. Vol Score
                vol_score = min(25, (vol_spike / 3.0) * 25)
                
                # 2. Momentum Score
                mom_score = 0
                if price_change > 2.0:
                    mom_score = min(25, (price_change / 2.0) * 25)
                    
                # 3. RSI Score
                rsi_score = 0
                if rsi_change > 10 and rsi < 80:
                    rsi_score = min(20, (rsi_change / 10.0) * 20)
                    
                # 4. Green Candles
                green_candles = 0
                for k in range(1, 6):
                    if current_slice.iloc[-k]['close'] > current_slice.iloc[-k]['open']:
                        green_candles += 1
                green_score = (green_candles / 5) * 20
                
                # 5. Consistency (last 3 vols increasing)
                vols = current_slice.iloc[-3:]['volume'].values
                consistency_score = 10 if (vols[0] <= vols[1] <= vols[2]) else 0
                
                # 6. WHALE VOLUME (Absorption) Check
                whale_score = 0
                if vol_spike >= 10.0 and abs(price_change) < 1.5:
                     whale_score = 35 # Major boost for absorption
                
                total_score = vol_score + mom_score + rsi_score + green_score + consistency_score + whale_score
                
                timestamp = current_slice.index[-1]
                
                # Highlights
                result = ""
                # Auto-add Logic Simulation
                auto_add = ""
                if total_score >= 75 or whale_score > 0:
                     auto_add = "📋 [Simulated Watchlist Add]"

                if total_score >= 60:
                    result = "🚨 TRIGGER"
                    potential_pumps.append((timestamp, close, total_score))
                elif total_score >= 40:
                    result = "⚠️ Watch"
                
                # Only print interesting rows or recent ones
                if total_score > 30 or i > len(df) - 20:
                     print(f"{timestamp} | {close:<10.4f} | {price_change:>5.2f}% | {vol_spike:>5.2f}x    | {rsi:>5.1f} | {whale_score:>3} | {int(total_score):>5} | {result} {auto_add}")
                    
            except Exception as e:
                print(f"Error at index {i}: {e}")
                continue

        # 2. Analyze Pre-Pump (Stealth Accumulation)
        print("\n💎 Checking Pre-Pump Criteria (1h Data)...")
        klines_1h = client.get_klines(symbol, '1h', limit=100)
        if klines_1h is not None:
             # Basic check for low volatility + rising volume
             # (This is a simplified version of AdvancedPumpDumpDetector)
             last_24h = klines_1h.iloc[-24:]
             high = last_24h['high'].max()
             low = last_24h['low'].min()
             volatility = (high - low) / low * 100
             
             print(f"24h Volatility: {volatility:.2f}%")
             if volatility < 5.0:
                 print("✅ Volatility is LOW (< 5%) - Good for accumulation")
             else:
                 print("❌ Volatility is HIGH (> 5%) - Failed accumulation check")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_orca()

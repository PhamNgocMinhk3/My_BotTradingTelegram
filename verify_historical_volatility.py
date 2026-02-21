
import logging
import pandas as pd
from binance_client import BinanceClient
from datetime import datetime, timedelta
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

def main():
    env = load_env()
    client = BinanceClient(env.get("BINANCE_API_KEY"), env.get("BINANCE_API_SECRET"))
    symbol = "RPLUSDT"
    
    print(f"🔍 Analyzing Historical Volatility for {symbol}...")
    
    # We want to check volatility BEFORE the pump started.
    # RPL Pump started around 15:00 - 18:00 on Feb 16
    
    # Get 1h klines covering that period
    klines_1h = client.get_klines(symbol, '1h', limit=500)
    
    # Convert to dataframe
    df = klines_1h.copy()
    
    # Look for the index corresponding to 2026-02-16 14:00
    target_date = "2026-02-16 14:00"
    
    print(f"Target Analysis Time: {target_date}")
    
    # Find the row closest to target
    target_idx = -1
    for i, idx in enumerate(df.index):
        if str(idx).startswith(target_date):
            target_idx = i
            break
            
    if target_idx != -1:
        # Get the 50 candles ENDING at target (Bot uses last 50 candles)
        start_idx = target_idx - 50
        if start_idx >= 0:
            recent = df.iloc[start_idx:target_idx].copy()
            
            # 1. Low Volatility (Price Compression)
            # Bot logic: high_low_range = (recent['high'] - recent['low']) / recent['low']
            # avg_volatility = high_low_range.mean()
            # is_compressed = avg_volatility < 0.025
            
            recent['high'] = recent['high'].astype(float)
            recent['low'] = recent['low'].astype(float)
            recent['close'] = recent['close'].astype(float)
            recent['volume'] = recent['volume'].astype(float)
            recent['open'] = recent['open'].astype(float)
            
            high_low_range = (recent['high'] - recent['low']) / recent['low']
            avg_volatility = high_low_range.mean()
            is_compressed = avg_volatility < 0.025
            
            print(f"\n📊 Bot Logic Analysis at {target_date}:")
            print(f"Avg Candle Volatility: {avg_volatility*100:.3f}% (Threshold: 2.5%)")
            if is_compressed:
                print("✅ PASSED Volatility Check")
            else:
                print("❌ FAILED Volatility Check")

            # 2. Volume Anomalies
            vol_first_half = recent['volume'].iloc[:25].mean()
            vol_second_half = recent['volume'].iloc[25:].mean()
            is_vol_increasing = vol_second_half > vol_first_half * 1.2
            print(f"Volume Ratio: {vol_second_half/vol_first_half:.2f}x (Threshold: 1.2x)")
            
            # 3. Buy Pressure
            green_candles = sum(1 for i in range(len(recent)-20, len(recent))
                              if float(recent['close'].iloc[i]) > float(recent['open'].iloc[i]))
            buy_ratio = green_candles / 20
            print(f"Buy Ratio: {buy_ratio:.2f} (Bonus if > 0.55)")
            
            # Scoring Simulation
            compression_score = max(0, 30 - (avg_volatility * 1200))
            vol_ratio = vol_second_half / vol_first_half if vol_first_half > 0 else 1
            volume_score = min(25, (vol_ratio - 1) * 25)
            buy_bonus = int(min(10, (buy_ratio - 0.5) * 40)) if buy_ratio > 0.5 else 0
            
            total_score = compression_score + volume_score + buy_bonus 
            # (Ignoring OBV/RSI for simplicity or add if needed, but these are main drivers)
            
            print(f"\n--- SCORING ---")
            print(f"Compression Score: {compression_score:.1f}/30")
            print(f"Volume Score:      {volume_score:.1f}/25")
            print(f"Buy Bonus:         {buy_bonus}/10")
            print(f"Est Total Score:   {total_score:.1f} (Need 75+)")
            
        else:
            print("Not enough history for 50 candle calculation.")
    else:
        print(f"Could not find timestamp {target_date} in data.")
        print("First timestamp:", df.index[0])
        print("Last timestamp:", df.index[-1])

if __name__ == "__main__":
    main()


import os
import sys
import logging
from binance.client import Client
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config
from advanced_pump_detector import AdvancedPumpDumpDetector

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_weekly_gainers():
    try:
        client = Client(config.BINANCE_API_KEY, config.BINANCE_API_SECRET)
        tickers = client.get_ticker()
        
        # Filter USDT pairs
        usdt_pairs = [t for t in tickers if t['symbol'].endswith('USDT')]
        
        # We need 7-day change, but ticker is 24h. 
        # We'll fetch 1w klines for a quick check or just sorting by 24h is not enough.
        # Let's get 7-day change by fetching 1w kline for all (slow) or just reliable ones.
        # Faster: Get top 24h gainers first, or just scan top 100 volume coins for 7d change.
        # Actually, let's just fetch daily klines for the last 8 days for all USDT pairs (might be slow).
        # Optimization: Check top 100 24h volume coins.
        
        sorted_by_vol = sorted(usdt_pairs, key=lambda x: float(x['quoteVolume']), reverse=True)[:100]
        
        gainers = []
        print(f"Scanning top {len(sorted_by_vol)} coins by volume for weekly gainers...")
        
        for t in sorted_by_vol:
            symbol = t['symbol']
            try:
                klines = client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_1DAY, limit=8)
                if len(klines) < 7:
                    continue
                    
                # Close price 7 days ago vs today
                close_7d_ago = float(klines[0][4])
                close_now = float(klines[-1][4])
                
                pct_change = ((close_now - close_7d_ago) / close_7d_ago) * 100
                
                if pct_change > 20: # Filter > 20% gainers
                    gainers.append({
                        'symbol': symbol,
                        'change_7d': pct_change,
                        'price': close_now
                    })
            except Exception as e:
                print(f"Error fetching {symbol}: {e}")
                
        # Sort by 7d change
        gainers.sort(key=lambda x: x['change_7d'], reverse=True)
        return gainers[:30]
        
    except Exception as e:
        logger.error(f"Error getting gainers: {e}")
        return []

def verify_logic(symbol):
    print(f"\n--- Verifying Logic for {symbol} ---")
    client = Client(config.BINANCE_API_KEY, config.BINANCE_API_SECRET)
    
    # Fetch 1h klines for last 14 days to capture the "Pre-Pump" phase
    # We want to find the exact moment detection WOULD have happened.
    start_str = "14 days ago UTC"
    klines = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1HOUR, start_str)
    
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'taker_base_vol', 'taker_quote_vol', 'ignore'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['close'] = df['close'].astype(float)
    df['volume'] = df['volume'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['open'] = df['open'].astype(float)
    
    detector = AdvancedPumpDumpDetector(None) # client not needed for internal calculation
    
    # Sliding window backtest
    # We slide a window across the data and check if detection triggers
    window_size = 120
    detections = []
    
    print(f"Backtesting sliding window over {len(df)} hours...")
    
    ticker_data = {}
    try:
        # Fetch Realtime Ticker for ESPUSDT
        raw_ticker = client.get_ticker(symbol='ESPUSDT')
        ticker_data = raw_ticker
        print(f"DEBUG: Ticker Data for ESPUSDT: Vol {ticker_data.get('volume')}")
    except Exception as e:
        print(f"Error fetching ticker: {e}")

    # Start loop
    for i in range(50, len(df) + 1):
        window = df.iloc[i-50:i].copy()
        current_time = window.iloc[-1]['timestamp']
        current_price = window.iloc[-1]['close']
        
        # Pass ticker_data ONLY to the last candle (current moment simulation)
        is_live_candle = (i == len(df))
        
        if is_live_candle:
             result = detector._detect_stealth_accumulation(window, ticker_data=ticker_data)
        else:
             result = detector._detect_stealth_accumulation(window)
        
        if result and result.get('detected'):
            score = result.get('confidence', 0)
            if score >= 60: # Capture Near Misses (60+)
                detections.append({
                    'time': current_time,
                    'price': current_price,
                    'score': score,
                    'type': 'Stealth Accumulation',
                    'pump_time': result.get('pump_time', 'Unknown'),
                    'evidence': result.get('evidence', [])
                })
        
        # DEBUG: Print Volume Stats for the last candle analyzed
        if i == len(df): # Last candle only
            curr_vol_24h_kline = window.iloc[-24:]['volume'].astype(float).sum()
            ticker_vol = float(ticker_data.get('volume', 0)) if ticker_data else 0
            
            print(f"\n📊 VOLUME ANALYSIS for {symbol} (Last Candle):")
            print(f"  • Realtime Ticker 24h Vol: {ticker_vol:,.0f} (Used for Logic)")
            print(f"  • Kline Sum 24h Vol:       {curr_vol_24h_kline:,.0f} (Calculated from Candles)")
            print(f"  • Difference:              {ticker_vol - curr_vol_24h_kline:,.0f}")
            print(f"  • Detection Result: {result.get('detected')} (Score: {result.get('confidence')})")
            print(f"  • Evidence:")
            if 'evidence' in result:
                for ev in result['evidence']:
                    print(f"    - {ev}")
            
            # SIMULATE SMART ALERT UPDATE (New Threshold: > 0.15%)
            print("\n--- 🧪 SMART ALERT SIMULATION (Threshold > 0.15%) ---")
            # Assume we alerted recently
            # Simulate a 0.2% increase (Micro-burst)
            prev_vol = ticker_vol * 0.998 
            vol_change = ((ticker_vol - prev_vol) / prev_vol) * 100
            print(f"Simulating Previous Alert (Vol: {prev_vol:,.0f})...")
            print(f"Current Vol: {ticker_vol:,.0f} -> Change: +{vol_change:.2f}%")
            
            if vol_change > 0.15:
                print("✅ Smart Alert Trigger: UPDATE (Volume Spike > 0.15%)")
            else:
                print("❌ Smart Alert Trigger: NONE (Change < 0.15%)")
                
            # SIMULATE FUNDING RATE BONUS
            print("\n--- 🧪 FUNDING RATE SIMULATION ---")
            mock_funding = -0.0002
            print(f"Simulating Negative Funding: {mock_funding*100:.4f}%")
            if mock_funding < 0:
                print("✅ Smart Alert Trigger: Funding Rate Bonus (+5/+10 points)")
            
            # CHECK BUY PRESSURE
            print(f"DEBUG EVIDENCE: {result.get('evidence', [])}")
                
    max_score = 0
    if detections:
        max_score = max(d['score'] for d in detections)
        print(f"✅ DETECTED {len(detections)} signals (Max Score: {max_score})")
        # Show specific detections
        max_price = df['close'].max()
        max_price_time = df.loc[df['close'].idxmax()]['timestamp']
        
        print(f"📈 Peak Price: {max_price} at {max_price_time}")
        print("All Detected Signals:")
        for d in detections:
            # if d['time'] < max_price_time:
            print(f"  • {d['time']} | Price: {d['price']} | Score: {d['score']} | Time: {d['pump_time']}")
            if d['score'] < 70 and d['score'] >= 60:
                print(f"    ⚠️ Evidence: {d['evidence']}")
            
    else:
        print("❌ NO DETECTION triggered (> 60).")
        
    return max_score

if __name__ == "__main__":
    # Target specific coin for analysis
    target_coin = 'ESPUSDT'
    print(f"Targeting {target_coin} for Volume & Logic analysis...")
    
    summary = []
    
    try:
        max_score = verify_logic(target_coin)
        summary.append({
            'symbol': target_coin,
            'change': 0, 
            'max_score': max_score
        })
    except Exception as e:
        print(f"Error checking {target_coin}: {e}")
        print("Note: Ensure the symbol is correct and listed on Binance USDT market.")
            
    print("\n\n=== VERIFICATION SUMMARY ===")
    print(f"{'Symbol':<10} | {'7d Change':<10} | {'Max Score':<10} | {'Status':<15}")
    print("-" * 55)
    for item in sorted(summary, key=lambda x: x['max_score'], reverse=True):
        status = "✅ DETECTED" if item['max_score'] >= 70 else "⚠️ NEAR MISS" if item['max_score'] >= 60 else "❌ MISSED"
        print(f"{item['symbol']:<10} | {item['change']:>9.1f}% | {item['max_score']:>9} | {status}")

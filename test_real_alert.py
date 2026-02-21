"""Test FULL alert pipeline with REAL Binance data"""
import os
from dotenv import load_dotenv
load_dotenv()

from binance_client import BinanceClient
from advanced_pump_detector import AdvancedPumpDumpDetector
from vietnamese_messages import get_stealth_accumulation_alert

bc = BinanceClient(os.getenv('BINANCE_API_KEY'), os.getenv('BINANCE_API_SECRET'))
detector = AdvancedPumpDumpDetector(bc)

# Test with a few coins
test_coins = ['BTCUSDT', 'ETHUSDT', 'COMPUSDT']

for symbol in test_coins:
    print(f"\n{'='*60}")
    print(f"Testing {symbol}...")
    
    # 1. Get klines
    klines = bc.get_klines(symbol, '1h', limit=50)
    if klines is None or klines.empty:
        print(f"  ❌ No klines for {symbol}")
        continue
    
    # 2. Get ticker data
    try:
        ticker_data = bc.client.get_ticker(symbol=symbol)
        vol_24h = float(ticker_data.get('volume', 0))
        vol_usdt = float(ticker_data.get('quoteVolume', 0))
        print(f"  📊 Ticker Vol: {vol_24h:,.0f} coin, ${vol_usdt:,.0f} USDT")
    except Exception as e:
        print(f"  ❌ Ticker error: {e}")
        ticker_data = None
        
    # 3. Run detector
    result = detector._detect_stealth_accumulation(klines, ticker_data=ticker_data, symbol=symbol)
    
    if result and result.get('detected'):
        score = result.get('confidence', 0)
        funding = result.get('funding_rate', 0)
        vol_ratio = result.get('vol_ratio', 1)
        r_vol_24h = result.get('vol_24h', 0)
        r_vol_usdt = result.get('vol_24h_usdt', 0)
        
        print(f"  ✅ DETECTED! Score: {score}, Funding: {funding*100:.4f}%")
        print(f"  📊 Result vol_24h: {r_vol_24h:,.0f}, vol_24h_usdt: {r_vol_usdt:,.0f}")
        
        # 4. Get supply shock
        try:
            price = float(klines.iloc[-1]['close'])
            order_book = bc.get_order_book(symbol, limit=100)
            supply_shock = detector._analyze_supply_shock(order_book, price)
        except:
            supply_shock = None
        
        # 5. Generate alert
        # 5. Generate alert (Simulate Update #1)
        changes = {
            'price_pct': 1.5,
            'vol_pct': 0.08,
            'vol_coin_abs': r_vol_24h * 0.0008, # 0.08%
            'vol_usdt_pct': 0.08,
            'vol_usdt_abs': r_vol_usdt * 0.0008,
            'score': 5,
            'vol_ratio': 0.5,
            'funding_diff': -0.0005
        }
        
        msg = get_stealth_accumulation_alert(
            symbol, str(price), None, result['evidence'],
            supply_shock_data=supply_shock,
            funding_rate=funding,
            vol_ratio=vol_ratio,
            vol_24h=r_vol_24h,
            vol_24h_usdt=r_vol_usdt,
            update_count=1,
            changes=changes
        )
        
        # 6. Check all expected fields
        checks = {
            'Tier Label': any(x in msg for x in ['ƯU TIÊN CAO', 'KHẢ QUAN', 'THEO DÕI']),
            'Funding Rate': 'Funding' in msg,
            'Volume 24h': 'Volume 24h' in msg,
            'Giá hiện tại': 'Giá hiện tại' in msg,
            'Yếu Tố Quyết Định': 'Yếu Tố' in msg,
        }
        
        print(f"\n  📋 FIELD CHECKS:")
        all_ok = True
        for field, ok in checks.items():
            status = "✅" if ok else "❌ MISSING"
            print(f"     {status} {field}")
            if not ok:
                all_ok = False
        
        if all_ok:
            print(f"\n  🎉 ALL FIELDS PRESENT!")
        else:
            print(f"\n  ⚠️ SOME FIELDS MISSING!")
            
        # Print first 20 lines of message
        print(f"\n  --- PREVIEW (first 15 lines) ---")
        for i, line in enumerate(msg.split('\n')[:15]):
            # Strip HTML tags for readability
            clean = line.replace('<b>', '').replace('</b>', '').replace('<i>', '').replace('</i>', '')
            print(f"  {clean}")
    else:
        print(f"  ℹ️ No stealth accumulation detected for {symbol}")

print(f"\n{'='*60}")
print("TEST COMPLETE!")

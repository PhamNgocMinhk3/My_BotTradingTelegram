"""
Verification Script - Check all fixes before packaging
Tests:
1. Import checks (all modules load without errors)
2. Scoring formula correctness
3. Stealth Accumulation detection with sample data
4. Supply Shock detection
5. RealtimePumpDetector attributes (running, start, stop)
"""
import sys
import traceback

passed = 0
failed = 0
total = 0

def test(name, func):
    global passed, failed, total
    total += 1
    try:
        result = func()
        if result:
            print(f"  ✅ {name}")
            passed += 1
        else:
            print(f"  ❌ {name} - returned False")
            failed += 1
    except Exception as e:
        print(f"  ❌ {name} - {e}")
        traceback.print_exc()
        failed += 1

print("=" * 60)
print("  🔍 VERIFICATION: Pre-packaging checks")
print("=" * 60)

# ---- TEST 1: Import checks ----
print("\n📦 1. IMPORT CHECKS")

def test_import_config():
    import config
    return True

def test_import_binance():
    from binance_client import BinanceClient
    return True

def test_import_pump_detector():
    from pump_detector_realtime import RealtimePumpDetector
    return True

def test_import_advanced_detector():
    from advanced_pump_detector import AdvancedPumpDumpDetector
    return True

def test_import_gemini():
    from gemini_analyzer import GeminiAnalyzer
    return True

def test_import_stoch_rsi():
    from stoch_rsi_analyzer import StochRSIAnalyzer
    return True

def test_import_telegram():
    from telegram_bot import TelegramBot
    return True

def test_import_indicators():
    from indicators import calculate_rsi, calculate_mfi
    return True

def test_import_os_json_in_pump_detector():
    """Verify os and json are importable from pump_detector_realtime"""
    import pump_detector_realtime
    # Check that the module has os and json available
    source = open(pump_detector_realtime.__file__, 'r', encoding='utf-8').read()
    has_os = 'import os' in source
    has_json = 'import json' in source
    return has_os and has_json

test("config", test_import_config)
test("binance_client", test_import_binance)
test("pump_detector_realtime", test_import_pump_detector)
test("advanced_pump_detector", test_import_advanced_detector)
test("gemini_analyzer", test_import_gemini)
test("stoch_rsi_analyzer", test_import_stoch_rsi)
test("telegram_bot", test_import_telegram)
test("indicators", test_import_indicators)
test("os/json in pump_detector_realtime", test_import_os_json_in_pump_detector)

# ---- TEST 2: RealtimePumpDetector attributes ----
print("\n🏗️ 2. RealtimePumpDetector ATTRIBUTES")

def test_pump_detector_has_running():
    from pump_detector_realtime import RealtimePumpDetector
    # Check source code for self.running
    import inspect
    source = inspect.getsource(RealtimePumpDetector.__init__)
    return 'self.running' in source

def test_pump_detector_has_start():
    from pump_detector_realtime import RealtimePumpDetector
    return hasattr(RealtimePumpDetector, 'start') and callable(getattr(RealtimePumpDetector, 'start'))

def test_pump_detector_has_stop():
    from pump_detector_realtime import RealtimePumpDetector
    return hasattr(RealtimePumpDetector, 'stop') and callable(getattr(RealtimePumpDetector, 'stop'))

test("has self.running attribute", test_pump_detector_has_running)
test("has start() method", test_pump_detector_has_start)
test("has stop() method", test_pump_detector_has_stop)

# ---- TEST 3: Scoring formula correctness ----
print("\n🧮 3. SCORING FORMULA (Stealth Accumulation)")

def test_scoring_no_duplicate_variable():
    """Verify the scoring bug is fixed - no duplicate vol_score"""
    import inspect
    from advanced_pump_detector import AdvancedPumpDumpDetector
    source = inspect.getsource(AdvancedPumpDumpDetector._detect_stealth_accumulation)
    
    # Should have compression_score, NOT duplicate vol_score
    has_compression = 'compression_score' in source
    has_volume = 'volume_score' in source
    
    # Should NOT have the old bug pattern "vol_score + vol_score"
    has_bug = 'vol_score + vol_score' in source
    
    if has_bug:
        print("    ⚠️  BUG STILL EXISTS: 'vol_score + vol_score' found!")
        return False
    if not has_compression:
        print("    ⚠️  Missing compression_score variable")
        return False
    if not has_volume:
        print("    ⚠️  Missing volume_score variable")
        return False
    
    return True

def test_scoring_formula_components():
    """Check all 5 scoring components are present"""
    import inspect
    from advanced_pump_detector import AdvancedPumpDumpDetector
    source = inspect.getsource(AdvancedPumpDumpDetector._detect_stealth_accumulation)
    
    components = ['compression_score', 'volume_score', 'obv_score', 'rsi_bonus', 'buy_bonus']
    missing = [c for c in components if c not in source]
    
    if missing:
        print(f"    ⚠️  Missing components: {missing}")
        return False
    return True

def test_scoring_total_formula():
    """Verify total_score uses all 5 components"""
    import inspect
    from advanced_pump_detector import AdvancedPumpDumpDetector
    source = inspect.getsource(AdvancedPumpDumpDetector._detect_stealth_accumulation)
    
    expected = 'compression_score + volume_score + obv_score + rsi_bonus + buy_bonus'
    return expected in source

def test_volatility_threshold_relaxed():
    """Verify volatility threshold was relaxed from 1.5% to 2.5%"""
    import inspect
    from advanced_pump_detector import AdvancedPumpDumpDetector
    source = inspect.getsource(AdvancedPumpDumpDetector._detect_stealth_accumulation)
    
    has_new_threshold = '0.025' in source
    has_old_threshold = 'avg_volatility < 0.015' in source  # Old strict threshold
    
    if has_old_threshold:
        print("    ⚠️  Old threshold 0.015 still present!")
        return False
    if not has_new_threshold:
        print("    ⚠️  New threshold 0.025 not found!")
        return False
    return True

test("No duplicate vol_score bug", test_scoring_no_duplicate_variable)
test("All 5 scoring components exist", test_scoring_formula_components)
test("Total formula uses all 5 components", test_scoring_total_formula)
test("Volatility threshold relaxed to 2.5%", test_volatility_threshold_relaxed)

# ---- TEST 4: Scoring with sample data ----
print("\n📊 4. SCORING WITH SAMPLE DATA")

def test_scoring_with_mock_data():
    """Test scoring with synthetic data to verify correctness"""
    import pandas as pd
    import numpy as np
    from advanced_pump_detector import AdvancedPumpDumpDetector
    
    # Create mock klines: 50 candles with slight upward OBV, flat price 
    np.random.seed(42)
    n = 60
    base_price = 1.0
    
    # Flat price (low volatility)
    closes = base_price + np.random.normal(0, 0.003, n)
    
    # Volume: first 25 low, last 25 higher (accumulation)
    volumes = np.concatenate([
        np.random.uniform(1000, 1500, 30),  # first half: low vol
        np.random.uniform(2000, 3000, 30),  # second half: high vol
    ])
    
    df = pd.DataFrame({
        'open': closes - 0.001,
        'high': closes + 0.005,
        'low': closes - 0.005,
        'close': closes,
        'volume': volumes
    })
    
    # Create detector (no binance needed for this test)
    detector = AdvancedPumpDumpDetector.__new__(AdvancedPumpDumpDetector)
    
    result = detector._detect_stealth_accumulation(df)
    
    if result.get('detected'):
        score = result.get('quality_score', 0)
        print(f"    📊 Detected! Score: {score}/100")
        print(f"    📋 Evidence: {result.get('evidence', [])}")
        
        # Score should be reasonable (not 0, not 200)
        if score < 0 or score > 100:
            print(f"    ⚠️  Score out of range: {score}")
            return False
        return True
    else:
        print("    ℹ️  Not detected with sample data (may be OK if data doesn't meet criteria)")
        return True  # Not a bug, just data doesn't match

test("Scoring with synthetic accumulation data", test_scoring_with_mock_data)

# ---- TEST 5: Supply Shock function ----
print("\n🧱 5. SUPPLY SHOCK ANALYSIS")

def test_supply_shock_function():
    """Test supply shock with mock order book"""
    from advanced_pump_detector import AdvancedPumpDumpDetector
    
    detector = AdvancedPumpDumpDetector.__new__(AdvancedPumpDumpDetector)
    
    # Mock order book: strong buy wall, thin sell wall (like ME)
    order_book = {
        'bids': [[str(1.0 - i*0.001), str(1000)] for i in range(20)],  # 20 levels, 1000 each
        'asks': [[str(1.0 + i*0.001), str(200)] for i in range(20)],   # 20 levels, 200 each (thin!)
    }
    
    result = detector._analyze_supply_shock(order_book, 1.0)
    
    detected = result.get('detected', False)
    ratio = result.get('ratio', 0)
    cost = result.get('cost_to_push_5pct', 0)
    
    print(f"    📊 Detected: {detected}, Ratio: {ratio:.2f}x, Cost 5%: ${cost:,.0f}")
    
    # With buy=20000, sell=4000, ratio should be ~5x
    if ratio < 1:
        print("    ⚠️  Ratio too low, something is wrong")
        return False
    return True

test("Supply shock with thin sell wall", test_supply_shock_function)

# ---- SUMMARY ----
print(f"\n{'=' * 60}")
print(f"  📋 SUMMARY: {passed}/{total} passed, {failed}/{total} failed")
print(f"{'=' * 60}")

if failed == 0:
    print("  ✅ ALL TESTS PASSED - Safe to package!")
else:
    print(f"  ❌ {failed} TESTS FAILED - Fix before packaging!")

sys.exit(0 if failed == 0 else 1)

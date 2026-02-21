
import logging
import time
from unittest.mock import MagicMock
from watchlist import WatchlistManager
from pump_detector_realtime import RealtimePumpDetector

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockBinance:
    def get_all_usdt_symbols(self):
        return ['BTCUSDT', 'ETHUSDT', 'WEAKUSDT', 'STRONGUSDT', 'STAGNANTUSDT']
    
    def get_current_price(self, symbol):
        return 100.0
        
    def format_price(self, symbol, price):
        return str(price)
    
    def get_klines(self, symbol, interval, limit):
        # Return dummy dataframe-like object or list if needed
        # PumpDetector needs dataframe usually
        import pandas as pd
        if symbol == 'WEAKUSDT':
            # Create dummy data that will result in low score
            return pd.DataFrame() 
        return pd.DataFrame()

class MockBotDetector:
    pass

class MockAdvancedDetector:
    def _detect_stealth_accumulation(self, klines):
        # Mock results based on symbol name
        if 'STRONG' in str(klines): # Hacky way to pass symbol info if needed, but here we mock differently
            return {'confidence': 80, 'detected': True}
        return {'confidence': 40, 'detected': True}

def test_cleanup_logic():
    print("\n--- Testing Watchlist Cleanup ---")
    
    # Mock dependencies
    mock_binance = MockBinance()
    mock_bot = MagicMock()
    mock_bot_detector = MockBotDetector()
    
    # Initialize Watchlist (use temp file)
    watchlist = WatchlistManager('test_watchlist.json')
    watchlist.clear()
    
    # Add dummy data
    # 1. Strong Coin (Score 80)
    watchlist.add('STRONGUSDT', price=100, score=80)
    
    # 2. Weak Coin (Score 40) - Should be removed
    watchlist.add('WEAKUSDT', price=100, score=40)
    
    # 3. Stagnant Coin (Old entry, no price change) - Should be removed
    watchlist.add('STAGNANTUSDT', price=100, score=70)
    # Manually backdate the entry time
    watchlist.details['STAGNANTUSDT']['time'] = time.time() - 90000 # > 24h
    watchlist.details['STAGNANTUSDT']['price'] = 100.0 # No change
    watchlist.save()
    
    print(f"Initial Watchlist: {watchlist.get_all()}")
    
    # Initialize Detector
    # Config signature: binance_client, telegram_bot, bot_detector, watchlist_manager=None, advanced_detector=None
    detector = RealtimePumpDetector(mock_binance, mock_bot, mock_bot_detector, watchlist_manager=watchlist)
    
    # Mock Advanced Detector for cleanup scan
    detector.advanced_detector = MagicMock()
    
    def mock_detect(klines):
        # We can't easily know which symbol generated the klines in this mock setup without complex mocking
        # So we will rely on side_effect or strict mocking
        pass

    # Let's mock the _detect_stealth_accumulation to return based on call args? 
    # Hard because it takes klines df.
    # Instead, we will Mock the get_klines to return a DF that we can identify, or just mock the detector method to return values based on sequence?
    
    # Simpler: Mock the method to return specific scores
    # WEAKUSDT -> 40
    # STRONGUSDT -> 80
    # STAGNANTUSDT -> 70
    
    # But detector iterates watchlist. We need to match calls.
    # Let's override the _clean_watchlist loop logic? No, we want to test it.
    
    # We will patch self.binance.get_klines to return a DataFrame that "knows" its symbol? No.
    # We will just patch PumpDetector.advanced_detector._detect_stealth_accumulation directly?
    
    # BETTER: Mock binance.get_klines to return a DataFrame with a hidden attribute?
    # Or just Assume iteration order? 
    # Watchlist order is: STRONG, WEAK, STAGNANT (Insertion order usually preserved)
    
    # Let's assume order and use side_effect
    import pandas as pd
    dummy_df = pd.DataFrame({'close': [100.0]*50})
    
    detector.binance.get_klines = MagicMock(return_value=dummy_df)
    
    # Side effect for detect: returns specific score for each call
    # Order of iteration in watchlist.get_all()
    # List: ['STRONGUSDT', 'WEAKUSDT', 'STAGNANTUSDT']
    
    results = [
        {'confidence': 80, 'detected': True}, # STRONG
        {'confidence': 40, 'detected': True}, # WEAK
        {'confidence': 70, 'detected': True}, # STAGNANT
    ]
    detector.advanced_detector._detect_stealth_accumulation = MagicMock(side_effect=results)
    
    # Run Cleanup
    detector._clean_watchlist()
    
    # Verify Removals
    current_list = watchlist.get_all()
    print(f"Final Watchlist: {current_list}")
    
    if 'WEAKUSDT' not in current_list:
        print("✅ Success: WEAKUSDT removed (Score 40)")
    else:
        print("❌ Failed: WEAKUSDT still in list")

    if 'STAGNANTUSDT' not in current_list:
        print("✅ Success: STAGNANTUSDT removed (Stagnant)")
    else:
        print("❌ Failed: STAGNANTUSDT still in list")
        
    if 'STRONGUSDT' in current_list:
        print("✅ Success: STRONGUSDT kept")
    else:
        print("❌ Failed: STRONGUSDT removed incorrectly")

if __name__ == "__main__":
    try:
        test_cleanup_logic()
    except Exception as e:
        print(f"Test Error: {e}")

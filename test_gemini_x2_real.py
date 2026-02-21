import os
import sys
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TestRealData")

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from binance.client import Client
from advanced_pump_detector import AdvancedPumpDumpDetector

def test_real_data(symbol="BTCUSDT"):
    """
    Test Gemini X2 logic with REAL data from Binance
    """
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    
    if not api_key or not api_secret:
        logger.error("❌ BINANCE_API_KEY or BINANCE_API_SECRET not found in .env")
        return

    try:
        logger.info(f"🔌 Connecting to Binance API (Wrapper)...")
        from binance_client import BinanceClient
        client = BinanceClient(api_key, api_secret)
        
        # Initialize detector - note: AdvancedPumpDumpDetector expects a client that has get_klines 
        # but historically it might have expected the raw client. 
        # Let's check AdvancedPumpDumpDetector.__init__
        # It usually takes 'client'. 
        
        # In pump_detector_realtime.py:
        # self.advanced_detector = AdvancedPumpDumpDetector(self.binance) 
        # where self.binance is the wrapper.
        
        # So we should pass the wrapper to the detector.
        detector = AdvancedPumpDumpDetector(client)
        
        logger.info(f"📊 Fetching real data for {symbol}...")
        
        # 1. Get 1h klines using the WRAPPER's method
        klines = client.get_klines(symbol, '1h', limit=50)
        
        if klines is not None and not klines.empty:
             logger.info(f"✅ Fetched {len(klines)} klines")
        else:
             logger.error("❌ Failed to fetch klines")
             return
        
        # 2. Test Stealth Accumulation
        logger.info(f"🔍 Analyzing Stealth Accumulation for {symbol}...")
        stealth_result = detector._detect_stealth_accumulation(klines)
        logger.info(f"👉 Result: {stealth_result}")
        
        # 3. Test Supply Shock (Fetch Order Book)
        logger.info(f"📚 Fetching Order Book for {symbol}...")
        order_book = client.get_order_book(symbol=symbol, limit=100)
        current_price = float(klines.iloc[-1]['close'])
        
        logger.info(f"🔍 Analyzing Supply Shock...")
        supply_shock = detector._analyze_supply_shock(order_book, current_price)
        
        logger.info(f"👉 Supply Shock: {supply_shock}")
        
        if supply_shock['detected']:
            logger.info("💎 SUPPLY SHOCK DETECTED (Real Data)!")
        else:
            logger.info("ℹ️ No Supply Shock detected (Normal for major pairs)")
            
        logger.info("✅ REAL DATA TEST COMPLETED SUCCESSFULLY")
        
    except Exception as e:
        logger.error(f"❌ Error during real data test: {e}", exc_info=True)

if __name__ == "__main__":
    # You can change symbol here to test others like 'PEPEUSDT' or 'DOGEUSDT'
    test_symbol = "BTCUSDT" 
    if len(sys.argv) > 1:
        test_symbol = sys.argv[1]
    test_real_data(test_symbol)

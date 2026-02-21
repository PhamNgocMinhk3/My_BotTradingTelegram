import logging
import time
import sys
import os
import json
from unittest.mock import MagicMock

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("VerifyCleanup")

def verify_cleanup():
    try:
        from main import TradingBot
        from watchlist import WatchlistManager
        
        # 1. Create a dummy watchlist file
        test_watchlist_file = "test_watchlist.json"
        
        # Create dummy data
        # Coin A: Stop Loss (Entry 100, Current 90) -> Should be removed
        # Coin B: Stagnant (Entry 100, Current 101, Added > 24h ago) -> Should be removed
        # Coin C: Good (Entry 100, Current 110) -> Keep
        # Coin D: New (Entry 100, Current 100, Added now) -> Keep
        
        now = time.time()
        yesterday = now - 90000 # > 24h
        
        data = {
            "symbols": ["COIN_A_USDT", "COIN_B_USDT", "COIN_C_USDT", "COIN_D_USDT"],
            "details": {
                "COIN_A_USDT": {"price": 100.0, "time": now, "score": 80},
                "COIN_B_USDT": {"price": 100.0, "time": yesterday, "score": 50},
                "COIN_C_USDT": {"price": 100.0, "time": yesterday, "score": 90},
                "COIN_D_USDT": {"price": 100.0, "time": now, "score": 60}
            }
        }
        
        with open(test_watchlist_file, 'w') as f:
            json.dump(data, f)
            
        logger.info("1. Created test watchlist with 4 simulated coins")
        
        # 2. Initialize Bot
        bot = TradingBot()
        
        # 3. Swap watchlist with testing one
        bot.command_handler.watchlist = WatchlistManager(test_watchlist_file)
        logger.info(f"   Loaded test watchlist: {bot.command_handler.watchlist.get_all()}")
        
        # 4. Mock Binance Client to return controlled prices
        # We need to mock get_all_tickers
        mock_tickers = [
            {'symbol': 'COIN_A_USDT', 'price': '90.00'},  # -10% -> Remove (SL)
            {'symbol': 'COIN_B_USDT', 'price': '101.00'}, # +1% & ancient -> Remove (Stagnant)
            {'symbol': 'COIN_C_USDT', 'price': '110.00'}, # +10% -> Keep
            {'symbol': 'COIN_D_USDT', 'price': '100.00'}, # 0% & new -> Keep
        ]
        
        # Inject mock
        bot.command_handler.binance.client.get_all_tickers = MagicMock(return_value=mock_tickers)
        # Also mock get_symbol_ticker for fallback check (though not used if batch works)
        bot.command_handler.binance.client.get_symbol_ticker = MagicMock(side_effect=lambda symbol: 
            next((t for t in mock_tickers if t['symbol'] == symbol), None)
        )
        
        # 5. Run Cleanup
        logger.info("2. Running _clean_watchlist()...")
        monitor = bot.command_handler.monitor
        monitor._clean_watchlist()
        
        # 6. Verify Results
        remaining = bot.command_handler.watchlist.get_all()
        logger.info(f"3. Remaining coins: {remaining}")
        
        errors = []
        if "COIN_A_USDT" in remaining:
            errors.append("❌ Failed to remove Stop Loss coin (A)")
        else:
            logger.info("✅ Coin A removed (Stop Loss)")
            
        if "COIN_B_USDT" in remaining:
            errors.append("❌ Failed to remove Stagnant coin (B)")
        else:
            logger.info("✅ Coin B removed (Stagnant)")
            
        if "COIN_C_USDT" not in remaining:
            errors.append("❌ Incorrectly removed Good coin (C)")
        else:
            logger.info("✅ Coin C kept (Good)")
            
        if "COIN_D_USDT" not in remaining:
            errors.append("❌ Incorrectly removed New coin (D)")
        else:
            logger.info("✅ Coin D kept (New)")
            
        if errors:
            logger.error("\n".join(errors))
            sys.exit(1)
            
        logger.info("✅ CLEANUP LOGIC VERIFIED SUCCESSFULLY")
        
        # Cleanup
        if os.path.exists(test_watchlist_file):
            os.remove(test_watchlist_file)
            
    except Exception as e:
        logger.error(f"Test Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    verify_cleanup()

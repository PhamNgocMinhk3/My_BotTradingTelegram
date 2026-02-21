
import sys
import os
import time
import logging
from unittest.mock import MagicMock
import pandas as pd

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Mock identifying parts
sys.path.append('d:/BOT COIN/rsi-mfi-trading-bot')

from watchlist_monitor import WatchlistMonitor

def verify_cleanup():
    logger.info("🧪 Starting Watchlist Cleanup Verification...")
    
    # Mocks
    mock_command_handler = MagicMock()
    mock_binance = MagicMock()
    mock_watchlist = MagicMock()
    mock_bot = MagicMock()
    
    mock_command_handler.binance = mock_binance
    mock_command_handler.watchlist = mock_watchlist
    mock_command_handler.bot = mock_bot
    
    # Initialize Monitor
    monitor = WatchlistMonitor(mock_command_handler)
    
    # Scenario 1: Quick Stagnation (> 4h, < 0.5% gain)
    # ------------------------------------------------
    symbol_stagnant = "STAGNANTUSDT"
    setup_stagnant_time = time.time() - 15000 # ~4.1 hours ago
    entry_price_stagnant = 100.0
    current_price_stagnant = 100.1 # 0.1% gain (should remove)
    
    # Scenario 2: Money Outflow (MFI < 30)
    # ------------------------------------
    symbol_outflow = "OUTFLOWUSDT"
    setup_outflow_time = time.time() - 3600 # 1 hour ago
    entry_price_outflow = 100.0
    current_price_outflow = 102.0 # 2% gain (looks good price-wise)
    
    # Mock Watchlist Data
    mock_watchlist.get_all.return_value = [symbol_stagnant, symbol_outflow]
    
    def get_details_side_effect(symbol):
        if symbol == symbol_stagnant:
            return {'price': entry_price_stagnant, 'time': setup_stagnant_time}
        if symbol == symbol_outflow:
            return {'price': entry_price_outflow, 'time': setup_outflow_time}
        return None
        
    mock_watchlist.get_details.side_effect = get_details_side_effect
    
    # Mock Current Prices (Batch Fetch)
    mock_binance.client.get_all_tickers.return_value = [
        {'symbol': symbol_stagnant, 'price': str(current_price_stagnant)},
        {'symbol': symbol_outflow, 'price': str(current_price_outflow)}
    ]
    
    # Mock Klines for MFI Calculation (Only for Outflow coin)
    # Need 14+ periods. Create a dataframe where MFI will be low.
    # Low MFI = Price dropping or low volume on up days. 
    # Simplest: Price dropping consistently.
    data = {
        'timestamp': range(30),
        'open': [100] * 30,
        'high': [101] * 30,
        'low': [90] * 30,
        'close': [95] * 30, # Close lower than open/previous?
        'volume': [1000] * 30
    }
    # To force low MFI, we need negative money flow.
    # Typical Price = (H+L+C)/3.
    # If Typical Price < Prev Typical Price -> Negative Flow.
    # Let's just create descending prices.
    prices = [100 - i for i in range(30)]
    df_low_mfi = pd.DataFrame({
        'timestamp': range(30),
        'open': prices,
        'high': [p+1 for p in prices],
        'low': [p-1 for p in prices],
        'close': prices,
        'volume': [10000] * 30,
        'close_time': range(30),
        'quote_asset_volume': [10000] * 30,
        'number_of_trades': [100] * 30,
        'taker_buy_base_asset_volume': [5000] * 30,
        'taker_buy_quote_asset_volume': [5000] * 30,
        'ignore': [0] * 30
    })
    
    mock_binance.get_klines.return_value = df_low_mfi
    
    # Run Cleanup
    logger.info("Running _clean_watchlist()...")
    monitor._clean_watchlist()
    
    # Verify Removals
    logger.info("Verifying removals...")
    
    removed_symbols = [call.args[0] for call in mock_watchlist.remove.call_args_list]
    
    if symbol_stagnant in removed_symbols:
        logger.info(f"✅ PASSED: Stagnant coin {symbol_stagnant} removed.")
    else:
        logger.error(f"❌ FAILED: Stagnant coin {symbol_stagnant} NOT removed.")
        
    if symbol_outflow in removed_symbols:
        logger.info(f"✅ PASSED: Outflow coin {symbol_outflow} removed (Low MFI).")
    else:
        logger.error(f"❌ FAILED: Outflow coin {symbol_outflow} NOT removed.")
        
    if len(removed_symbols) == 2:
        logger.info("✅ SUCCESS: All verification scenarios passed.")
    else:
        logger.error(f"❌ FAILURE: Expected 2 removals, got {len(removed_symbols)}.")

if __name__ == "__main__":
    verify_cleanup()

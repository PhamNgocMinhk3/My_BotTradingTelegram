import os
import sys
import logging
import inspect

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FinalVerify")

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from binance_client import BinanceClient
from telegram_bot import TelegramBot
from pump_detector_realtime import RealtimePumpDetector

def check_methods():
    """Check if critical methods exist in classes"""
    logger.info("🔍 Checking Method Availability...")
    
    # 1. Check BinanceClient methods used in RealtimePumpDetector
    required_binance_methods = [
        'get_klines',
        'get_current_price',
        'format_price',
        'get_order_book', # This was the missing one
        'get_all_usdt_symbols',
        'get_24h_data'
    ]
    
    missing_binance = []
    for method in required_binance_methods:
        if not hasattr(BinanceClient, method):
            missing_binance.append(method)
    
    if missing_binance:
        logger.error(f"❌ BinanceClient is missing methods: {missing_binance}")
    else:
        logger.info("✅ BinanceClient has all required methods.")

    # 2. Check TelegramBot methods
    required_bot_methods = [
        'send_message', # Replaced send_message_to_all
        'send_photo'
    ]
    
    missing_bot = []
    for method in required_bot_methods:
        if not hasattr(TelegramBot, method):
            missing_bot.append(method)
            
    if missing_bot:
        logger.error(f"❌ TelegramBot is missing methods: {missing_bot}")
    else:
        logger.info("✅ TelegramBot has all required methods.")
        
    return not missing_binance and not missing_bot

def check_files():
    """Check if essential files exist"""
    logger.info("🔍 Checking Critical Files...")
    
    required_files = [
        '.env', # Config
        'prompt_v3.txt', # AI Prompt
        'jsonAi.txt', # AI Structure
        'main.py', 
        'pump_detector_realtime.py',
        'advanced_pump_detector.py',
        'vietnamese_messages.py'
    ]
    
    missing_files = []
    for f in required_files:
        if not os.path.exists(f):
            missing_files.append(f)
            
    if missing_files:
        logger.error(f"❌ Missing critical files: {missing_files}")
    else:
        logger.info("✅ All critical files present.")
        
    return not missing_files

if __name__ == "__main__":
    logger.info("🚀 STARTING FINAL SYSTEM VERIFICATION")
    
    methods_ok = check_methods()
    files_ok = check_files()
    
    if methods_ok and files_ok:
        logger.info("\n✨ VERIFICATION PASSED! System is ready for packaging. ✨")
    else:
        logger.error("\n❌ VERIFICATION FAILED! Please fix issues before packaging.")
        sys.exit(1)

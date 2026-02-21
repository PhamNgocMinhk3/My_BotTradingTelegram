import logging
import time
import sys
import os

# Setup logging to console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("VerifyPump")

try:
    logger.info("1. Importing TradingBot...")
    from main import TradingBot
    
    logger.info("2. Initializing Bot (Connecting to APIs)...")
    bot = TradingBot()
    
    logger.info("3. Bot Initialized. Simulating '/startpumpwatch' command...")
    # Access the pump detector through command handler
    pump_detector = bot.command_handler.pump_detector
    
    if not pump_detector:
        logger.error("❌ Pump Detector not found in command handler!")
        sys.exit(1)
        
    logger.info(f"   Current Status: {'Running' if pump_detector.running else 'Stopped'}")
    
    logger.info("4. Starting Pump Detector...")
    pump_detector.start()
    
    if pump_detector.running:
        logger.info("✅ Pump Detector Started Successfully!")
    else:
        logger.error("❌ Failed to set running state!")
        sys.exit(1)
        
    logger.info("5. Waiting 30 seconds to verify scanning threads (Layer 1 & Pre-pump)...")
    for i in range(30):
        if i % 10 == 0:
            logger.info(f"   Scanning... {i}s")
        time.sleep(1)
        
        # Check if threads died
        if not pump_detector.running:
             logger.error("❌ Pump Monitor stopped unexpectedly!")
             sys.exit(1)

    logger.info("6. Verification Complete. Stopping...")
    pump_detector.stop()
    logger.info("✅ TEST PASSED: /startpumpwatch logic works without crashing.")
    
except Exception as e:
    logger.error(f"❌ TEST FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

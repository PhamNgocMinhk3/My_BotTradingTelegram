
import sys
import os
import logging
from unittest.mock import MagicMock

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Verification")

def verify_main_import():
    try:
        logger.info("Verifying main.py import...")
        import main
        if not hasattr(main, 'main'):
            logger.error("❌ main.main function missing!")
            return False
        logger.info("✅ main.py imported successfully and main() exists.")
        return True
    except ImportError as e:
        logger.error(f"❌ ImportError in main.py: {e}")
        return False
    except NameError as e:
        logger.error(f"❌ NameError in main.py: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error in main.py: {e}")
        return False

def verify_pump_detector():
    try:
        logger.info("Verifying RealtimePumpDetector...")
        from pump_detector_realtime import RealtimePumpDetector
        
        # Mock dependencies
        mock_binance = MagicMock()
        mock_bot = MagicMock()
        mock_detector = MagicMock()
        
        # Instantiate
        detector = RealtimePumpDetector(mock_binance, mock_bot, mock_detector)
        
        # Check attributes
        if not hasattr(detector, 'running'):
            logger.error("❌ RealtimePumpDetector missing 'running' attribute")
            return False
            
        # Check methods
        if not hasattr(detector, 'start'):
            logger.error("❌ RealtimePumpDetector missing 'start' method")
            return False
            
        if not hasattr(detector, 'stop'):
            logger.error("❌ RealtimePumpDetector missing 'stop' method")
            return False
            
        # Test Start/Stop logic
        logger.info("Testing start/stop logic...")
        detector.start()
        if not detector.running:
            logger.error("❌ detector.start() failed to set running=True")
            return False
            
        detector.stop()
        if detector.running:
            logger.error("❌ detector.stop() failed to set running=False")
            return False
            
        logger.info("✅ RealtimePumpDetector verified successfully.")
        return True
        
    except ImportError as e:
        logger.error(f"❌ ImportError in pump_detector_realtime.py: {e}")
        return False
    except NameError as e:
        logger.error(f"❌ NameError in pump_detector_realtime.py: {e}")
        return False
    except AttributeError as e:
         logger.error(f"❌ AttributeError: {e}")
         return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False

def verify_watchlist_monitor():
    try:
        logger.info("Verifying WatchlistMonitor...")
        from watchlist_monitor import WatchlistMonitor
        # Just check import for syntax errors for now
        logger.info("✅ WatchlistMonitor imported successfully.")
        return True
    except Exception as e:
        logger.error(f"❌ WatchlistMonitor error: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting Pre-Build Verification...")
    
    checks = [
        verify_main_import(),
        verify_pump_detector(),
        verify_watchlist_monitor()
    ]
    
    if all(checks):
        logger.info("\n✨ ALL CHECKS PASSED! Ready to build.")
        sys.exit(0)
    else:
        logger.error("\n❌ VERIFICATION FAILED. Fix errors before building.")
        sys.exit(1)

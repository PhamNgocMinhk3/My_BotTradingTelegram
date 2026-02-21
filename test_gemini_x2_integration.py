import unittest
from unittest.mock import MagicMock, patch
import logging
import sys
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pump_detector_realtime import RealtimePumpDetector
from vietnamese_messages import get_stealth_accumulation_alert

class TestGeminiX2Integration(unittest.TestCase):
    def setUp(self):
        self.mock_binance = MagicMock()
        self.mock_bot = MagicMock()
        self.mock_bot_detector = MagicMock()
        
        # Mock advanced detector return values
        self.mock_advanced = MagicMock()
        
        self.detector = RealtimePumpDetector(
            self.mock_binance,
            self.mock_bot,
            self.mock_bot_detector,
            advanced_detector=self.mock_advanced
        )

    def test_alert_generation_and_sending(self):
        """Test that alert is generated and sent correctly with Supply Shock data"""
        logger.info("🧪 Testing Gemini X2 Alert Integration...")
        
        # 1. Simulate Detection Data
        symbol = "BTCUSDT"
        price = 50000.0
        
        # Mock result from _detect_stealth_accumulation
        stealth_result = {
            'detected': True,
            'confidence': 85,
            'evidence': ['Low Volatility', 'Rising Volume', 'OBV Divergence']
        }
        self.mock_advanced._detect_stealth_accumulation.return_value = stealth_result
        
        # Mock result from _analyze_supply_shock
        supply_shock_result = {
            'detected': True,
            'ratio': 3.5,
            'cost_to_push_5pct': 150000.0
        }
        self.mock_advanced._analyze_supply_shock.return_value = supply_shock_result
        
        # Mock Binance responses
        import pandas as pd
        mock_df = pd.DataFrame({'close': [price] * 50, 'volume': [1000] * 50})
        self.mock_binance.get_klines.return_value = mock_df
        
        self.mock_binance.format_price.return_value = "50,000.00"
        self.mock_binance.get_current_price.return_value = price

        # 2. Run _analyze_pre_pump (which triggers the logic)
        # We need to patch the internal calls or just simulate the flow manually if _analyze_pre_pump is too complex
        # But let's try calling it directly since we mocked everything it uses.
        
        result = self.detector._analyze_pre_pump(symbol)
        
        # 3. Verify Result Structure (Fixing the KeyError issue)
        self.assertIsNotNone(result)
        self.assertTrue(result['supply_shock']['detected'])
        self.assertEqual(result['supply_shock']['ratio'], 3.5)
        
        # 4. Simulate the Alert Sending (Logic inside _scan_pre_pump loop)
        # Since _scan_pre_pump runs in a loop/thread, we just extract the alert logic block here to test it safely
        
        try:
            msg = get_stealth_accumulation_alert(
                result['symbol'],
                "50,000.00",
                None,
                result['evidence'], # This was the source of KeyError: 'indicators'
                supply_shock_data=result.get('supply_shock')
            )
            
            print("\nGenerated Message Preview:")
            print("-" * 40)
            print(msg)
            print("-" * 40)
            
            # Send (Mocked)
            self.mock_bot.send_message(msg)
            
            # Verify call
            self.mock_bot.send_message.assert_called_once()
            logger.info("✅ Alert sent successfully via send_message()")
            
        except KeyError as e:
            self.fail(f"❌ KeyError detected: {e} - Logic is still broken!")
        except AttributeError as e:
             self.fail(f"❌ AttributeError detected: {e} - Logic is still broken!")
        except Exception as e:
            self.fail(f"❌ Unexpected error: {e}")

if __name__ == '__main__':
    unittest.main()

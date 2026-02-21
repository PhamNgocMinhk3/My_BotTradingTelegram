
import sys
import unittest
from unittest.mock import MagicMock

# Mock imports since we only want to test prompt generation
sys.modules['binance_client'] = MagicMock()
sys.modules['stoch_rsi_analyzer'] = MagicMock()
sys.modules['google.generativeai'] = MagicMock()
sys.modules['database'] = MagicMock()
sys.modules['price_tracker'] = MagicMock()

# Import the class to test
# We need to ensure we can import it even if dependencies are mocked
from gemini_analyzer import GeminiAnalyzer

class TestPromptGeneration(unittest.TestCase):
    def setUp(self):
        # Mock dependencies
        self.mock_binance = MagicMock()
        self.mock_stoch = MagicMock()
        self.analyzer = GeminiAnalyzer("fake_key", self.mock_binance, self.mock_stoch)
        
    def test_early_pump_injection(self):
        # Mock data structure required by _build_prompt
        mock_data = {
            'symbol': 'BTCUSDT',
            'market_data': {
                'price': 100.0,
                'price_change_24h': 1.5,
                'high_24h': 105.0,
                'low_24h': 95.0,
                'volume_24h': 1000000
            },
            'rsi_mfi': {'consensus': 'NEUTRAL'},
            'stoch_rsi': {'consensus': 'NEUTRAL'},
            'volume_data': {'current': 1000, 'base_volume': 10, 'trades': 50},
            'historical_klines': {},
            
            # The Critical Part: Advanced Detection Data
            'advanced_detection': {
                'signal': 'POTENTIAL_PUMP',
                'confidence': 85,
                'volume_analysis': {
                    'is_spike': True,
                    'volume_ratio': 3.5,
                    'buy_pressure': 80.0
                },
                'supply_shock': {
                    'detected': True,
                    'cost_to_push_5pct': 50000,
                    'resistance_strength': 'Weak'
                },
                'pump_time': '24-48h'
            }
        }
        
        # Override format_price to avoid errors if called
        self.mock_binance.format_price.return_value = "100.00"
        
        # Generate Prompt
        prompt = self.analyzer._build_prompt(mock_data, trading_style='swing', user_id=None)
        
        # Verify Key Strings
        print("\n--- Testing Prompt Content ---")
        
        # Check for Early Pump Section
        self.assertIn("EARLY PUMP DETECTION (Stealth & Accumulation)", prompt)
        print("✅ Found 'EARLY PUMP DETECTION' section")
        
        # Check for Stealth Accumulation Logic (Volume Ratio 3.5 > 2.0 and Price Change 1.5 < 2.0 -> YES)
        self.assertIn("Stealth Accumulation: YES 🟢", prompt) 
        print("✅ Found 'Stealth Accumulation: YES 🟢'")
        
        # Check for Supply Shock
        self.assertIn("Supply Shock Risk: HIGH 🚨", prompt)
        print("✅ Found 'Supply Shock Risk: HIGH 🚨'")
        
        # Check for Pump Time
        self.assertIn("Estimated Pump Time: 24-48h", prompt)
        print("✅ Found 'Estimated Pump Time: 24-48h'")
        
        # Check for Whale Activity (from Volume Spike)
        self.assertIn("Spike Detected: YES 🚨 (Whale Activity)", prompt)
        print("✅ Found 'Spike Detected: YES 🚨 (Whale Activity)'")
        
        print("\n--- Test Passed Successfully! ---")

if __name__ == '__main__':
    unittest.main()

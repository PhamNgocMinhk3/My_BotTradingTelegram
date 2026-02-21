"""
Test script: Run Gemini AI Analysis on FUNUSDT
Usage: python test_funusdt.py
"""
import os, sys, json, logging
sys.stdout.reconfigure(encoding='utf-8')  # Force UTF-8 output
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
except Exception as e:
    print(f"[WARN] dotenv not loaded: {e}")

# Basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("test_funusdt")

SYMBOL = "FUNUSDT"

def main():
    from binance_client import BinanceClient
    from stoch_rsi_analyzer import StochRSIAnalyzer
    from gemini_analyzer import GeminiAnalyzer

    gemini_key = os.getenv("GEMINI_API_KEY", "")
    binance_key = os.getenv("BINANCE_API_KEY", "")
    binance_secret = os.getenv("BINANCE_SECRET_KEY", "")

    if not gemini_key:
        print("[ERR] GEMINI_API_KEY not set in .env")
        sys.exit(1)

    print(f"[KEY] GEMINI_API_KEY: ...{gemini_key[-6:]}")
    print(f"[NET] Connecting to Binance...")

    try:
        binance = BinanceClient(binance_key, binance_secret)
        price = binance.get_current_price(SYMBOL)
        print(f"[OK] Binance connected -- {SYMBOL} price: {price}")
    except Exception as e:
        print(f"[ERR] Binance error: {e}")
        sys.exit(1)

    print(f"[...] Initializing StochRSI Analyzer...")
    try:
        stoch_analyzer = StochRSIAnalyzer(binance)
    except Exception as e:
        print(f"[ERR] StochRSI init error: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)

    print(f"[...] Initializing Gemini AI Analyzer...")
    try:
        ai = GeminiAnalyzer(gemini_key, binance, stoch_analyzer)
    except Exception as e:
        print(f"[ERR] GeminiAnalyzer init error: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)

    print(f"\n[RUN] Running AI analysis for {SYMBOL}...")
    print("="*60)
    try:
        result = ai.analyze(SYMBOL, trading_style='swing')
        if result is None:
            print("[FAIL] analyze() returned None -- check logs above for the reason")
            sys.exit(1)

        print(f"\n[OK] Analysis complete!")
        print("="*60)
        print(f"Signal:      {result.get('signal', 'N/A')}")
        print(f"Confidence:  {result.get('confidence', 'N/A')}%")
        print(f"Entry Price: {result.get('entry_price', 'N/A')}")
        print(f"TP1:         {result.get('tp1', 'N/A')}")
        print(f"TP2:         {result.get('tp2', 'N/A')}")
        print(f"SL:          {result.get('sl', 'N/A')}")
        recommendation = result.get('recommendation', 'N/A')
        print(f"Recommend:   {recommendation}")

        reasoning = result.get('reasoning_vietnamese') or result.get('reasoning', '')
        print(f"\n[REASONING] (first 600 chars):")
        print(reasoning[:600])

        # Test format_response (Telegram message generation)
        print(f"\n{'='*60}")
        print("[TEST] Testing format_response (Telegram message)...")
        try:
            msg1, msg2, msg3 = ai.format_response(result)
            print(f"[OK] Message 1 ({len(msg1)} chars)")
            print(f"[OK] Message 2 ({len(msg2)} chars)")
            print(f"[OK] Message 3 ({len(msg3)} chars)")
            print("\n-- Message 1 preview --")
            print(msg1[:500])
        except Exception as e:
            print(f"[ERR] format_response error: {e}")
            import traceback; traceback.print_exc()

    except Exception as e:
        print(f"[ERR] Analysis error: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

"""
Main Bot Script
RSI + MFI Multi-Timeframe Analysis Bot
Scans Binance markets and sends alerts to Telegram
"""

import time
import logging
from datetime import datetime
import sys
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import modules
import config
from binance_client import BinanceClient
from telegram_bot import TelegramBot
from chart_generator import ChartGenerator
from indicators import analyze_multi_timeframe
from telegram_commands import TelegramCommandHandler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class TradingBot:
    def __init__(self):
        """Initialize the trading bot"""
        logger.info("Initializing Trading Bot...")
        
        # Initialize clients
        self.binance = BinanceClient(config.BINANCE_API_KEY, config.BINANCE_API_SECRET)
        self.telegram = TelegramBot(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID)
        self.chart_gen = ChartGenerator(
            style=config.CHART_STYLE,
            dpi=config.CHART_DPI,
            width=config.CHART_WIDTH,
            height=config.CHART_HEIGHT
        )
        
        # Initialize command handler (pass self for /scan command)
        self.command_handler = TelegramCommandHandler(
            self.telegram,
            self.binance,
            self.chart_gen,
            trading_bot_instance=self  # Pass bot instance for /scan
        )
        
        # Store instance globally for API access
        TradingBot._instance = self
        
        # Test connections
        if not self.test_connections():
            logger.error("Failed to initialize connections. Exiting.")
            sys.exit(1)
        
        logger.info("Trading Bot initialized successfully")
    
    def test_connections(self):
        """Test all API connections"""
        logger.info("Testing API connections...")
        
        binance_ok = self.binance.test_connection()
        telegram_ok = self.telegram.test_connection()
        
        if binance_ok and telegram_ok:
            logger.info("All connections successful")
            welcome_msg = """
<b>🤖 TRADING BOT ONLINE!</b>

<b>✅ ALL SYSTEMS OPERATIONAL</b>

<b>🎮 MODE:</b> Command-Only
<b>📊 Interactive:</b> Enabled
<b>⚡ Fast Scan:</b> Active

<b>🚀 QUICK START:</b>
• /<b>BTC</b> - Bitcoin analysis
• /<b>ETH</b> - Ethereum analysis  
• /<b>scan</b> - Scan entire market
• /<b>help</b> - All commands

<i>💡 No auto-scan. Use /scan when needed!</i>
            """
            self.telegram.send_message(welcome_msg)
            return True
        else:
            logger.error("Connection test failed")
            return False
    
    def analyze_symbol(self, symbol):
        """
        Analyze a single symbol (thread-safe method for concurrent execution)
        
        Args:
            symbol: Trading symbol to analyze
        
        Returns:
            Signal data dict or None if no signal
        """
        try:
            # Get multi-timeframe data
            klines_dict = self.binance.get_multi_timeframe_data(
                symbol, 
                config.TIMEFRAMES,
                limit=200
            )
            
            if not klines_dict:
                logger.warning(f"No data for {symbol}")
                return None
            
            # Analyze
            analysis = analyze_multi_timeframe(
                klines_dict,
                config.RSI_PERIOD,
                config.MFI_PERIOD,
                config.RSI_LOWER,
                config.RSI_UPPER,
                config.MFI_LOWER,
                config.MFI_UPPER
            )
            
            # Check if signal meets minimum consensus strength
            if analysis['consensus'] != 'NEUTRAL' and \
               analysis['consensus_strength'] >= config.MIN_CONSENSUS_STRENGTH:
                
                # Get current price and 24h data
                price = self.binance.get_current_price(symbol)
                market_data = self.binance.get_24h_data(symbol)
                
                signal_data = {
                    'symbol': symbol,
                    'timeframe_data': analysis['timeframes'],
                    'consensus': analysis['consensus'],
                    'consensus_strength': analysis['consensus_strength'],
                    'price': price,
                    'market_data': market_data,
                    'klines_dict': klines_dict
                }
                
                logger.info(f"✓ Signal found for {symbol}: {analysis['consensus']}" 
                          f"(Strength: {analysis['consensus_strength']})")
                return signal_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return None
    
    def scan_market(self, use_fast_scan=True, max_workers=0):
        """
        Scan the market for trading signals
        
        Args:
            use_fast_scan: Use parallel processing (default: True)
            max_workers: Number of concurrent threads (0 = auto-scale, default: 0)
        """
        logger.info(f"Starting market scan... (Fast: {use_fast_scan})")
        
        # Get all valid symbols
        symbol_infos = self.binance.get_all_symbols(
            quote_asset=config.QUOTE_ASSET,
            excluded_keywords=config.EXCLUDED_KEYWORDS,
            min_volume=config.MIN_VOLUME_USDT
        )
        
        if not symbol_infos:
            logger.warning("No symbols found to scan")
            return
        
        # Extract symbol names
        symbols = [s['symbol'] for s in symbol_infos]
        
        logger.info(f"Scanning {len(symbols)} symbols...")
        
        start_time = time.time()
        signals_found = []
        
        if use_fast_scan:
            # AUTO-SCALE workers based on number of symbols
            if max_workers == 0:
                # Smart scaling: 
                # 1-10 symbols: 5 workers
                # 11-50 symbols: 10 workers
                # 51-100 symbols: 15 workers
                # 100+ symbols: 20 workers (max)
                if len(symbols) <= 10:
                    max_workers = 5
                elif len(symbols) <= 50:
                    max_workers = 10
                elif len(symbols) <= 100:
                    max_workers = 15
                else:
                    max_workers = 20
                
                logger.info(f"Auto-scaled workers: {max_workers} (for {len(symbols)} symbols)")
            else:
                # Use provided max_workers but cap at 20
                max_workers = min(max_workers, 20)
            
            # FAST SCAN - Parallel processing
            self.telegram.send_message(
                f"🔍 <b>Fast Market Scan Started</b>\n\n"
                f"⚡ Analyzing {len(symbols)} symbols\n"
                f"🚀 Using {max_workers} parallel threads (auto-scaled)\n"
                f"⏳ Please wait..."
            )
            
            completed_count = 0
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all analysis tasks
                future_to_symbol = {
                    executor.submit(self.analyze_symbol, symbol): symbol 
                    for symbol in symbols
                }
                
                # Process results as they complete
                for future in as_completed(future_to_symbol):
                    symbol = future_to_symbol[future]
                    completed_count += 1
                    
                    try:
                        signal_data = future.result()
                        
                        if signal_data:
                            signals_found.append(signal_data)
                        
                        # Send progress update every 20%
                        progress_pct = (completed_count / len(symbols)) * 100
                        if completed_count % max(1, len(symbols) // 5) == 0:
                            elapsed = time.time() - start_time
                            avg_time = elapsed / completed_count
                            remaining = (len(symbols) - completed_count) * avg_time
                            
                            self.telegram.send_message(
                                f"⏳ Progress: {completed_count}/{len(symbols)} ({progress_pct:.0f}%)\n"
                                f"📊 Signals: {len(signals_found)}\n"
                                f"⏱️ Est. remaining: {remaining:.0f}s"
                            )
                    
                    except Exception as e:
                        logger.error(f"Error processing result for {symbol}: {e}")
        
        else:
            # NORMAL SCAN - Sequential processing
            for i, symbol in enumerate(symbols):
                logger.info(f"Analyzing {symbol} ({i+1}/{len(symbols)})...")
                
                signal_data = self.analyze_symbol(symbol)
                if signal_data:
                    signals_found.append(signal_data)
                
                # Small delay to avoid rate limits
                time.sleep(0.1)
        
        # Calculate performance
        total_time = time.time() - start_time
        avg_per_symbol = total_time / len(symbols) if len(symbols) > 0 else 0
        
        # Send results summary
        scan_mode = "⚡ Fast" if use_fast_scan else "🌐 Normal"
        summary_msg = (
            f"✅ <b>{scan_mode} Market Scan Complete!</b>\n\n"
            f"⏱️ Time: {total_time:.1f}s ({avg_per_symbol:.2f}s per symbol)\n"
            f"🔍 Scanned: {len(symbols)} symbols\n"
            f"📊 Signals found: {len(signals_found)}"
        )
        
        if use_fast_scan:
            summary_msg += f"\n⚡ Threads used: {max_workers}"
        
        self.telegram.send_message(summary_msg)
        
        # Send results
        if signals_found:
            logger.info(f"Found {len(signals_found)} signals")
            self.send_signals(signals_found)
        else:
            logger.info("No signals found")
            if not config.SEND_SUMMARY_ONLY:
                self.telegram.send_message("📊 Market scan complete. No signals detected.")
    
    def send_signals(self, signals_list):
        """Send signals to Telegram"""
        # Send summary first
        self.telegram.send_summary_table(signals_list)
        
        # If summary only mode, stop here
        if config.SEND_SUMMARY_ONLY:
            return
        
        # Add delay
        time.sleep(2)  # Give user time to see summary
        
        # Send RSI/MFI overview charts (for /scan command)
        if config.SEND_CHARTS and len(signals_list) > 0:
            self.telegram.send_message(f"📊 <b>Generating RSI/MFI overview charts by timeframe...</b>")
            
            try:
                chart_buffers = self.chart_gen.create_rsi_mfi_overview_charts(signals_list)
                
                if chart_buffers:
                    # chart_buffers is list of tuples: (indicator, timeframe, buffer)
                    for indicator, timeframe, chart_buf in chart_buffers:
                        emoji = "📊" if indicator == "RSI" else "💰"
                        self.telegram.send_photo(
                            chart_buf,
                            caption=f"{emoji} <b>{indicator} Signals - {timeframe}</b>\n"
                                   f"Coins with active {indicator} {timeframe} signals"
                        )
                        time.sleep(0.8)
                    
                    logger.info(f"✅ Sent {len(chart_buffers)} overview charts successfully")
                else:
                    logger.warning("No overview charts generated")
            except Exception as e:
                logger.error(f"Error sending overview charts: {e}")
        
        # Send notification before detailed analysis
        total_signals = len(signals_list)
        
        # Sort signals by priority: lowest RSI/MFI first (best buy opportunities)
        def get_signal_priority(signal):
            """
            Calculate priority score for signal
            Lower score = higher priority (better buy opportunity)
            """
            timeframe_data = signal.get('timeframe_data', {})
            
            # Get RSI and MFI from important timeframes
            important_tfs = ['1h', '4h', '1d']
            rsi_values = []
            mfi_values = []
            
            for tf in important_tfs:
                if tf in timeframe_data:
                    rsi = timeframe_data[tf].get('rsi', 100)
                    mfi = timeframe_data[tf].get('mfi', 100)
                    rsi_values.append(rsi)
                    mfi_values.append(mfi)
            
            if not rsi_values:
                return 999  # No data = lowest priority
            
            # Use minimum RSI/MFI across timeframes (most oversold)
            min_rsi = min(rsi_values)
            min_mfi = min(mfi_values)
            min_indicator = min(min_rsi, min_mfi)
            
            # Priority scoring:
            # < 20 = 0-19 (highest priority)
            # 20-30 = 20-29
            # 30-40 = 30-39
            # etc.
            return min_indicator
        
        # Sort by priority (lowest RSI/MFI first)
        signals_list_sorted = sorted(signals_list, key=get_signal_priority)
        
        self.telegram.send_message(
            f"📤 <b>Sending detailed analysis for {total_signals} signals...</b>\n"
            f"<i>Sorted by RSI/MFI (lowest first - best opportunities)</i>"
        )
        time.sleep(1)
        
        # Send ALL signals (no limit) - sorted by priority
        for i, signal in enumerate(signals_list_sorted, 1):
            # Send text alert only
            # Format price and market_data for display
            formatted_price = None
            try:
                formatted_price = self.binance.format_price(signal['symbol'], signal.get('price')) if signal.get('price') is not None else None
            except Exception:
                formatted_price = None
            md = signal.get('market_data')
            if md:
                md = md.copy()
                try:
                    md['high'] = self.binance.format_price(signal['symbol'], md.get('high'))
                    md['low'] = self.binance.format_price(signal['symbol'], md.get('low'))
                except Exception:
                    pass

            self.telegram.send_signal_alert(
                signal['symbol'],
                signal['timeframe_data'],
                signal['consensus'],
                signal['consensus_strength'],
                formatted_price,
                md,
                signal.get('volume_data')
            )
            
            # Add progress indicator every 10 coins
            if i % 10 == 0 and i < total_signals:
                remaining = total_signals - i
                self.telegram.send_message(f"⏳ Progress: {i}/{total_signals} sent, {remaining} remaining...")
            
            time.sleep(1)  # Delay between messages
        
        # Send completion message
        self.telegram.send_message(
            f"✅ <b>Analysis Complete!</b>\n"
            f"Sent detailed analysis for all {total_signals} signals"
        )
    
    def run(self):
        """Main bot loop - Commands only mode (no auto-scan)"""
        logger.info("Bot is now running in COMMAND-ONLY mode...")
        
        self.telegram.send_message(
            f"<b>🤖 BOT NOW RUNNING!</b>\n\n"
            f"<b>⚙️ MODE:</b> Command-Only (Auto-scan OFF)\n"
            f"<b>📊 Monitoring:</b> {config.QUOTE_ASSET} pairs\n"
            f"<b>🎯 Min Consensus:</b> {config.MIN_CONSENSUS_STRENGTH}/4\n"
            f"<b>⚡ Fast Scan:</b> {'✅ Enabled' if config.USE_FAST_SCAN else '❌ Disabled'}\n\n"
            f"<b>💬 AVAILABLE COMMANDS:</b>\n"
            f"• /<b>scan</b> - Run market scan\n"
            f"• /<b>BTC</b>, /<b>ETH</b> - Analyze coins\n"
            f"• /<b>help</b> - Show all commands\n\n"
            f"<i>💡 Use /scan to scan market anytime!</i>"
        )
        
        # Start command handler (blocking - this will run forever)
        try:
            logger.info("Starting command handler (blocking mode)...")
            self.command_handler.start_polling()
            
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            # Auto-backup trigger on exit
            if hasattr(self.command_handler, 'watchlist'):
                 self.command_handler.watchlist.save()
                 logger.info("✅ Watchlist saved on exit")
            if hasattr(self.command_handler, 'pump_detector') and hasattr(self.command_handler.pump_detector, '_save_history'):
                 self.command_handler.pump_detector._save_history()
                 logger.info("✅ Pump history saved on exit")
                 
            self.telegram.send_message("🛑 <b>Bot shutting down - Data Saved</b>")
            
        except Exception as e:
            logger.error(f"Error in command handler: {e}")
            self.telegram.send_message(f"❌ <b>Bot error:</b> {str(e)}")


def main():
    """Main entry point"""
    print("""
    RSI + MFI Multi-Timeframe Trading Bot
        Binance + Telegram Integration
    """)
    
    # Check if config is set
    if "your_" in config.BINANCE_API_KEY or "your_" in config.TELEGRAM_BOT_TOKEN:
        print("\n⚠️  WARNING: Please configure your API keys in config.py first!\n")
        sys.exit(1)
    
    # Start Telegram bot (no Flask API - no conflicts)
    bot = TradingBot()
    bot.run()


if __name__ == "__main__":
    main()



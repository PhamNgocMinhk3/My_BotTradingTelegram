"""
Market Scanner v2.0 - Advanced Detection Integration
Scans all Binance USDT pairs for extreme overbought/oversold RSI conditions on 1D timeframe
Alert condition: RSI only (MFI is calculated but not used for alerts)

Enhanced with Advanced Detection System:
- Institutional flow detection (accumulation/distribution)
- Volume legitimacy checks (VWAP, buy/sell pressure)
- 5 BOT type detection (Wash Trading, Spoofing, Iceberg, Market Maker, Dump)
- Direction probability calculation (UP/DOWN/SIDEWAYS)
- Risk assessment (LOW/MEDIUM/HIGH/EXTREME)
- Early entry signals 10-20 minutes before pump
"""

import logging
import time
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# Import advanced detection
try:
    from advanced_pump_detector import AdvancedPumpDumpDetector
    ADVANCED_DETECTOR_AVAILABLE = True
    logger.info("✅ Advanced Pump/Dump Detector available for MarketScanner")
except ImportError:
    ADVANCED_DETECTOR_AVAILABLE = False
    logger.warning("⚠️ Advanced Detector not available for MarketScanner")


class MarketScanner:
    def __init__(self, command_handler, scan_interval=900):
        """
        Initialize market scanner with advanced detection
        
        Args:
            command_handler: TelegramCommandHandler instance
            scan_interval: Scan interval in seconds (default: 900 = 15 minutes)
        """
        self.command_handler = command_handler
        self.binance = command_handler.binance
        self.bot = command_handler.bot
        self.bot_detector = command_handler.bot_detector  # Basic bot detector
        
        # Initialize Advanced Detector (NEW)
        self.advanced_detector = None
        if ADVANCED_DETECTOR_AVAILABLE:
            try:
                self.advanced_detector = AdvancedPumpDumpDetector(self.binance)
                logger.info("✅ Advanced Detector initialized for MarketScanner")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize Advanced Detector: {e}")
        
        self.scan_interval = scan_interval
        
        # Scanner state
        self.running = False
        self.thread = None
        self.last_alerts = {}  # Track last alerts to avoid duplicates
        
        # Extreme levels for 1D timeframe
        self.rsi_upper = 80
        self.rsi_lower = 20
        self.mfi_upper = 80
        self.mfi_lower = 20
        
        # Advanced detection thresholds
        self.advanced_confidence_threshold = 70  # Minimum confidence for advanced signals
        self.institutional_flow_threshold = 50   # Minimum institutional score
        
        detector_status = "with Advanced Detection" if self.advanced_detector else "basic mode"
        logger.info(f"✅ Market scanner v2.0 initialized {detector_status} (interval: {self.scan_interval}s, RSI: {self.rsi_lower}-{self.rsi_upper})")
    
    def start(self):
        """Start market scanner"""
        if self.running:
            logger.warning("Market scanner already running")
            return False
        
        self.running = True
        self.thread = threading.Thread(target=self._scan_loop, daemon=True)
        self.thread.start()
        
        logger.info("✅ Market scanner started")
        return True
    
    def stop(self):
        """Stop market scanner"""
        if not self.running:
            logger.warning("Market scanner not running")
            return False
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        
        logger.info("⛔ Market scanner stopped")
        return True
    
    def _scan_loop(self):
        """Main scanning loop"""
        logger.info("Market scanner loop started")
        
        while self.running:
            try:
                # Perform scan
                logger.info("🔍 Starting market scan...")
                start_time = time.time()
                
                extreme_coins = self._scan_market()
                
                scan_time = time.time() - start_time
                logger.info(f"✅ Market scan completed in {scan_time:.1f}s - Found {len(extreme_coins)} extreme coins")
                
                # Send alerts for extreme coins
                if extreme_coins:
                    self._send_alerts(extreme_coins)
                
                # Sleep until next scan
                if self.running:
                    logger.info(f"💤 Sleeping for {self.scan_interval}s until next scan...")
                    time.sleep(self.scan_interval)
                    
            except Exception as e:
                logger.error(f"Error in market scanner loop: {e}")
                if self.running:
                    time.sleep(60)  # Sleep 1 minute on error
        
        logger.info("Market scanner loop stopped")
    
    def _scan_market(self):
        """
        Scan all Binance USDT pairs for extreme RSI on 1D
        (MFI is calculated but only RSI determines alert condition)
        
        Returns:
            List of coins with extreme conditions
        """
        try:
            # Get all USDT trading pairs
            all_symbols_data = self.binance.get_all_symbols(quote_asset='USDT')
            
            if not all_symbols_data:
                logger.warning("No symbols found")
                return []
            
            # Extract just the symbol names
            all_symbols = [s['symbol'] for s in all_symbols_data]
            
            logger.info(f"Scanning {len(all_symbols)} USDT pairs...")
            
            extreme_coins = []
            
            # Use thread pool for parallel scanning
            max_workers = 10  # Limit concurrent requests
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all analysis tasks
                future_to_symbol = {
                    executor.submit(self._analyze_coin_1d, symbol): symbol 
                    for symbol in all_symbols
                }
                
                # Collect results
                for future in as_completed(future_to_symbol):
                    symbol = future_to_symbol[future]
                    try:
                        result = future.result()
                        if result and result.get('is_extreme'):
                            extreme_coins.append(result)
                            mfi_text = f", MFI: {result.get('mfi_1d', 0):.1f}" if result.get('mfi_1d') is not None else ""
                            logger.info(f"⚡ EXTREME: {symbol} - RSI: {result.get('rsi_1d', 0):.1f}{mfi_text}")
                    except Exception as e:
                        logger.debug(f"Error analyzing {symbol}: {e}")
            
            return extreme_coins
            
        except Exception as e:
            logger.error(f"Error scanning market: {e}")
            return []
    
    def _analyze_coin_1d(self, symbol):
        """
        Analyze single coin for extreme RSI on 1D timeframe
        (MFI is calculated for display but only RSI triggers alerts)
        Additionally performs bot detection and pump/dump analysis
        
        Args:
            symbol: Trading symbol
        
        Returns:
            dict with analysis or None
        """
        try:
            # Get 1D klines
            df_1d = self.binance.get_klines(symbol, '1d', limit=100)
            
            if df_1d is None or len(df_1d) < 14:
                return None
            
            # Validate data - check for NaN values in critical columns
            if df_1d[['high', 'low', 'close', 'volume']].isnull().any().any():
                logger.debug(f"Skipping {symbol} - contains invalid data")
                return None
            
            # Calculate both RSI and MFI for 1D (but only RSI for alert condition)
            from indicators import calculate_rsi, calculate_mfi, calculate_hlcc4
            
            hlcc4 = calculate_hlcc4(df_1d)
            rsi_1d = calculate_rsi(hlcc4, period=14)
            mfi_1d = calculate_mfi(df_1d, period=14)
            
            if rsi_1d is None:
                return None
            
            current_rsi = rsi_1d.iloc[-1]
            current_mfi = mfi_1d.iloc[-1] if mfi_1d is not None else None
            
            # Check if extreme (RSI only - MFI is ignored for alert condition)
            is_extreme = (
                current_rsi >= self.rsi_upper or 
                current_rsi <= self.rsi_lower
            )
            
            if not is_extreme:
                return None
            
            # Get current price
            current_price = df_1d['close'].iloc[-1]
            
            # Perform bot detection for extreme coins
            bot_detection = None
            try:
                bot_detection = self.bot_detector.detect_bot_activity(symbol)
                if bot_detection:
                    logger.info(f"🤖 Bot analysis for {symbol}: Bot={bot_detection.get('bot_score', 0):.1f}%, Pump={bot_detection.get('pump_score', 0):.1f}%")
            except Exception as e:
                logger.warning(f"Bot detection failed for {symbol}: {e}")
            
            # === ADVANCED DETECTION (NEW) ===
            advanced_result = None
            if self.advanced_detector:
                try:
                    # Run comprehensive advanced detection
                    advanced_result = self.advanced_detector.analyze_comprehensive(
                        symbol=symbol,
                        klines_5m=None,  # Will fetch internally if needed
                        klines_1h=None,
                        order_book=None,
                        trades=None,
                        market_data=None
                    )
                    
                    if advanced_result:
                        signal = advanced_result.get('signal', 'NEUTRAL')
                        confidence = advanced_result.get('confidence', 0)
                        direction_prob = advanced_result.get('direction_probability', {})
                        
                        logger.info(f"🎯 Advanced: {symbol} - Signal={signal}, Confidence={confidence}%, UP={direction_prob.get('up')}%")
                        
                        # Log institutional activity
                        inst_flow = advanced_result.get('institutional_flow', {})
                        if inst_flow.get('is_institutional'):
                            activity = inst_flow.get('activity_type', 'NONE')
                            logger.info(f"🐋 {symbol}: Institutional {activity} detected")
                        
                        # Log BOT warnings
                            if data.get('detected'):
                                logger.warning(f"🚨 {symbol}: {bot_type.upper()} BOT detected ({data.get('confidence')}%)")
                except Exception as e:
                    logger.error(f"Error in advanced detection for {symbol}: {e}")
            
            # Determine condition type (RSI only)
            conditions = []
            if current_rsi >= self.rsi_upper:
                conditions.append(f"RSI Overbought ({current_rsi:.1f})")
            if current_rsi <= self.rsi_lower:
                conditions.append(f"RSI Oversold ({current_rsi:.1f})")
            
            # Add bot/pump warnings if detected
            if bot_detection:
                bot_score = bot_detection.get('bot_score', 0)
                pump_score = bot_detection.get('pump_score', 0)
                
                if pump_score >= 45:  # Pump detected
                    conditions.append(f"⚠️ PUMP Pattern ({pump_score:.0f}%)")
                if bot_score >= 40:  # Bot activity detected
                    conditions.append(f"🤖 Bot Activity ({bot_score:.0f}%)")
            
            # === ADD ADVANCED DETECTION CONDITIONS (NEW) ===
            if advanced_result:
                signal = advanced_result.get('signal', 'NEUTRAL')
                confidence = advanced_result.get('confidence', 0)
                
                # Strong signals
                if signal == 'STRONG_PUMP' and confidence >= 75:
                    conditions.append(f"🚀 STRONG PUMP ({confidence:.0f}%)")
                elif signal == 'STRONG_DUMP':
                    conditions.append(f"🚨 STRONG DUMP ({confidence:.0f}%)")
                
                # Institutional activity
                inst_flow = advanced_result.get('institutional_flow', {})
                if inst_flow.get('is_institutional'):
                    activity = inst_flow.get('activity_type', 'NONE')
                    if activity == 'ACCUMULATION':
                        conditions.append(f"🐋 Institutional Accumulation")
                    elif activity == 'DISTRIBUTION':
                        conditions.append(f"🐋 Institutional Distribution")
                
                # Volume legitimacy warning
                vol_analysis = advanced_result.get('volume_analysis', {})
                if not vol_analysis.get('is_legitimate') and vol_analysis.get('legitimacy_score', 100) < 50:
                    conditions.append(f"⚠️ Fake Volume")
                
                # Critical BOT warnings
                bot_activity = advanced_result.get('bot_activity', {})
                if bot_activity.get('wash_trading', {}).get('detected'):
                    conditions.append(f"🚨 Wash Trading")
                if bot_activity.get('dump_bot', {}).get('detected'):
                    conditions.append(f"🚨 Dump BOT")
            
            return {
                'symbol': symbol,
                'is_extreme': True,
                'rsi_1d': current_rsi,
                'mfi_1d': current_mfi,  # Include MFI for display
                'price': current_price,
                'conditions': conditions,
                'bot_detection': bot_detection,  # Include full bot analysis
                'advanced_detection': advanced_result,  # NEW: Advanced detection results
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.debug(f"Error analyzing {symbol}: {e}")
            return None
    
    def _send_alerts(self, extreme_coins):
        """
        Send alerts for extreme coins
        
        Args:
            extreme_coins: List of extreme coin data
        """
        try:
            # Filter out recently alerted coins (avoid spam)
            new_alerts = []
            current_time = time.time()
            cooldown = 3600  # 1 hour cooldown per coin
            
            for coin in extreme_coins:
                symbol = coin['symbol']
                last_alert_time = self.last_alerts.get(symbol, 0)
                
                if current_time - last_alert_time > cooldown:
                    new_alerts.append(coin)
                    self.last_alerts[symbol] = current_time
            
            if not new_alerts:
                logger.info("No new alerts (all in cooldown period)")
                return
            
            # Send summary first in Vietnamese
            summary = f"<b>🔍 CẢNH BÁO QUÉT THỊ TRƯỜNG (v2.0)</b>\n\n"
            summary += f"⚡ Tìm thấy <b>{len(new_alerts)}</b> coin có RSI 1D cực đoan:\n\n"
            
            # Count bot/pump detections
            pump_count = sum(1 for c in new_alerts if c.get('bot_detection') and c['bot_detection'].get('pump_score', 0) >= 45)
            bot_count = sum(1 for c in new_alerts if c.get('bot_detection') and c['bot_detection'].get('bot_score', 0) >= 40)
            
            # Count advanced detection signals (NEW)
            strong_pump_count = sum(1 for c in new_alerts if c.get('advanced_detection') and c['advanced_detection'].get('signal') == 'STRONG_PUMP')
            institutional_count = sum(1 for c in new_alerts if c.get('advanced_detection') and c['advanced_detection'].get('institutional_flow', {}).get('is_institutional'))
            fake_volume_count = sum(1 for c in new_alerts if c.get('advanced_detection') and not c['advanced_detection'].get('volume_analysis', {}).get('is_legitimate'))
            
            for coin in new_alerts:
                symbol = coin['symbol']
                rsi = coin['rsi_1d']
                mfi = coin.get('mfi_1d')
                conditions_text = ", ".join(coin['conditions'])
                bot_data = coin.get('bot_detection')
                
                # Emoji based on condition and bot detection
                if rsi <= self.rsi_lower:
                    emoji = "🟢"  # Oversold - potential buy
                    if bot_data and bot_data.get('pump_score', 0) >= 45:
                        emoji = "🚀🟢"  # Pump + Oversold = Strong buy signal
                else:
                    emoji = "🔴"  # Overbought - potential sell
                    if bot_data and bot_data.get('pump_score', 0) >= 45:
                        emoji = "⚠️🔴"  # Pump + Overbought = Dump warning
                
                summary += f"{emoji} <b>{symbol}</b>\n"
                summary += f"   📊 RSI: {rsi:.1f}"
                if mfi is not None:
                    summary += f" | MFI: {mfi:.1f}"
                
                # Add bot/pump scores only if significant
                if bot_data:
                    bot_score = bot_data.get('bot_score', 0)
                    pump_score = bot_data.get('pump_score', 0)
                    if pump_score >= 20 or bot_score >= 20:
                        summary += f"\n   🤖 Bot: {bot_score:.0f}% | Pump: {pump_score:.0f}%"
                
                summary += f"\n   ⚡ {conditions_text}\n\n"
            
            # Add summary stats
            has_detections = (pump_count > 0 or bot_count > 0 or strong_pump_count > 0 or institutional_count > 0 or fake_volume_count > 0)
            
            if has_detections:
                summary += f"<b>⚠️ PHÁT HIỆN (Advanced Detection):</b>\n"
                if strong_pump_count > 0:
                    summary += f"🚀 {strong_pump_count} STRONG PUMP signals (confidence ≥75%)\n"
                if pump_count > 0:
                    summary += f"⚡ {pump_count} mẫu PUMP (basic detection)\n"
                if institutional_count > 0:
                    summary += f"🐋 {institutional_count} hoạt động Institutional\n"
                if bot_count > 0:
                    summary += f"🤖 {bot_count} hoạt động Bot\n"
                if fake_volume_count > 0:
                    summary += f"⚠️ {fake_volume_count} volume giả (wash trading)\n"
                summary += f"\n"
            
            summary += f"📤 Đang gửi phân tích chi tiết cho từng coin...\n"
            
            # Send detailed analysis for each coin (1D ONLY - no multi-timeframe)
            self.bot.send_message(summary)
            time.sleep(1)
            
            for coin in new_alerts:
                try:
                    # Send 1D analysis with bot detection
                    self._send_1d_analysis_with_bot(coin)
                    time.sleep(2)  # Rate limiting between coins
                except Exception as e:
                    logger.error(f"Error sending 1D analysis for {coin['symbol']}: {e}")
            
            logger.info(f"✅ Sent alerts for {len(new_alerts)} extreme coins")
            
        except Exception as e:
            logger.error(f"Error sending alerts: {e}")
    
    def _send_1d_analysis_with_bot(self, coin):
        """
        Send 1D analysis with ADVANCED DETECTION RESULTS
        
        Args:
            coin: Coin data dict with symbol, rsi_1d, mfi_1d, price, conditions, bot_detection, advanced_detection
        """
        try:
            symbol = coin['symbol']
            bot_detection = coin.get('bot_detection')
            advanced_result = coin.get('advanced_detection')  # NEW
            
            # Get only 1D klines
            df_1d = self.binance.get_klines(symbol, '1d', limit=100)
            
            if df_1d is None or len(df_1d) < 14:
                logger.warning(f"No 1D data for {symbol}")
                return
            
            # Calculate both RSI and MFI
            from indicators import calculate_rsi, calculate_mfi, calculate_hlcc4
            
            hlcc4 = calculate_hlcc4(df_1d)
            rsi_series = calculate_rsi(hlcc4, period=14)
            mfi_series = calculate_mfi(df_1d, period=14)
            
            # Get current values
            current_rsi = rsi_series.iloc[-1]
            current_mfi = mfi_series.iloc[-1] if mfi_series is not None else None
            last_rsi = rsi_series.iloc[-2] if len(rsi_series) >= 2 else current_rsi
            last_mfi = mfi_series.iloc[-2] if mfi_series is not None and len(mfi_series) >= 2 else current_mfi
            
            # Get signal based on both RSI and MFI (for display)
            from indicators import get_signal
            signal = get_signal(
                current_rsi, 
                current_mfi if current_mfi is not None else 50,  # Default MFI to neutral if None
                self.rsi_lower, 
                self.rsi_upper,
                self.mfi_lower, 
                self.mfi_upper
            )
            
            # Determine consensus with bot/pump consideration
            base_consensus = "BUY" if signal == 1 else ("SELL" if signal == -1 else "NEUTRAL")
            consensus_strength = 1 if signal != 0 else 0
            
            # Enhance signal with bot detection
            enhanced_signal = base_consensus
            if bot_detection:
                pump_score = bot_detection.get('pump_score', 0)
                bot_score = bot_detection.get('bot_score', 0)
                
                # Strong pump + oversold RSI = Strong BUY
                if pump_score >= 60 and current_rsi <= self.rsi_lower:
                    enhanced_signal = "🚀 STRONG BUY (PUMP + OVERSOLD)"
                    consensus_strength = 2
                # Pump + overbought RSI = DUMP WARNING
                elif pump_score >= 60 and current_rsi >= self.rsi_upper:
                    enhanced_signal = "⚠️ DUMP WARNING (PUMP + OVERBOUGHT)"
                    consensus_strength = 2
                # High bot activity + signal
                elif bot_score >= 70:
                    if base_consensus == "BUY":
                        enhanced_signal = "🤖 BOT BUY SIGNAL"
                    elif base_consensus == "SELL":
                        enhanced_signal = "🤖 BOT SELL SIGNAL"
            
            # Get price and market data
            price = self.binance.get_current_price(symbol)
            market_data = self.binance.get_24h_data(symbol)
            
            # Map signal names to Vietnamese
            signal_map = {
                "BUY": "MUA",
                "SELL": "BÁN", 
                "NEUTRAL": "TRUNG LẬP",
                "🚀 STRONG BUY (PUMP + OVERSOLD)": "🚀 MUA MẠNH (PUMP + QUÁ BÁN)",
                "⚠️ DUMP WARNING (PUMP + OVERBOUGHT)": "⚠️ CẢNH BÁO DUMP (PUMP + QUÁ MUA)",
                "🤖 BOT BUY SIGNAL": "🤖 TÍN HIỆU MUA BOT",
                "🤖 BOT SELL SIGNAL": "🤖 TÍN HIỆU BÁN BOT"
            }
            enhanced_signal_vi = signal_map.get(enhanced_signal, enhanced_signal)
            
            # Build enhanced message with bot analysis in Vietnamese
            msg = f"<b>📊 {symbol} - QUÉT THỊ TRƯỜNG + PHÂN TÍCH BOT</b>\n\n"
            
            # RSI/MFI Section
            msg += f"<b>📈 Chỉ Báo Kỹ Thuật (1D):</b>\n"
            rsi_change_text = f"({'+' if current_rsi > last_rsi else ''}{current_rsi - last_rsi:.2f})"
            msg += f"RSI: {current_rsi:.2f} {rsi_change_text}\n"
            if current_mfi is not None:
                mfi_change_text = f"({'+' if current_mfi > last_mfi else ''}{current_mfi - last_mfi:.2f})"
                msg += f"MFI: {current_mfi:.2f} {mfi_change_text}\n"
            
            # Signal
            msg += f"\n<b>📍 Tín Hiệu: {enhanced_signal_vi}</b>\n"
            
            # === ADVANCED DETECTION SECTION (NEW) ===
            if advanced_result:
                signal_adv = advanced_result.get('signal', 'NEUTRAL')
                confidence = advanced_result.get('confidence', 0)
                direction_prob = advanced_result.get('direction_probability', {})
                risk_level = advanced_result.get('risk_level', 'MEDIUM')
                
                # Show advanced signal if significant
                if confidence >= 60:
                    msg += f"\n<b>🎯 ADVANCED DETECTION (v4.0):</b>\n"
                    msg += f"Signal: <b>{signal_adv}</b> (Confidence: {confidence}%)\n"
                    msg += f"Direction: ⬆️{direction_prob.get('up', 0)}% | ⬇️{direction_prob.get('down', 0)}% | ➡️{direction_prob.get('sideways', 0)}%\n"
                    msg += f"Risk Level: {risk_level}\n"
                
                # Institutional Flow
                inst_flow = advanced_result.get('institutional_flow', {})
                if inst_flow.get('is_institutional'):
                    activity = inst_flow.get('activity_type', 'NONE')
                    smart_flow = inst_flow.get('smart_money_flow', 'NEUTRAL')
                    
                    msg += f"\n<b>🐋 INSTITUTIONAL FLOW:</b>\n"
                    msg += f"Activity: <b>{activity}</b>\n"
                    msg += f"Smart Money: {smart_flow}\n"
                    
                    if activity == 'ACCUMULATION' and current_rsi <= self.rsi_lower:
                        msg += f"\n💎 <b>CƠ HỘI VÀNG!</b>\n"
                        msg += f"   • Tổ chức đang tích lũy\n"
                        msg += f"   • RSI quá bán\n"
                        msg += f"   • Có thể vào lệnh sớm 10-20 phút\n"
                    elif activity == 'DISTRIBUTION' and current_rsi >= self.rsi_upper:
                        msg += f"\n⚠️ <b>CẢNH BÁO THOÁT!</b>\n"
                        msg += f"   • Tổ chức đang phân phối\n"
                        msg += f"   • RSI quá mua\n"
                        msg += f"   • Cân nhắc chốt lời / thoát lệnh\n"
                
                # Volume Legitimacy
                vol_analysis = advanced_result.get('volume_analysis', {})
                if not vol_analysis.get('is_legitimate'):
                    legitimacy_score = vol_analysis.get('legitimacy_score', 0)
                    volume_quality = vol_analysis.get('volume_quality', 'UNKNOWN')
                    
                    msg += f"\n<b>⚠️ CẢNH BÁO VOLUME:</b>\n"
                    msg += f"Legitimacy: {legitimacy_score}/100 ({volume_quality})\n"
                    msg += f"⚠️ Volume có thể giả - Thận trọng!\n"
                
                # BOT Activity Warnings
                bot_activity = advanced_result.get('bot_activity', {})
                detected_bots = [k for k, v in bot_activity.items() if isinstance(v, dict) and v.get('detected')]
                
                if detected_bots:
                    msg += f"\n<b>🚨 BOT ACTIVITY DETECTED:</b>\n"
                    for bot_type in detected_bots:
                        conf = bot_activity[bot_type].get('confidence', 0)
                        bot_name_map = {
                            'wash_trading': 'Wash Trading',
                            'spoofing': 'Spoofing',
                            'iceberg': 'Iceberg BOT',
                            'market_maker': 'Market Maker',
                            'dump_bot': 'Dump BOT'
                        }
                        bot_name = bot_name_map.get(bot_type, bot_type)
                        msg += f"• {bot_name}: {conf}%\n"
                    
                    msg += f"\n⚠️ Thị trường bị thao túng - TRÁNH TRADE!\n"
                
                # Recommendation
                recommendation = advanced_result.get('recommendation', {})
                action = recommendation.get('action', 'WAIT')
                
                if action in ['BUY', 'SELL'] and confidence >= 70:
                    msg += f"\n<b>💡 KHUYẾN NGHỊ:</b>\n"
                    msg += f"Action: <b>{action}</b>\n"
                    msg += f"Position Size: {recommendation.get('position_size', 'N/A')}\n"
                    
                    reasoning = recommendation.get('reasoning', [])
                    if reasoning:
                        msg += f"Lý do:\n"
                        for reason in reasoning[:3]:  # Show first 3 reasons
                            msg += f"  {reason}\n"
            
            # Bot Detection Section - Only show if detected (basic)
            elif bot_detection:  # Only show if no advanced detection
                bot_score = bot_detection.get('bot_score', 0)
                pump_score = bot_detection.get('pump_score', 0)
                
                # Only show bot analysis if there's something detected
                if bot_score >= 20 or pump_score >= 20:
                    msg += f"\n<b>🤖 PHÂN TÍCH BOT (Basic):</b>\n"
                    
                    if bot_score >= 20:
                        status = "✅ PHÁT HIỆN" if bot_score >= 40 else "⚠️ Có dấu hiệu"
                        msg += f"Hoạt động Bot: {bot_score:.1f}% {status}\n"
                    
                    if pump_score >= 20:
                        status = "🚀 PHÁT HIỆN" if pump_score >= 45 else "⚠️ Có dấu hiệu"
                        msg += f"Mẫu Pump: {pump_score:.1f}% {status}\n"
                
                # Add specific warnings
                if pump_score >= 60 and current_rsi <= self.rsi_lower:
                    msg += f"\n⚡ <b>CƠ HỘI VÀO LỆNH SỚM!</b>\n"
                    msg += f"   • Mẫu pump đang hình thành\n"
                    msg += f"   • RSI quá bán - có thể tăng\n"
                    msg += f"   • Cân nhắc vào lệnh trong 3 phút\n"
                elif pump_score >= 60 and current_rsi >= self.rsi_upper:
                    msg += f"\n⚠️ <b>CẢNH BÁO DUMP!</b>\n"
                    msg += f"   • Mẫu pump + Quá mua\n"
                    msg += f"   • Rủi ro dump cao\n"
                    msg += f"   • Tránh mua / Cân nhắc thoát lệnh\n"
                elif bot_score >= 70:
                    msg += f"\n🤖 <b>HOẠT ĐỘNG BOT CAO!</b>\n"
                    msg += f"   • Có thể bị thao túng\n"
                    msg += f"   • Theo dõi biến động đột ngột\n"
            
            # Price and Market Data - Only show meaningful data
            if price and market_data:
                msg += f"\n<b>💰 Thông Tin Giá:</b>\n"
                msg += f"Giá hiện tại: ${price:,.8f}\n"
                
                change_24h = float(market_data.get('priceChangePercent', 0))
                if abs(change_24h) >= 0.01:  # Only show if change >= 0.01%
                    change_emoji = "📈" if change_24h > 0 else "📉" if change_24h < 0 else "➡️"
                    msg += f"Thay đổi 24h: {change_emoji} {change_24h:+.2f}%\n"
                
                volume_24h = float(market_data.get('quoteVolume', 0))
                if volume_24h >= 1000:  # Only show if volume >= $1000
                    msg += f"Khối lượng 24h: ${volume_24h:,.0f}\n"
            
            self.bot.send_message(msg)
            logger.info(f"✅ Sent 1D analysis with bot detection for {symbol}")
            
        except Exception as e:
            logger.error(f"Error in 1D analysis with bot detection for {coin.get('symbol', 'UNKNOWN')}: {e}")
    
    def _send_1d_analysis(self, coin):
        """
        Send 1D analysis for a coin (calculates both RSI and MFI, shows both)
        
        Args:
            coin: Coin data dict with symbol, rsi_1d, mfi_1d, price, conditions
        """
        try:
            symbol = coin['symbol']
            
            # Get only 1D klines
            df_1d = self.binance.get_klines(symbol, '1d', limit=100)
            
            if df_1d is None or len(df_1d) < 14:
                logger.warning(f"No 1D data for {symbol}")
                return
            
            # Calculate both RSI and MFI
            from indicators import calculate_rsi, calculate_mfi, calculate_hlcc4
            
            hlcc4 = calculate_hlcc4(df_1d)
            rsi_series = calculate_rsi(hlcc4, period=14)
            mfi_series = calculate_mfi(df_1d, period=14)
            
            # Get current values
            current_rsi = rsi_series.iloc[-1]
            current_mfi = mfi_series.iloc[-1] if mfi_series is not None else None
            last_rsi = rsi_series.iloc[-2] if len(rsi_series) >= 2 else current_rsi
            last_mfi = mfi_series.iloc[-2] if mfi_series is not None and len(mfi_series) >= 2 else current_mfi
            
            # Get signal based on both RSI and MFI (for display)
            from indicators import get_signal
            signal = get_signal(
                current_rsi, 
                current_mfi if current_mfi is not None else 50,  # Default MFI to neutral if None
                self.rsi_lower, 
                self.rsi_upper,
                self.mfi_lower, 
                self.mfi_upper
            )
            
            # Determine consensus
            if signal == 1:
                consensus = "BUY"
                consensus_strength = 1
            elif signal == -1:
                consensus = "SELL"
                consensus_strength = 1
            else:
                consensus = "NEUTRAL"
                consensus_strength = 0
            
            # Get price and market data
            price = self.binance.get_current_price(symbol)
            market_data = self.binance.get_24h_data(symbol)
            
            # Build timeframe_data with ONLY 1D (includes both RSI and MFI)
            timeframe_data = {
                '1d': {
                    'rsi': round(current_rsi, 2),
                    'mfi': round(current_mfi, 2) if current_mfi is not None else None,
                    'last_rsi': round(last_rsi, 2),
                    'last_mfi': round(last_mfi, 2) if last_mfi is not None else None,
                    'rsi_change': round(current_rsi - last_rsi, 2),
                    'mfi_change': round(current_mfi - last_mfi, 2) if current_mfi is not None and last_mfi is not None else None,
                    'signal': signal
                }
            }
            
            # Send alert with ONLY 1D timeframe (format prices for display)
            formatted_price = None
            try:
                formatted_price = self.binance.format_price(symbol, price) if price is not None else None
            except Exception:
                formatted_price = None
            md = market_data
            if md:
                md = md.copy()
                try:
                    md['high'] = self.binance.format_price(symbol, md.get('high'))
                    md['low'] = self.binance.format_price(symbol, md.get('low'))
                except Exception:
                    pass

            self.bot.send_signal_alert(
                symbol,
                timeframe_data,
                consensus,
                consensus_strength,
                formatted_price,
                md,
                None  # No volume data for market scanner
            )
            
            logger.info(f"✅ Sent 1D analysis for {symbol}")
            
        except Exception as e:
            logger.error(f"Error in 1D analysis for {coin.get('symbol', 'UNKNOWN')}: {e}")
    
    def _send_detailed_analysis(self, symbol):
        """
        Send detailed multi-timeframe analysis for symbol
        
        Args:
            symbol: Trading symbol
        """
        try:
            # Use command handler's analysis function
            result = self.command_handler._analyze_symbol_full(symbol)

            if result:
                # Format price and market_data for display
                formatted_price = None
                try:
                    formatted_price = self.command_handler.binance.format_price(result['symbol'], result.get('price')) if result.get('price') is not None else None
                except Exception:
                    formatted_price = None
                md = result.get('market_data')
                if md:
                    md = md.copy()
                    try:
                        md['high'] = self.command_handler.binance.format_price(result['symbol'], md.get('high'))
                        md['low'] = self.command_handler.binance.format_price(result['symbol'], md.get('low'))
                    except Exception:
                        pass

                self.bot.send_signal_alert(
                    result['symbol'],
                    result['timeframe_data'],
                    result['consensus'],
                    result['consensus_strength'],
                    formatted_price,
                    md,
                    result.get('volume_data')
                )
                logger.info(f"✅ Sent detailed analysis for {symbol}")
            else:
                logger.warning(f"Failed to analyze {symbol}")
                
        except Exception as e:
            logger.error(f"Error in detailed analysis for {symbol}: {e}")
    
    def get_status(self):
        """
        Get scanner status
        
        Returns:
            dict with status info
        """
        return {
            'running': self.running,
            'scan_interval': self.scan_interval,
            'rsi_levels': f"{self.rsi_lower}-{self.rsi_upper}",
            'mfi_levels': f"{self.mfi_lower}-{self.mfi_upper}",
            'tracked_coins': len(self.last_alerts),
            'cooldown': '1 hour'
        }

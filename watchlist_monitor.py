"""
Watchlist Monitor v2.0 - PUMP FOCUSED
Monitors watchlist coins for PUMP signals instead of generic RSI/MFI buy/sell alerts.

Key indicators tracked:
- Volume Spike (5m & 1H)
- OBV (On Balance Volume) trend
- Order Book Imbalance (Buy/Sell ratio)
- Cost to push price 5% (Liquidity depth)
- RSI Momentum
- Buy Pressure (green candle ratio)
"""

import logging
import time
import json
import os
import numpy as np
from datetime import datetime
from threading import Thread
from concurrent.futures import ThreadPoolExecutor, as_completed
from indicators import calculate_mfi  # Added for Smart Eviction

logger = logging.getLogger(__name__)


class WatchlistMonitor:
    def __init__(self, command_handler, check_interval=300, volume_check_interval=60):
        """
        Initialize watchlist monitor
        
        Args:
            command_handler: TelegramCommandHandler instance
            check_interval: Pump check interval in seconds (default: 300 = 5 minutes)
            volume_check_interval: Quick volume check interval (default: 60 = 1 minute)
        """
        self.command_handler = command_handler
        self.check_interval = check_interval
        self.volume_check_interval = volume_check_interval
        self.running = False
        self.thread = None
        self.volume_thread = None
        self.last_signals = {}  # Track last signals to avoid duplicates
        self.last_volume_alerts = {}  # Track volume alerts
        self.signal_history_file = 'watchlist_signals_history.json'
        self.volume_history_file = 'watchlist_volume_history.json'
        
        # Initialize volume detector (keep for volume spike detection)
        from volume_detector import VolumeDetector
        self.volume_detector = VolumeDetector(
            command_handler.binance,
            sensitivity='medium'
        )
        
        # Load signal history
        self.load_history()
        
        logger.info(f"Watchlist Monitor v2.0 (PUMP FOCUSED) initialized")
        logger.info(f"  • Pump scan: {check_interval}s, Volume scan: {volume_check_interval}s")

    def load_history(self):
        """Load signal history from file"""
        try:
            if os.path.exists(self.signal_history_file):
                with open(self.signal_history_file, 'r') as f:
                    data = json.load(f)
                    self.last_signals = data.get('signals', {})
                    logger.info(f"Loaded {len(self.last_signals)} signal history entries")
        except Exception as e:
            logger.error(f"Error loading signal history: {e}")
            self.last_signals = {}
        
        try:
            if os.path.exists(self.volume_history_file):
                with open(self.volume_history_file, 'r') as f:
                    data = json.load(f)
                    self.last_volume_alerts = data.get('alerts', {})
                    logger.info(f"Loaded {len(self.last_volume_alerts)} volume alert history entries")
        except Exception as e:
            logger.error(f"Error loading volume history: {e}")
            self.last_volume_alerts = {}
    
    def save_history(self):
        """Save signal history to file"""
        try:
            with open(self.signal_history_file, 'w') as f:
                json.dump({'signals': self.last_signals}, f)
        except Exception as e:
            logger.error(f"Error saving signal history: {e}")
            
        try:
            with open(self.volume_history_file, 'w') as f:
                json.dump({'alerts': self.last_volume_alerts}, f)
        except Exception as e:
            logger.error(f"Error saving volume history: {e}")
    
    def start(self):
        """Start monitoring watchlist"""
        if self.running:
            logger.warning("Watchlist monitor already running")
            return
        
        self.running = True
        
        # Start pump monitoring thread
        self.thread = Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        
        # Start volume monitoring thread (more frequent)
        self.volume_thread = Thread(target=self._volume_monitor_loop, daemon=True)
        self.volume_thread.start()
        
        logger.info("✅ Watchlist pump monitor started")
    
    def stop(self):
        """Stop monitoring watchlist"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        if self.volume_thread:
            self.volume_thread.join(timeout=5)
        logger.info("⛔ Watchlist pump monitor stopped")

    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                self.check_watchlist()
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
            
            # Sleep in small intervals to allow quick shutdown
            for _ in range(self.check_interval):
                if not self.running:
                    break
                time.sleep(1)

    # ================================================================
    # PUMP-FOCUSED ANALYSIS (REPLACES OLD RSI/MFI SIGNAL LOGIC)
    # ================================================================

    def _analyze_pump_signals(self, symbol):
        """
        Analyze a single coin for PUMP potential.
        Returns dict with all pump indicators or None.
        """
        try:
            binance = self.command_handler.binance
            
            # Get klines for multiple timeframes
            df_5m = binance.get_klines(symbol, '5m', limit=100)
            df_1h = binance.get_klines(symbol, '1h', limit=50)
            
            if df_5m is None or len(df_5m) < 20:
                return None
            
            current_price = float(df_5m['close'].iloc[-1])
            
            # ---- 1. VOLUME SPIKE (5m) ----
            vol_current_5m = float(df_5m['volume'].iloc[-1])
            vol_avg_20 = float(df_5m['volume'].rolling(20).mean().iloc[-1])
            vol_spike_5m = vol_current_5m / vol_avg_20 if vol_avg_20 > 0 else 0
            
            # ---- 2. VOLUME SPIKE (1H) ----
            vol_spike_1h = 0
            if df_1h is not None and len(df_1h) >= 20:
                vol_current_1h = float(df_1h['volume'].iloc[-1])
                vol_avg_1h = float(df_1h['volume'].rolling(20).mean().iloc[-1])
                vol_spike_1h = vol_current_1h / vol_avg_1h if vol_avg_1h > 0 else 0
            
            # ---- 3. PRICE CHANGES ----
            price_5m_ago = float(df_5m['close'].iloc[-2])
            price_30m_ago = float(df_5m['close'].iloc[-7]) if len(df_5m) >= 7 else price_5m_ago
            price_1h_ago = float(df_5m['close'].iloc[-13]) if len(df_5m) >= 13 else price_5m_ago
            
            chg_5m = ((current_price - price_5m_ago) / price_5m_ago) * 100
            chg_30m = ((current_price - price_30m_ago) / price_30m_ago) * 100
            chg_1h = ((current_price - price_1h_ago) / price_1h_ago) * 100
            
            # ---- 4. RSI (5m) ----
            delta = df_5m['close'].diff()
            gain = delta.where(delta > 0, 0.0)
            loss = -delta.where(delta < 0, 0.0)
            avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
            avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
            rs = avg_gain / avg_loss
            rsi_series = 100 - (100 / (1 + rs))
            rsi_current = float(rsi_series.iloc[-1])
            rsi_prev = float(rsi_series.iloc[-4]) if len(rsi_series) >= 4 else rsi_current
            rsi_momentum = rsi_current - rsi_prev
            
            # RSI 1H
            rsi_1h = 50
            if df_1h is not None and len(df_1h) >= 20:
                delta_1h = df_1h['close'].diff()
                gain_1h = delta_1h.where(delta_1h > 0, 0.0)
                loss_1h = -delta_1h.where(delta_1h < 0, 0.0)
                avg_gain_1h = gain_1h.ewm(alpha=1/14, adjust=False).mean()
                avg_loss_1h = loss_1h.ewm(alpha=1/14, adjust=False).mean()
                rs_1h = avg_gain_1h / avg_loss_1h
                rsi_1h_series = 100 - (100 / (1 + rs_1h))
                rsi_1h = float(rsi_1h_series.iloc[-1])
            
            # ---- 5. OBV TREND ----
            obv_values = (np.sign(df_5m['close'].diff().fillna(0)) * df_5m['volume']).cumsum()
            obv_current = float(obv_values.iloc[-1])
            obv_10_ago = float(obv_values.iloc[-10]) if len(obv_values) >= 10 else 0
            obv_trend = "INFLOW" if obv_current > obv_10_ago else "OUTFLOW"
            obv_change = obv_current - obv_10_ago
            
            # ---- 6. BUY PRESSURE ----
            buy_candles = sum(1 for i in range(len(df_5m)-20, len(df_5m))
                            if float(df_5m['close'].iloc[i]) > float(df_5m['open'].iloc[i]))
            buy_ratio = buy_candles / 20
            
            # ---- 6b. TAKER BUY RATIO (NEW — aligned with momentum detection) ----
            taker_buy_ratio = 0.5
            try:
                last_vol = float(df_5m['quote_volume'].iloc[-1])
                last_buy = float(df_5m.iloc[-1].get('taker_buy_quote', 0))
                taker_buy_ratio = last_buy / last_vol if last_vol > 0 else 0.5
            except:
                pass
            
            # ---- 6c. CONSECUTIVE WHALE BUY (NEW — Signal 5 from momentum) ----
            consecutive_whale = 0
            max_consecutive = 0
            for ci in range(max(0, len(df_5m)-6), len(df_5m)):
                c = df_5m.iloc[ci]
                cv = float(c['quote_volume'])
                cb = float(c.get('taker_buy_quote', 0))
                cr = cb / cv if cv > 0 else 0.5
                if cr > 0.60:
                    consecutive_whale += 1
                    max_consecutive = max(max_consecutive, consecutive_whale)
                else:
                    consecutive_whale = 0
            
            # ---- 7. ORDER BOOK ----
            ob_ratio = 0
            cost_5pct = 0
            try:
                depth = binance.get_order_book(symbol)
                if depth:
                    bids = depth['bids'][:20]
                    asks = depth['asks'][:20]
                    bid_vol = sum(float(b[1]) for b in bids)
                    ask_vol = sum(float(a[1]) for a in asks)
                    ob_ratio = bid_vol / ask_vol if ask_vol > 0 else 0
                    
                    # Cost to push price +5%
                    target_price = current_price * 1.05
                    for ask in depth['asks']:
                        if float(ask[0]) <= target_price:
                            cost_5pct += float(ask[0]) * float(ask[1])
                        else:
                            break
            except Exception as e:
                logger.debug(f"Order book error for {symbol}: {e}")
            
            # ---- 8. 24H DATA ----
            market_data = binance.get_24h_data(symbol)
            chg_24h = float(market_data.get('change_pct', 0)) if market_data else 0
            volume_24h = float(market_data.get('volume_usd', 0)) if market_data else 0
            
            # ---- PUMP SCORE CALCULATION ----
            pump_score = 0
            pump_signals = []
            
            # Volume spike (max 25)
            if vol_spike_5m > 3:
                pump_score += 25
                pump_signals.append(f"🔥 Vol Spike 5m: {vol_spike_5m:.1f}x")
            elif vol_spike_5m > 2:
                pump_score += 15
                pump_signals.append(f"📊 Vol Spike 5m: {vol_spike_5m:.1f}x")
            elif vol_spike_5m > 1.5:
                pump_score += 8
                
            # Volume spike 1H (max 20)
            if vol_spike_1h > 3:
                pump_score += 20
                pump_signals.append(f"🔥 Vol Spike 1H: {vol_spike_1h:.1f}x")
            elif vol_spike_1h > 2:
                pump_score += 12
                pump_signals.append(f"📊 Vol Spike 1H: {vol_spike_1h:.1f}x")
            
            # Price momentum (max 15)
            if chg_1h > 5:
                pump_score += 15
                pump_signals.append(f"🚀 Price 1H: {chg_1h:+.2f}%")
            elif chg_30m > 3:
                pump_score += 10
                pump_signals.append(f"📈 Price 30m: {chg_30m:+.2f}%")
            
            # OBV inflow (max 15)
            if obv_change > 0:
                pump_score += 15
                pump_signals.append(f"💰 OBV: Dòng tiền VÀO")
            
            # Taker Buy dominance (max 15) — NEW
            if taker_buy_ratio > 0.70:
                pump_score += 15
                pump_signals.append(f"🐋 Buy: {taker_buy_ratio*100:.0f}% (Cá mập!)")
            elif taker_buy_ratio > 0.65:
                pump_score += 10
                pump_signals.append(f"🐋 Buy: {taker_buy_ratio*100:.0f}%")
            
            # Consecutive whale buy (max 15) — NEW
            if max_consecutive >= 3:
                pump_score += 15
                pump_signals.append(f"🐋🐋 Whale: {max_consecutive} nến liên tiếp")
            
            # Order book imbalance (max 15)
            if ob_ratio > 3:
                pump_score += 15
                pump_signals.append(f"🧱 Cạn cung: Buy/Sell = {ob_ratio:.1f}x")
            elif ob_ratio > 2:
                pump_score += 10
                pump_signals.append(f"💪 Buy wall mạnh: {ob_ratio:.1f}x")
            
            # Thin liquidity (max 10)
            if 0 < cost_5pct < 50000:
                pump_score += 10
                pump_signals.append(f"🐋 Thanh khoản mỏng: ${cost_5pct:,.0f}/5%")
            elif 0 < cost_5pct < 200000:
                pump_score += 5
            
            return {
                'symbol': symbol,
                'price': current_price,
                'pump_score': pump_score,
                'pump_signals': pump_signals,
                # Raw data
                'vol_spike_5m': vol_spike_5m,
                'vol_spike_1h': vol_spike_1h,
                'chg_5m': chg_5m,
                'chg_30m': chg_30m,
                'chg_1h': chg_1h,
                'chg_24h': chg_24h,
                'rsi_5m': rsi_current,
                'rsi_1h': rsi_1h,
                'rsi_momentum': rsi_momentum,
                'obv_trend': obv_trend,
                'obv_change': obv_change,
                'buy_ratio': buy_ratio,
                'taker_buy_ratio': taker_buy_ratio,
                'max_consecutive_whale': max_consecutive,
                'ob_ratio': ob_ratio,
                'cost_5pct': cost_5pct,
                'volume_24h': volume_24h,
            }
            
        except Exception as e:
            logger.error(f"Error analyzing pump for {symbol}: {e}")
            return None

    def check_watchlist(self):
        """Check watchlist for PUMP signals (replaces old RSI/MFI check)"""
        try:
            # === SMART CLEANER: REMOVE FAILED COINS FIRST ===
            self._clean_watchlist()
            
            symbols = self.command_handler.watchlist.get_all()
            
            if not symbols:
                logger.debug("Watchlist is empty, skipping check")
                return
            
            logger.info(f"🔍 Pump scanning {len(symbols)} watchlist coins...")
            
            results = []
            
            # Analyze all symbols concurrently
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {executor.submit(self._analyze_pump_signals, sym): sym for sym in symbols}
                
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        if result:
                            results.append(result)
                    except Exception as e:
                        logger.debug(f"Pump analysis error: {e}")
            
            if not results:
                logger.info("No pump data retrieved")
                return
            
            # --- TARGET TRACKING (preserved from v1) ---
            for result in results:
                symbol = result['symbol']
                current_price = result['price']
                
                details = self.command_handler.watchlist.get_details(symbol)
                if details and current_price:
                    entry_price = details.get('price', 0)
                    if entry_price > 0:
                        gain_pct = ((current_price - entry_price) / entry_price) * 100
                        gain_key = f"{symbol}_gain"
                        last_gain_alert = self.last_volume_alerts.get(gain_key, 0)
                        
                        if gain_pct >= 50:
                            alert_msg = (
                                f"🚀 <b>MOONSHOT! {symbol} (+{gain_pct:.2f}%)</b>\n\n"
                                f"💰 Entry: {entry_price}\n"
                                f"💰 Hiện tại: {current_price}\n"
                                f"✅ Đã gỡ khỏi Watchlist"
                            )
                            self.command_handler.bot.send_message(alert_msg)
                            self.command_handler.watchlist.remove(symbol)
                            continue
                            
                        elif gain_pct >= 20 and (time.time() - last_gain_alert > 7200):
                            alert_msg = (
                                f"🔥 <b>HUGE MOVE: {symbol} (+{gain_pct:.2f}%)</b>\n\n"
                                f"💰 Entry: {entry_price}\n"
                                f"💰 Hiện tại: {current_price}\n"
                                f"🚀 Target tiếp: +50%"
                            )
                            self.command_handler.bot.send_message(alert_msg)
                            self.last_volume_alerts[gain_key] = time.time() # Update 20% alert time

                        elif gain_pct >= 10 and (time.time() - last_gain_alert > 3600):
                            alert_msg = (
                                f"📈 <b>BREAKOUT: {symbol} (+{gain_pct:.2f}%)</b>\n\n"
                                f"💰 Entry: {entry_price}\n"
                                f"💰 Hiện tại: {current_price}\n"
                                f"⏳ Giữ chờ +20%"
                            )
                            self.command_handler.bot.send_message(alert_msg)
                            self.last_volume_alerts[gain_key] = time.time() # Update 10% alert time
            
            # --- PUMP SIGNAL NOTIFICATIONS ---
            # Sort by pump score descending
            results.sort(key=lambda x: x['pump_score'], reverse=True)
            
            # Send a consolidated pump dashboard for all watchlist coins
            self._send_pump_dashboard(results)
            
            self.save_history()
            
        except Exception as e:
            logger.error(f"Error checking watchlist: {e}")

    def _clean_watchlist(self):
        """
        SMART CLEANER v2.0 - Strict Eviction
        Removes coins that are failing, stagnant, or seeing money outflow.
        """
        try:
            symbols = self.command_handler.watchlist.get_all()
            if not symbols:
                return

            removed_count = 0
            
            # Batch fetch all prices to avoid rate limits and correct errors
            try:
                all_tickers = self.command_handler.binance.client.get_all_tickers()
                price_map = {t['symbol']: float(t['price']) for t in all_tickers}
            except Exception as e:
                logger.error(f"Error fetching all tickers for cleanup: {e}")
                return

            binance = self.command_handler.binance

            for symbol in symbols:
                try:
                    details = self.command_handler.watchlist.get_details(symbol)
                    if not details:
                        continue
                        
                    entry_price = details.get('price', 0)
                    added_time = details.get('time', 0)
                    time_in_list = time.time() - added_time
                    
                    # Get current price from batch map
                    current_price = price_map.get(symbol)
                    
                    if not current_price:
                        continue

                    reason = None
                    
                    # 1. STOP LOSS (> 5% drop)
                    if entry_price > 0 and current_price < entry_price * 0.95:
                        loss_pct = ((entry_price - current_price) / entry_price) * 100
                        reason = f"❌ STOP LOSS (-{loss_pct:.1f}%)"
                    
                    # 2. IMMEDIATE REVERSAL (> 1h and Price < Entry)
                    elif time_in_list > 3600 and current_price < entry_price * 0.98:
                         # 2% drop after 1 hour is a failed pump
                        reason = f"📉 Failed Pump (Drop 2% after 1h)"

                    # 3. QUICK STAGNATION (> 4h and < 0.5% gain)
                    elif time_in_list > 14400 and current_price < entry_price * 1.005:
                        reason = f"💤 Stagnation (> 4h no move)"
                        
                    # 4. MONEY FLOW CHECK (If none of above)
                    elif time_in_list > 1800: # Give it 30 mins grace period
                        # Get 1h klines to check MFI
                        klines = binance.get_klines(symbol, '1h', limit=24)
                        if klines is not None and len(klines) >= 14:
                            mfi = calculate_mfi(klines, period=14)
                            if mfi is not None:
                                current_mfi = mfi.iloc[-1]
                                
                                # CRITERIA: MFI < 30 (Money Leaving)
                                if current_mfi < 30:
                                    reason = f"💸 Money Outflow (MFI {current_mfi:.0f} < 30)"

                    if reason:
                        msg = (
                            f"🗑️ <b>SMART CLEANER: {symbol}</b>\n"
                            f"Reason: {reason}\n"
                            f"Price: {current_price}\n"
                            f"Removed from Watchlist."
                        )
                        self.command_handler.bot.send_message(msg)
                        self.command_handler.watchlist.remove(symbol)
                        removed_count += 1
                        logger.info(f"Smart Cleaner removed {symbol}: {reason}")

                except Exception as e:
                    logger.error(f"Error checking cleanup for {symbol}: {e}")
                    continue
            
            if removed_count > 0:
                logger.info(f"🧹 Smart Cleaner removed {removed_count} coins")
                
        except Exception as e:
            logger.error(f"Error in Smart Cleaner: {e}")

    def _send_pump_dashboard(self, results):
        """Send pump-focused dashboard for all watchlist coins"""
        try:
            now = datetime.now().strftime('%H:%M:%S')
            
            msg = f"📡 <b>PUMP MONITOR</b> — {now}\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            for r in results:
                symbol = r['symbol']
                score = r['pump_score']
                price = r['price']
                
                # Score emoji
                if score >= 60:
                    score_emoji = "🔴"   # HOT
                    status = "🔥 HOT"
                elif score >= 40:
                    score_emoji = "🟡"   # WARM
                    status = "⚡ WARM"
                elif score >= 20:
                    score_emoji = "🟢"   # MILD
                    status = "📊 MILD"
                else:
                    score_emoji = "⚪"   # COLD
                    status = "💤 COLD"
                
                # Score bar
                filled = min(5, score // 20)
                score_bar = "█" * filled + "░" * (5 - filled)
                
                # Format price
                try:
                    formatted_price = self.command_handler.binance.format_price(symbol, price)
                except:
                    formatted_price = f"${price:,.6f}"
                
                msg += f"{score_emoji} <b>#{symbol}</b> — {status}\n"
                msg += f"   Pump Score: [{score_bar}] {score}/100\n"
                msg += f"   💰 Giá: {formatted_price}\n"
                
                # Price changes
                msg += f"   📊 5m: {r['chg_5m']:+.2f}% | 30m: {r['chg_30m']:+.2f}% | 1H: {r['chg_1h']:+.2f}%\n"
                
                # Volume spike
                vol_5m_icon = "🔥" if r['vol_spike_5m'] > 2 else "📊"
                vol_1h_icon = "🔥" if r['vol_spike_1h'] > 2 else "📊"
                msg += f"   {vol_5m_icon} Vol 5m: {r['vol_spike_5m']:.1f}x | {vol_1h_icon} Vol 1H: {r['vol_spike_1h']:.1f}x\n"
                
                # RSI
                rsi_icon = "🔴" if r['rsi_5m'] > 70 else ("🟢" if r['rsi_5m'] < 30 else "🔵")
                rsi_1h_icon = "🔴" if r['rsi_1h'] > 70 else ("🟢" if r['rsi_1h'] < 30 else "🔵")
                msg += f"   {rsi_icon} RSI 5m: {r['rsi_5m']:.0f} | {rsi_1h_icon} RSI 1H: {r['rsi_1h']:.0f} | Δ{r['rsi_momentum']:+.1f}\n"
                
                # OBV
                obv_icon = "💰" if r['obv_trend'] == "INFLOW" else "🔻"
                msg += f"   {obv_icon} OBV: {r['obv_trend']}"
                if abs(r['obv_change']) > 0:
                    msg += f" ({r['obv_change']:+,.0f})"
                msg += "\n"
                
                # Order Book
                if r['ob_ratio'] > 0:
                    ob_icon = "🧱" if r['ob_ratio'] > 2 else "📋"
                    msg += f"   {ob_icon} Buy/Sell: {r['ob_ratio']:.1f}x"
                    if r['cost_5pct'] > 0:
                        msg += f" | Push 5%: ${r['cost_5pct']:,.0f}"
                    msg += "\n"
                
                # Buy pressure
                bp_icon = "💪" if r['buy_ratio'] > 0.6 else "📊"
                msg += f"   {bp_icon} Buy Pressure: {r['buy_ratio']*100:.0f}% ({int(r['buy_ratio']*20)}/20 green)\n"
                
                # Pump signals summary
                if r['pump_signals']:
                    msg += f"   ⚡ <b>Signals:</b> {' | '.join(r['pump_signals'])}\n"
                
                # Risk warning
                if r['rsi_5m'] > 80 or r['rsi_1h'] > 80:
                    msg += f"   ⚠️ RSI QUÁ CAO — Rủi ro điều chỉnh!\n"
                
                msg += "\n"
            
            msg += f"━━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"⏰ Quét tiếp sau {self.check_interval // 60} phút"
            
            # Get target chat_id
            target_chat_id = getattr(self.command_handler._config, 'GROUP_CHAT_ID', None)
            self.command_handler.bot.send_message(msg, chat_id=target_chat_id)
            
        except Exception as e:
            logger.error(f"Error sending pump dashboard: {e}")

    # ================================================================
    # VOLUME MONITORING (KEEP - runs more frequently)
    # ================================================================

    def _volume_monitor_loop(self):
        """Volume monitoring loop (runs more frequently)"""
        while self.running:
            try:
                self.check_watchlist_volumes()
            except Exception as e:
                logger.error(f"Error in volume monitor loop: {e}")
            
            # Sleep in small intervals to allow quick shutdown
            for _ in range(self.volume_check_interval):
                if not self.running:
                    break
                time.sleep(1)
    
    def check_watchlist_volumes(self):
        """Check watchlist for Volume Spikes AND Price Velocity (Real-time tracking)"""
        try:
            symbols = self.command_handler.watchlist.get_all()
            
            if not symbols:
                logger.debug("Watchlist is empty, skipping volume check")
                return
            
            logger.info(f"Checking volumes for {len(symbols)} watchlist symbols...")
            
            # Scan for volume spikes
            spike_alerts = self.volume_detector.scan_watchlist_volumes(
                symbols,
                timeframes=['5m', '1h']
            )
            
            # --- REAL-TIME PRICE VELOCITY CHECK ---
            velocity_alerts = []
            for symbol in symbols:
                try:
                    # Get last 2 candles (5m)
                    klines = self.command_handler.binance.get_klines(symbol, '5m', limit=2)
                    if klines is not None and len(klines) >= 2:
                        last_close = float(klines.iloc[-2]['close'])
                        current_close = float(klines.iloc[-1]['close'])
                        
                        pct_change = ((current_close - last_close) / last_close) * 100
                        
                        # Alert if price jumps > 1.5% in current 5m candle (FAST MOVER)
                        if pct_change >= 1.5:
                            velocity_alerts.append({
                                'symbol': symbol,
                                'type': 'velocity',
                                'change': pct_change,
                                'price': current_close
                            })
                except Exception as e:
                    logger.debug(f"Velocity check error for {symbol}: {e}")

            if not spike_alerts and not velocity_alerts:
                logger.info("No volume spikes or velocity alerts detected")
                return
            
            # Filter out recently alerted spikes (avoid spam)
            new_alerts = []
            current_time = time.time()
            
            # Process Volume Spikes
            if spike_alerts:
                for alert in spike_alerts:
                    symbol = alert['symbol']
                    alert_key = f"{symbol}_volume"
                    last_alert_time = self.last_volume_alerts.get(alert_key, 0)
                    
                    # Only alert if it's been more than 1 hour since last alert
                    if current_time - last_alert_time > 3600:
                        new_alerts.append(alert)
                        self.last_volume_alerts[alert_key] = current_time
            
            # Process Velocity Alerts
            if velocity_alerts:
                for alert in velocity_alerts:
                    symbol = alert['symbol']
                    alert_key = f"{symbol}_velocity"
                    last_alert_time = self.last_volume_alerts.get(alert_key, 0)
                    
                    # Alert every 15 mins for strong moves
                    if current_time - last_alert_time > 900:
                        # Add a flag to distinguish
                        alert['is_velocity'] = True
                        new_alerts.append(alert)
                        self.last_volume_alerts[alert_key] = current_time

            if not new_alerts:
                return
            
            # Save updated history
            self.save_history()
            
            # Send notifications
            self._send_volume_notifications(new_alerts)
            
        except Exception as e:
            logger.error(f"Error checking watchlist volumes: {e}")
    
    def _send_volume_notifications(self, alerts):
        """Send volume/velocity notifications (pump-focused)"""
        try:
            now = datetime.now().strftime('%H:%M:%S')
            
            for alert in alerts:
                symbol = alert['symbol']
                
                # Do a quick pump analysis for more context
                pump_data = self._analyze_pump_signals(symbol)
                
                if not pump_data:
                    continue
                
                # Check if it's a Velocity Alert or Volume Alert
                is_velocity = alert.get('is_velocity', False)
                
                if is_velocity:
                    msg = f"🚀 <b>FAST MOVER: #{symbol}</b>\n"
                    msg += f"📈 Tăng nhanh <b>+{alert['change']:.2f}%</b> trong nến 5m hiện tại!\n"
                else:
                    msg = f"⚡ <b>VOLUME SPIKE: #{symbol}</b>\n"
                
                msg += f"🕐 {now}\n"
                msg += f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                
                # Volume details (if Volume Alert)
                if not is_velocity and 'timeframe_results' in alert:
                    strongest_tf = None
                    max_ratio = 0
                    for tf, tf_result in alert['timeframe_results'].items():
                        if tf_result['is_spike'] and tf_result['volume_ratio'] > max_ratio:
                            max_ratio = tf_result['volume_ratio']
                            strongest_tf = tf
                    
                    if strongest_tf:
                        tf_data = alert['timeframe_results'][strongest_tf]
                        msg += f"🔥 <b>Volume {strongest_tf}: {max_ratio:.1f}x</b> so với TB\n\n"
                
                # Add pump context
                try:
                    formatted_price = self.command_handler.binance.format_price(symbol, pump_data['price'])
                except:
                    formatted_price = f"${pump_data['price']:,.6f}"
                    
                msg += f"💰 Giá: {formatted_price}\n"
                msg += f"📊 5m: {pump_data['chg_5m']:+.2f}% | 30m: {pump_data['chg_30m']:+.2f}% | 1H: {pump_data['chg_1h']:+.2f}%\n"
                
                obv_icon = "💰" if pump_data['obv_trend'] == "INFLOW" else "🔻"
                msg += f"{obv_icon} OBV: {pump_data['obv_trend']} ({pump_data['obv_change']:+,.0f})\n"
                
                if pump_data['ob_ratio'] > 0:
                    msg += f"🧱 Buy/Sell: {pump_data['ob_ratio']:.1f}x"
                    if pump_data['cost_5pct'] > 0:
                        msg += f" | Push 5%: ${pump_data['cost_5pct']:,.0f}"
                    msg += "\n"
                
                rsi_icon = "🔴" if pump_data['rsi_5m'] > 70 else "🔵"
                msg += f"{rsi_icon} RSI: {pump_data['rsi_5m']:.0f} (5m) | {pump_data['rsi_1h']:.0f} (1H)\n"
                
                msg += f"💪 Buy Pressure: {pump_data['buy_ratio']*100:.0f}%\n"
                
                # Pump score
                score = pump_data['pump_score']
                filled = min(5, score // 20)
                score_bar = "█" * filled + "░" * (5 - filled)
                msg += f"\n🎯 Pump Score: [{score_bar}] {score}/100\n"
                
                if pump_data['pump_signals']:
                    msg += f"⚡ {' | '.join(pump_data['pump_signals'])}\n"
                
                # Risk
                if pump_data['rsi_5m'] > 80:
                    msg += f"\n⚠️ RSI > 80 — Cẩn thận điều chỉnh!"
                
                target_chat_id = getattr(self.command_handler._config, 'GROUP_CHAT_ID', None)
                self.command_handler.bot.send_message(msg, chat_id=target_chat_id)
                
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"Error sending volume notifications: {e}")

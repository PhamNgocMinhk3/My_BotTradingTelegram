"""
Advanced Pump/Dump Detector v4.0
Phát hiện chính xác coin sẽ tăng/giảm mạnh với 15+ indicators

Features:
- 5 loại BOT detection (Wash Trading, Spoofing, Iceberg, Market Maker, Dump)
- Volume legitimacy analysis (VWAP, buy/sell pressure, large trades)
- Order book manipulation detection (fake walls, layering)
- Price action quality assessment (respects S/R, clean breakouts)
- Institutional flow detection (block trades, Wyckoff patterns)
- Direction probability calculation (UP/DOWN/SIDEWAYS)
- Comprehensive risk assessment

Author: AI Assistant
Date: November 20, 2025
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class AdvancedPumpDumpDetector:
    """
    Phát hiện Pump/Dump với độ chính xác cao
    Kết hợp 15+ indicators để xác định xu hướng thực sự
    """
    
    def __init__(self, binance_client):
        """
        Initialize advanced detector
        
        Args:
            binance_client: BinanceClient instance
        """
        self.binance = binance_client
        self.confidence_threshold = 70  # Ngưỡng tin cậy tối thiểu
        
        logger.info("✅ Advanced Pump/Dump Detector v4.0 initialized")
        
    def analyze_comprehensive(self, 
                            symbol: str,
                            klines_5m: Optional[pd.DataFrame] = None,
                            klines_1h: Optional[pd.DataFrame] = None,
                            order_book: Optional[Dict] = None,
                            trades: Optional[List[Dict]] = None,
                            market_data: Optional[Dict] = None) -> Dict:
        """
        Phân tích toàn diện để xác định pump/dump thực sự
        
        Args:
            symbol: Trading symbol
            klines_5m: 5-minute klines data
            klines_1h: 1-hour klines data  
            order_book: Order book data
            trades: Recent trades data
            market_data: 24h market data
            
        Returns:
            {
                'signal': 'STRONG_PUMP' | 'PUMP' | 'NEUTRAL' | 'DUMP' | 'STRONG_DUMP',
                'confidence': 0-100,
                'direction_probability': {
                    'up': 0-100,
                    'down': 0-100,
                    'sideways': 0-100
                },
                'bot_activity': {...},
                'volume_analysis': {...},
                'depth_analysis': {...},
                'price_quality': {...},
                'institutional_flow': {...},
                'risk_level': 'LOW' | 'MEDIUM' | 'HIGH' | 'EXTREME',
                'recommendation': {...}
            }
        """
        
        try:
            results = {}
            
            # Fetch data if not provided
            if klines_5m is None:
                klines_5m = self.binance.get_klines(symbol, '5m', limit=200)
            if klines_1h is None:
                klines_1h = self.binance.get_klines(symbol, '1h', limit=100)
            if order_book is None:
                try:
                    order_book = self.binance.client.get_order_book(symbol=symbol, limit=100)
                except:
                    order_book = None
            if trades is None:
                try:
                    trades = self.binance.client.get_recent_trades(symbol=symbol, limit=500)
                except:
                    trades = []
            if market_data is None:
                try:
                    market_data = self.binance.client.get_ticker(symbol=symbol)
                except:
                    market_data = {}
            
            # Use 5m for main analysis, 1h for confirmation
            klines = klines_5m if klines_5m is not None and not klines_5m.empty else klines_1h
            
            if klines is None or klines.empty:
                logger.warning(f"No klines data for {symbol}")
                return self._get_neutral_result(symbol)
            
            # 1. Phân tích BOT activity (15 points)
            bot_analysis = self._detect_bot_types(klines, trades, order_book)
            results['bot_activity'] = bot_analysis
            
            # 2. Phân tích Volume Profile (20 points)
            volume_analysis = self._analyze_volume_legitimacy(klines, trades)
            results['volume_analysis'] = volume_analysis
            
            # 3. Phân tích Order Book Depth (15 points)
            depth_analysis = self._analyze_order_book_manipulation(order_book)
            results['depth_analysis'] = depth_analysis
            
            # 4. Phân tích Price Action Quality (20 points)
            price_quality = self._analyze_price_action_quality(klines)
            results['price_quality'] = price_quality
            
            # 5. Phân tích Institutional Flow (30 points - quan trọng nhất!)
            institutional = self._detect_institutional_activity(klines, trades, market_data)
            results['institutional_flow'] = institutional
            
            # 6. Tính toán xác suất hướng di chuyển
            direction_prob = self._calculate_direction_probability(results)
            results['direction_probability'] = direction_prob
            
            # 7. Tính confidence tổng thể
            confidence = self._calculate_overall_confidence(results)
            results['confidence'] = confidence
            
            # 8. Xác định signal cuối cùng
            signal = self._determine_final_signal(direction_prob, confidence, results)
            results['signal'] = signal
            
            # 9. Đánh giá rủi ro
            risk = self._assess_risk_level(results)
            results['risk_level'] = risk
            
            # 10. Tạo recommendation
            recommendation = self._generate_recommendation(results, symbol)
            results['recommendation'] = recommendation
            
            # Add metadata
            results['symbol'] = symbol
            results['timestamp'] = datetime.now().isoformat()
            
            logger.info(f"📊 {symbol}: Signal={signal}, Confidence={confidence}%, Risk={risk}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in comprehensive analysis for {symbol}: {e}")
            return self._get_neutral_result(symbol)
    
    def _get_neutral_result(self, symbol: str) -> Dict:
        """Return neutral result when analysis fails"""
        return {
            'symbol': symbol,
            'signal': 'NEUTRAL',
            'confidence': 0,
            'direction_probability': {'up': 33, 'down': 33, 'sideways': 34},
            'bot_activity': {},
            'volume_analysis': {},
            'depth_analysis': {},
            'price_quality': {},
            'institutional_flow': {},
            'risk_level': 'MEDIUM',
            'recommendation': {'action': 'WAIT', 'reasoning': ['Insufficient data']},
            'timestamp': datetime.now().isoformat()
        }
    
    def _detect_bot_types(self, klines: pd.DataFrame, trades: List[Dict], order_book: Optional[Dict]) -> Dict:
        """
        Phát hiện 5 loại BOT:
        - Wash Trading BOT
        - Spoofing BOT  
        - Iceberg BOT
        - Market Maker BOT
        - Dump BOT
        """
        
        bot_signals = {
            'wash_trading': {'detected': False, 'confidence': 0, 'evidence': []},
            'spoofing': {'detected': False, 'confidence': 0, 'evidence': []},
            'iceberg': {'detected': False, 'confidence': 0, 'evidence': []},
            'market_maker': {'detected': False, 'confidence': 0, 'evidence': []},
            'dump_bot': {'detected': False, 'confidence': 0, 'evidence': []}
        }
        
        if klines.empty:
            return bot_signals
        
        # === 1. WASH TRADING DETECTION ===
        # Volume spike nhưng giá không đổi
        recent = klines.tail(20)
        volume_spike = recent['volume'].iloc[-1] > recent['volume'].mean() * 2
        price_change = abs((recent['close'].iloc[-1] - recent['close'].iloc[-5]) / recent['close'].iloc[-5] * 100)
        
        if volume_spike and price_change < 0.5:
            bot_signals['wash_trading']['detected'] = True
            bot_signals['wash_trading']['confidence'] = min(90, 50 + (2.0 - price_change) * 20)
            bot_signals['wash_trading']['evidence'].append(f"Volume tăng {recent['volume'].iloc[-1] / recent['volume'].mean():.1f}x nhưng giá chỉ thay đổi {price_change:.2f}%")
        
        # === 2. SPOOFING DETECTION ===
        # Order book thay đổi nhiều nhưng ít trades
        if order_book and trades:
            try:
                bid_depth = sum([float(bid[1]) for bid in order_book.get('bids', [])[:10]])
                ask_depth = sum([float(ask[1]) for ask in order_book.get('asks', [])[:10]])
                total_depth = bid_depth + ask_depth
                
                recent_trades_volume = sum([float(t.get('qty', 0)) for t in trades[-50:]])
                
                if total_depth > recent_trades_volume * 5:
                    bot_signals['spoofing']['detected'] = True
                    bot_signals['spoofing']['confidence'] = min(85, 40 + (total_depth / recent_trades_volume) * 5)
                    bot_signals['spoofing']['evidence'].append(f"Order book depth {total_depth:.2f} >> recent trades {recent_trades_volume:.2f}")
            except:
                pass
        
        # === 3. ICEBERG BOT DETECTION ===
        # Nhiều orders nhỏ cùng size, đều đặn
        if trades and len(trades) > 100:
            try:
                trade_sizes = [float(t.get('qty', 0)) for t in trades[-100:]]
                size_std = np.std(trade_sizes)
                size_mean = np.mean(trade_sizes)
                
                # Nếu std/mean < 0.15 → size rất đồng nhất → bot
                if size_mean > 0 and size_std / size_mean < 0.15:
                    # Check thời gian đều đặn
                    timestamps = [t.get('time', 0) for t in trades[-50:]]
                    if timestamps:
                        time_diffs = np.diff(timestamps)
                        time_std = np.std(time_diffs)
                        time_mean = np.mean(time_diffs)
                        
                        if time_mean > 0 and time_std / time_mean < 0.3:
                            bot_signals['iceberg']['detected'] = True
                            bot_signals['iceberg']['confidence'] = 75
                            bot_signals['iceberg']['evidence'].append(f"Trade size đồng nhất (std/mean={size_std/size_mean:.3f}), thời gian đều đặn")
            except:
                pass
        
        # === 4. MARKET MAKER BOT DETECTION ===
        # Bid-ask spread hẹp bất thường + depth cao
        if order_book:
            try:
                best_bid = float(order_book['bids'][0][0]) if order_book.get('bids') else 0
                best_ask = float(order_book['asks'][0][0]) if order_book.get('asks') else 0
                
                if best_bid > 0 and best_ask > 0:
                    spread_pct = (best_ask - best_bid) / best_bid * 100
                    
                    if spread_pct < 0.05:  # Spread < 0.05% = rất hẹp
                        bot_signals['market_maker']['detected'] = True
                        bot_signals['market_maker']['confidence'] = 70
                        bot_signals['market_maker']['evidence'].append(f"Spread cực hẹp {spread_pct:.4f}% → MM bot tạo liquidity giả")
            except:
                pass
        
        # === 5. DUMP BOT DETECTION ===
        # Giá giảm dần + volume giảm dần + lower highs
        if len(klines) >= 20:
            recent_20 = klines.tail(20)
            
            # Check downtrend
            price_changes = recent_20['close'].pct_change()
            negative_candles = (price_changes < 0).sum()
            
            # Check declining volume
            volume_trend = np.polyfit(range(len(recent_20)), recent_20['volume'].values, 1)[0]
            
            # Check lower highs
            highs = recent_20['high'].values
            lower_highs = sum([highs[i] < highs[i-1] for i in range(1, len(highs))])
            
            if negative_candles > 14 and volume_trend < 0 and lower_highs > 15:
                bot_signals['dump_bot']['detected'] = True
                bot_signals['dump_bot']['confidence'] = 80
                bot_signals['dump_bot']['evidence'].append(f"Giảm liên tục {negative_candles}/20 nến, volume giảm dần, lower highs {lower_highs}/19")
        
        return bot_signals
    
    def _analyze_volume_legitimacy(self, klines: pd.DataFrame, trades: List[Dict]) -> Dict:
        """
        Phân tích xem volume có thực hay giả (wash trading)
        
        Indicators:
        - VWAP deviation
        - Buy/Sell pressure balance
        - Large trades ratio
        - Volume clustering
        """
        
        analysis = {
            'legitimacy_score': 0,  # 0-100
            'is_legitimate': False,
            'buy_sell_ratio': 0,
            'large_trades_pct': 0,
            'volume_quality': 'UNKNOWN',
            'evidence': []
        }
        
        if klines.empty:
            return analysis
        
        recent = klines.tail(50)
        
        # === 1. VWAP DEVIATION ===
        # Volume thực sẽ có VWAP gần close price, nhưng pump mạnh có thể lệch
        try:
            recent['vwap'] = (recent['volume'] * (recent['high'] + recent['low'] + recent['close']) / 3).cumsum() / recent['volume'].cumsum()
            vwap_dev = abs((recent['close'].iloc[-1] - recent['vwap'].iloc[-1]) / recent['close'].iloc[-1] * 100)
            
            # Less strict penalty: Allow up to 5% deviation for pumps
            vwap_score = max(0, 100 - max(0, vwap_dev - 2) * 15)
        except:
            vwap_score = 50
            vwap_dev = 0
        
        # === 2. BUY/SELL PRESSURE ===
        ratio_score = 50
        if trades and len(trades) > 100:
            try:
                buy_volume = sum([float(t.get('qty', 0)) for t in trades if not t.get('isBuyerMaker', True)])
                sell_volume = sum([float(t.get('qty', 0)) for t in trades if t.get('isBuyerMaker', True)])
                
                total = buy_volume + sell_volume
                if total > 0:
                    analysis['buy_sell_ratio'] = buy_volume / sell_volume if sell_volume > 0 else 10
                    
                    # WIDENED RANGE: 0.5-2.5 is normal for volatile coins
                    if 0.5 <= analysis['buy_sell_ratio'] <= 2.5:
                        ratio_score = 100
                    elif 0.3 <= analysis['buy_sell_ratio'] <= 4.0:
                        ratio_score = 70
                    else:
                        ratio_score = 40
            except:
                pass
        
        # === 3. LARGE TRADES RATIO ===
        large_score = 50
        if trades and len(trades) > 50:
            try:
                trade_sizes = [float(t.get('qty', 0)) for t in trades]
                mean_size = np.mean(trade_sizes)
                large_trades = [t for t in trade_sizes if t > mean_size * 5]
                
                analysis['large_trades_pct'] = len(large_trades) / len(trades) * 100
                
                # Allow up to 30% large trades for institutional moves
                if 5 <= analysis['large_trades_pct'] <= 30:
                    large_score = 100
                elif analysis['large_trades_pct'] < 5:
                    large_score = 60  # Quá ít whale = retail only
                else:
                    large_score = 40  # Quá nhiều large = manipulation
            except:
                pass
        
        # === 4. VOLUME CLUSTERING ===
        cluster_score = 50
        try:
            volume_std = recent['volume'].std()
            volume_mean = recent['volume'].mean()
            
            if volume_mean > 0:
                cv = volume_std / volume_mean  # Coefficient of variation
                
                if cv < 0.5:
                    cluster_score = 40  # Quá đồng đều = bot
                elif cv < 2.0: # Allow higher variance for pumps (spiky volume)
                    cluster_score = 100  # Lý tưởng
                else:
                    cluster_score = 60  # Quá phân tán
        except:
            pass
        
        # === TÍNH TỔNG ===
        analysis['legitimacy_score'] = int((vwap_score * 0.3 + ratio_score * 0.3 + large_score * 0.2 + cluster_score * 0.2))
        # LOWER THRESHOLD: 60 is enough for legit check
        analysis['is_legitimate'] = analysis['legitimacy_score'] >= 60
        
        if analysis['legitimacy_score'] >= 80:
            analysis['volume_quality'] = 'EXCELLENT'
        elif analysis['legitimacy_score'] >= 60:
            analysis['volume_quality'] = 'GOOD'
        elif analysis['legitimacy_score'] >= 45:
            analysis['volume_quality'] = 'FAIR'
        else:
            analysis['volume_quality'] = 'POOR'
        
        try:
            analysis['evidence'].append(f"VWAP deviation: {vwap_dev:.2f}% (score: {vwap_score:.0f})")
        except:
            pass
        analysis['evidence'].append(f"Buy/Sell ratio: {analysis['buy_sell_ratio']:.2f} (score: {ratio_score:.0f})")
        analysis['evidence'].append(f"Large trades: {analysis['large_trades_pct']:.1f}% (score: {large_score:.0f})")
        
        return analysis
    
    def _analyze_order_book_manipulation(self, order_book: Optional[Dict]) -> Dict:
        """
        Phát hiện manipulation qua order book:
        - Fake walls (đặt lệnh lớn rồi cancel)
        - Layering (nhiều lệnh nhỏ tạo illusion)
        - Imbalance bất thường
        """
        
        analysis = {
            'manipulation_score': 0,  # 0-100 (càng cao càng bị manipulate)
            'is_manipulated': False,
            'bid_ask_imbalance': 0,
            'wall_detection': {'bid_wall': False, 'ask_wall': False},
            'layering_detected': False,
            'evidence': []
        }
        
        if not order_book or not order_book.get('bids') or not order_book.get('asks'):
            return analysis
        
        try:
            bids = order_book['bids'][:20]
            asks = order_book['asks'][:20]
            
            # === 1. FAKE WALLS DETECTION ===
            bid_volumes = [float(b[1]) for b in bids]
            ask_volumes = [float(a[1]) for a in asks]
            
            bid_mean = np.mean(bid_volumes[1:6])  # Trung bình level 2-6
            ask_mean = np.mean(ask_volumes[1:6])
            
            # Wall = level 1 lớn hơn mean của 2-6 > 5x
            if bid_volumes[0] > bid_mean * 5:
                analysis['wall_detection']['bid_wall'] = True
                analysis['evidence'].append(f"Bid wall detected: {bid_volumes[0]:.2f} vs mean {bid_mean:.2f}")
            
            if ask_volumes[0] > ask_mean * 5:
                analysis['wall_detection']['ask_wall'] = True
                analysis['evidence'].append(f"Ask wall detected: {ask_volumes[0]:.2f} vs mean {ask_mean:.2f}")
            
            # === 2. LAYERING DETECTION ===
            bid_size_std = np.std(bid_volumes[:10])
            ask_size_std = np.std(ask_volumes[:10])
            
            bid_size_mean = np.mean(bid_volumes[:10])
            ask_size_mean = np.mean(ask_volumes[:10])
            
            if bid_size_mean > 0 and bid_size_std / bid_size_mean < 0.2:
                analysis['layering_detected'] = True
                analysis['evidence'].append(f"Bid layering detected (std/mean={bid_size_std/bid_size_mean:.3f})")
            
            if ask_size_mean > 0 and ask_size_std / ask_size_mean < 0.2:
                analysis['layering_detected'] = True
                analysis['evidence'].append(f"Ask layering detected (std/mean={ask_size_std/ask_size_mean:.3f})")
            
            # === 3. BID-ASK IMBALANCE ===
            total_bid = sum(bid_volumes[:10])
            total_ask = sum(ask_volumes[:10])
            
            if total_bid + total_ask > 0:
                analysis['bid_ask_imbalance'] = (total_bid - total_ask) / (total_bid + total_ask) * 100
                
                # Imbalance > 50% = bất thường
                if abs(analysis['bid_ask_imbalance']) > 50:
                    analysis['evidence'].append(f"Extreme imbalance: {analysis['bid_ask_imbalance']:.1f}%")
            
            # === MANIPULATION SCORE ===
            score = 0
            
            if analysis['wall_detection']['bid_wall'] or analysis['wall_detection']['ask_wall']:
                score += 30
            
            if analysis['layering_detected']:
                score += 35
            
            if abs(analysis['bid_ask_imbalance']) > 50:
                score += 25
            elif abs(analysis['bid_ask_imbalance']) > 30:
                score += 15
            
            analysis['manipulation_score'] = min(100, score)
            analysis['is_manipulated'] = score >= 40
            
        except Exception as e:
            logger.debug(f"Order book analysis error: {e}")
        
        return analysis
    
    def _analyze_price_action_quality(self, klines: pd.DataFrame) -> Dict:
        """
        Đánh giá chất lượng price action:
        - Có follow technical patterns không
        - Có respect support/resistance không
        - Có breakout/breakdown hợp lệ không
        """
        
        analysis = {
            'quality_score': 0,  # 0-100
            'is_organic': False,
            'respects_levels': False,
            'clean_breakouts': False,
            'evidence': []
        }
        
        if klines.empty or len(klines) < 50:
            return analysis
        
        recent = klines.tail(50)
        
        # === 1. RESPECTS SUPPORT/RESISTANCE ===
        try:
            highs = recent['high'].values
            lows = recent['low'].values
            
            resistance_levels = []
            support_levels = []
            
            # Simple S/R detection
            for i in range(2, len(highs) - 2):
                if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                    resistance_levels.append(highs[i])
                
                if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                    support_levels.append(lows[i])
            
            # Check xem giá có bounce/reject ở levels không
            respects_count = 0
            for level in resistance_levels[-3:]:
                nearby_candles = recent[abs(recent['high'] - level) / level < 0.01]
                if len(nearby_candles) > 0:
                    rejections = nearby_candles[nearby_candles['close'] < nearby_candles['open']]
                    if len(rejections) > 0:
                        respects_count += 1
            
            for level in support_levels[-3:]:
                nearby_candles = recent[abs(recent['low'] - level) / level < 0.01]
                if len(nearby_candles) > 0:
                    bounces = nearby_candles[nearby_candles['close'] > nearby_candles['open']]
                    if len(bounces) > 0:
                        respects_count += 1
            
            if respects_count >= 2:
                analysis['respects_levels'] = True
                analysis['evidence'].append(f"Respects {respects_count} S/R levels → Organic price action")
        except:
            pass
        
        # === 2. KHÔNG CÓ SPIKE BẤT THƯỜNG ===
        try:
            price_changes = recent['close'].pct_change().abs()
            extreme_moves = (price_changes > price_changes.mean() + 3 * price_changes.std()).sum()
            
            if extreme_moves <= 2:
                smooth_score = 100
                analysis['evidence'].append(f"Smooth price action, only {extreme_moves} extreme moves")
            else:
                smooth_score = max(0, 100 - extreme_moves * 15)
                analysis['evidence'].append(f"⚠️ {extreme_moves} extreme price spikes detected")
        except:
            smooth_score = 50
        
        # === QUALITY SCORE ===
        score = 0
        
        if analysis['respects_levels']:
            score += 40
        
        if analysis['clean_breakouts']:
            score += 30
        
        score += smooth_score * 0.3
        
        analysis['quality_score'] = int(score)
        analysis['is_organic'] = score >= 60
        
        return analysis
    
        return analysis

    def _estimate_pump_time(self, klines: pd.DataFrame) -> str:
        """
        Estimate time until pump based on Market Phase (Accumulation vs Breakout)
        Uses Bollinger Band Squeeze & Volume trends.
        """
        try:
            # 1. Calculate Bollinger Bands & Band Width (Squeeze)
            close = klines['close'].astype(float)
            
            # Use min_periods to handle initial data
            rolling_mean = close.rolling(window=20, min_periods=20).mean()
            rolling_std = close.rolling(window=20, min_periods=20).std()
            
            upper_band = rolling_mean + (rolling_std * 2)
            lower_band = rolling_mean - (rolling_std * 2)
            
            # Band Width: (Upper - Lower) / Middle
            # Handle potential division by zero or NaN
            bbw = (upper_band - lower_band) / rolling_mean
            
            # Need at least one valid BBW value
            if bbw.dropna().empty:
                 return "Unknown (Thiếu dữ liệu BBW)"
                 
            current_bbw = float(bbw.iloc[-1])
            
            # Rolling average of BBW (needs history)
            # If not enough history for 50, use what we have (min 10)
            avg_bbw_series = bbw.rolling(window=50, min_periods=10).mean()
            
            if avg_bbw_series.dropna().empty:
                avg_bbw = current_bbw # Fallback
            else:
                avg_bbw = float(avg_bbw_series.iloc[-1])
            
            if np.isnan(current_bbw) or np.isnan(avg_bbw) or avg_bbw == 0:
                is_squeeze = False
            else:
                is_squeeze = current_bbw < (avg_bbw * 0.8) # Squeeze if 20% tighter than average
            
            # 2. Volume Analysis
            recent_vol = klines['volume'].tail(3).mean()
            avg_vol = klines['volume'].tail(50).mean()
            vol_ratio = recent_vol / avg_vol if avg_vol > 0 else 1.0
            
            # 3. Consolidation Duration (Low Volatility)
            low_vol_count = 0
            for i in range(len(klines)-1, -1, -1):
                high = float(klines.iloc[i]['high'])
                low = float(klines.iloc[i]['low'])
                volatility = (high - low) / low
                if volatility < 0.02: # < 2% range
                    low_vol_count += 1
                else:
                    break
            
            # === TIMING LOGIC ===
            
            # CASE A: BREAKOUT IMMINENT (High Volume + Breaking Out)
            if vol_ratio > 3.0:
                return "5-15 phút (ĐỘT BIẾN VOLUME 🚨)"
            if vol_ratio > 2.0 and is_squeeze:
                 return "15-30 phút (SQUEEZE BREAKOUT)"
                 
            # CASE B: PRE-BREAKOUT (Squeeze + Slight Volume Increase)
            if is_squeeze and vol_ratio > 1.2:
                return "1-4 giờ (Chuẩn bị Break)"
            
            # CASE C: ACCUMULATION (Long Consolidation)
            # Assuming 1h candles
            if low_vol_count > 48: # > 2 days
                return "24-48 giờ (Gom hàng dài hạn)"
            elif low_vol_count > 24: # > 1 day
                return "12-24 giờ (Gom hàng)"
            elif low_vol_count > 10:
                return "4-12 giờ"
            
            # CASE D: NORMAL / UNKNOWN
            if vol_ratio < 0.8:
                return "Chưa rõ (Volume thấp)"
            else:
                return "Trong 24h tới"
                
        except Exception as e:
            logger.error(f"Error estimating pump time: {e}")
            print(f"DEBUG ERROR estimating pump time: {e}") # Force print
            traceback.print_exc()

    def _calculate_entry_zone(self, klines: pd.DataFrame) -> Tuple[float, float]:
        """
        Calculate Safe Entry Zone based on Support & VWAP
        Logic:
        - Support: Lowest Low of last 6 candles
        - Fair Value: VWAP
        - Dynamic Support: EMA 25
        """
        try:
            # 1. Calculate VWAP
            klines['tp'] = (klines['high'] + klines['low'] + klines['close']) / 3
            klines['vwap'] = (klines['tp'] * klines['volume']).cumsum() / klines['volume'].cumsum()
            vwap = float(klines.iloc[-1]['vwap'])
            
            # 2. Calculate Support (Lowest of last 6)
            recent_low = float(klines['low'].tail(6).min())
            
            # 3. Calculate EMA 25 (Dynamic Support)
            ema_25 = float(klines['close'].ewm(span=25, adjust=False).mean().iloc[-1])
            
            current_price = float(klines.iloc[-1]['close'])
            
            # === ZONE LOGIC ===
            # If Price > VWAP (Uptrend): Entry at VWAP retest or EMA25
            if current_price > vwap:
                entry_high = vwap
                entry_low = max(recent_low, ema_25)
                # If EMA is too far below, tighten it to 1% below VWAP
                if entry_low < vwap * 0.98:
                    entry_low = vwap * 0.98
            else:
                # If Price < VWAP (Accumulation): Entry at Support to Current
                entry_high = current_price
                entry_low = recent_low
            
            # Ensure logical bounds
            if entry_low > entry_high:
                entry_low, entry_high = entry_high, entry_low
                
            return entry_low, entry_high
            
        except Exception as e:
            logger.error(f"Error calculating entry zone: {e}")
            close = float(klines.iloc[-1]['close'])
            return close * 0.98, close

    def _calculate_atr(self, klines: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range (ATR)"""
        try:
            high = klines['high'].astype(float)
            low = klines['low'].astype(float)
            close = klines['close'].astype(float)
            
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.ewm(alpha=1/period, adjust=False).mean()
            
            return float(atr.iloc[-1])
        except Exception as e:
            logger.error(f"Error calculating ATR: {e}")
            return 0.0

    def _calculate_dynamic_tp_sl(self, entry_price: float, atr: float, score: float, vol_ratio: float) -> dict:
        """
        Calculate Dynamic TP/SL based on ATR and Signal Strength
        """
        try:
            # Base SL: -5% (Hard Stop) or ATR based
            # System Rule: Watchlist removes if < -5%
            hard_stop = entry_price * 0.95
            
            # Dynamic SL: Entry - 1.5 * ATR
            if atr > 0:
                dynamic_sl = entry_price - (1.5 * atr)
                sl_price = max(hard_stop, dynamic_sl) # Take the higher (tighter) one, but never below hard stop? 
                # Actually we want the wider one to avoid noise, but capped at -5%.
                # So SL = min(Entry * 0.98, dynamic_sl) but not lower than 0.95?
                # Let's stick to: Max risk 5%. If ATR suggests tighter, use ATR.
                sl_price = max(hard_stop, dynamic_sl)
            else:
                sl_price = hard_stop

            # Determine Signal Strength (Swing vs Quick)
            # Strong: Score >= 80 OR Vol Ratio > 3.0
            is_strong = (score >= 80) or (vol_ratio > 3.0)
            
            if atr > 0:
                # TP1 (Quick/Base): Entry + 2 ATR (~3-5%)
                tp1 = entry_price + (2.0 * atr)
                
                # TP2 (Swing/Moon): Entry + 5 ATR (~8-12%+)
                tp2 = entry_price + (5.0 * atr)
            else:
                # Fallback if ATR fails
                tp1 = entry_price * 1.04
                tp2 = entry_price * 1.10
            
            return {
                'sl': sl_price,
                'tp1': tp1,
                'tp2': tp2,
                'is_strong': is_strong,
                'recommendation': 'GỒNG LÃI (Hold)' if is_strong else 'TP NGẮN HẠN (Quick)'
            }
            
        except Exception as e:
            logger.error(f"Error calculating TP/SL: {e}")
            return {
                'sl': entry_price * 0.95,
                'tp1': entry_price * 1.04,
                'tp2': entry_price * 1.10,
                'is_strong': False,
                'recommendation': 'TP NGẮN HẠN'
            }

            return f"Error: {str(e)}"

    def _analyze_supply_shock(self, order_book: Dict, current_price: float) -> Dict:
        """
        Phân tích Supply Shock (Cạn Cung) - Layer 4
        - Tính volume bán trong phạm vi 5% (Sell Pressure)
        - Tính volume mua trong phạm vi 5% (Buy Support)
        - Xác định xem phe bán có mỏng không
        """
        try:
            if not order_book:
                return {'detected': False}

            bids = order_book.get('bids', [])
            asks = order_book.get('asks', [])

            if not bids or not asks:
                return {'detected': False}

            # Calculate thresholds
            upper_threshold = current_price * 1.05
            lower_threshold = current_price * 0.95

            # Calculate Sell Pressure (Volume up to +5%)
            sell_volume_5pct = 0
            cost_to_pump_5pct = 0
            for price, qty in asks:
                price = float(price)
                qty = float(qty)
                if price <= upper_threshold:
                    sell_volume_5pct += qty
                    cost_to_pump_5pct += price * qty
                else:
                    break

            # Calculate Buy Support (Volume down to -5%)
            buy_volume_5pct = 0
            for price, qty in bids:
                price = float(price)
                qty = float(qty)
                if price >= lower_threshold:
                    buy_volume_5pct += qty
                else:
                    break

            # Calculate Ratio
            if sell_volume_5pct > 0:
                buy_sell_ratio = buy_volume_5pct / sell_volume_5pct
            else:
                buy_sell_ratio = 100 # Infinite ratio if no sellers

            # Criteria for Supply Shock:
            # 1. Buy Support is 2x stronger than Sell Pressure (Strong Hands holding)
            # OR 2. Cost to pump 5% is very low (< $100k for mid-caps)
            is_supply_shock = buy_sell_ratio >= 2.0 or (cost_to_pump_5pct < 100000 and cost_to_pump_5pct > 0)

            return {
                'detected': is_supply_shock,
                'ratio': buy_sell_ratio,
                'sell_volume_5pct': sell_volume_5pct,
                'buy_volume_5pct': buy_volume_5pct,
                'cost_to_push_5pct': cost_to_pump_5pct
            }

        except Exception as e:
            logger.error(f"Error in supply shock analysis: {e}")
            return {'detected': False}

    def _detect_stealth_accumulation(self, klines: pd.DataFrame, ticker_data: Optional[Dict] = None, symbol: str = "") -> Dict:
        """
        DETECT STEALTH ACCUMULATION (THE "GEMINI" SIGNAL)
        
        Criteria:
        1. Price Compression: Volatility low and decreasing.
        2. Volume Divergence: Volume increases/spikes while price stays flat.
        3. OBV Divergence: OBV moves up while price is flat.
        4. RSI Accumulation: RSI in 30-60 zone.
        5. 24h Volume Growth: Rolling 24h volume is trending up (Realtime).
        """
        analysis = {
            'detected': False,
            'confidence': 0,
            'quality_score': 0,
            'reason': [],
            'evidence': [],
            'pump_time': "Unknown"
        }
        
        if klines.empty or len(klines) < 50:
            return analysis
            
        recent = klines.tail(50)
        
        # 1. Low Volatility (Giá nén chặt)
        high_low_range = (recent['high'] - recent['low']) / recent['low']
        avg_volatility = high_low_range.mean()
        
        # OPTIMIZED: Relaxed from 2.5% to 4% to catch declining micro-caps (Wyckoff Spring)
        is_compressed = avg_volatility < 0.04
        
        # 2. Volume Anomalies (Volume tăng trong khi giá đi ngang)
        # Chia 50 nến thành 2 nửa: 25 nến đầu và 25 nến cuối
        vol_first_half = recent['volume'].iloc[:25].mean()
        vol_second_half = recent['volume'].iloc[25:].mean()
        
        is_vol_increasing = vol_second_half > vol_first_half * 1.2  # Volume tăng 20%
        
        # 3. OBV Divergence (Giá ngang, OBV tăng)
        # Tính OBV đơn giản
        obv = (np.sign(recent['close'].diff()) * recent['volume']).cumsum()
        obv_trend = np.polyfit(range(len(obv.fillna(0))), obv.fillna(0).values, 1)[0]
        price_trend = np.polyfit(range(len(recent)), recent['close'].values, 1)[0]
        
        # OBV tăng mạnh trong khi giá đi ngang hoặc giảm nhẹ
        # FIXED: price_trend threshold was 0.0001 (too strict, missed declining coins like ESPUSDT)
        # Now uses relative threshold: < 1% of average price per candle
        avg_price = recent['close'].mean()
        price_trend_threshold = avg_price * 0.01  # 1% of avg price
        is_obv_divergence = obv_trend > 0 and abs(price_trend) < price_trend_threshold
        
        # 4. RSI Check (NEW) - RSI in accumulation zone (30-60) is ideal
        try:
            delta = recent['close'].diff()
            gain = delta.where(delta > 0, 0.0)
            loss = -delta.where(delta < 0, 0.0)
            avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
            avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = float(rsi.iloc[-1])
            is_rsi_accumulation = 30 <= current_rsi <= 60
        except:
            current_rsi = 50
            is_rsi_accumulation = False
        
        # 5. Buy Pressure (Refined) - Volume Based
        # Calculates the ratio of Volume on Green Candles vs Total Volume
        buy_volume = 0.0
        sell_volume = 0.0
        
        for i in range(len(recent)-20, len(recent)):
            try:
                c_close = float(recent['close'].iloc[i])
                c_open = float(recent['open'].iloc[i])
                c_vol = float(recent['volume'].iloc[i])
                
                if c_close >= c_open:
                    buy_volume += c_vol
                else:
                    sell_volume += c_vol
            except:
                continue
                
        total_recent_vol = buy_volume + sell_volume
        buy_ratio = 0.5 # Default neutral
        if total_recent_vol > 0:
            buy_ratio = buy_volume / total_recent_vol
            
        is_buy_dominant = buy_ratio > 0.55
        
        # DEBUG PRINT
        # print(f"DEBUG: Comp={is_compressed} ({avg_volatility:.4f}), VolInc={is_vol_increasing}, OBV={is_obv_divergence}, Buy={is_buy_dominant}")
        # 5b. Wyckoff Spring Detection (NEW)
        # Pattern: Price drops for days, then sudden volume spike at the bottom
        # This catches coins like ESPUSDT that dump first then pump x4
        is_wyckoff_spring = False
        wyckoff_bonus = 0
        try:
            # Check if price has been declining (negative trend)
            price_pct_change = ((recent['close'].iloc[-1] - recent['close'].iloc[0]) / recent['close'].iloc[0]) * 100
            # RSI oversold or near oversold
            is_oversold = current_rsi < 40
            # Volume spike in last 6 candles vs previous average
            last_6_vol = recent['volume'].iloc[-6:].mean()
            prev_avg_vol = recent['volume'].iloc[:-6].mean()
            vol_spike_at_bottom = last_6_vol > prev_avg_vol * 1.5 if prev_avg_vol > 0 else False
            
            if price_pct_change < -3 and is_oversold and vol_spike_at_bottom:
                is_wyckoff_spring = True
                wyckoff_bonus = 15
                analysis['evidence'].append(f"🧲 Wyckoff Spring: Giá giảm {price_pct_change:.1f}% + RSI {current_rsi:.0f} + Vol đột biến tại đáy")
        except:
            pass
        
        if is_compressed and (is_vol_increasing or is_obv_divergence or is_wyckoff_spring):
            analysis['detected'] = True
            
            # Estimate Pump Time
            try:
                pump_time = self._estimate_pump_time(klines)
                analysis['pump_time'] = pump_time
                analysis['evidence'].append(f"⏳ Dự Kiến Pump: {pump_time}")
            except Exception as e:
                logger.error(f"Error adding pump time: {e}")
                analysis['pump_time'] = "Unknown"
            
            # --- SCORING SYSTEM (GEMINI SCORE) --- FIXED ---
            # 1. Compression Score (Max 30) - Lower volatility is better
            # avg_volatility < 0.025 (2.5%) is threshold
            # OLD: 30 - (vol * 1200) -> Too harsh for 1.5% vol
            # NEW: 30 - (vol * 600) -> 1.5% vol gets 21 pts (was 12)
            compression_score = max(0, 30 - (avg_volatility * 600))
            
            # 2. Volume Score (Max 25) - Higher increase is better
            # Increase > 20% is threshold
            # 1.2x -> 12 pts, 2.0x -> 25 pts
            # FIX: Clamp to 0. Do not penalize low volume (accumulation often has low vol)
            vol_ratio = vol_second_half / vol_first_half if vol_first_half > 0 else 1
            volume_score = max(0, min(25, (vol_ratio - 1) * 25))
            
            # 3. OBV Score (Max 25) - Higher divergence is better
            obv_score = 25 if is_obv_divergence else 0
            
            # 4. RSI Bonus (Max 10) - RSI in accumulation zone
            rsi_bonus = 10 if is_rsi_accumulation else 0
            
            # 5. Buy Pressure Bonus (Max 10) - Using Volume Ratio
            # 50% -> 0 pts, 75% -> 10 pts
            buy_bonus = int(min(10, max(0, (buy_ratio - 0.5) * 40)))
            
            # 6. Pattern Bonus - Valid detection base points
            pattern_bonus = 15  # Max 15 (was accidentally set to 20)

            # 7. 24h Volume Trend Bonus (New) - increasing 24h Vol & USDT Vol
            # User request: Check if 24h Vol (Coin) and 24h Vol (USDT) are increasing
            vol_growth_bonus = 0
            curr_vol_24h = 0
            curr_qav_24h = 0
            
            # Read volume and price change from ticker first (safe)
            price_change_24h = 0
            if ticker_data:
                curr_vol_24h = float(ticker_data.get('volume', 0))
                curr_qav_24h = float(ticker_data.get('quoteVolume', 0))
                price_change_24h = float(ticker_data.get('priceChangePercent', 0))
            
            # Count recent red candles (last 6)
            recent_6 = klines.tail(6)
            red_count = sum(1 for _, r in recent_6.iterrows() 
                          if float(r['close']) < float(r['open']))
            analysis['red_candles_6'] = red_count
            analysis['price_change_24h'] = price_change_24h
            
            # Compare with kline data (may fail, but don't reset vol values)
            try:
                if curr_vol_24h > 0:
                    prev_vol_24h = klines.iloc[-25:-1]['volume'].astype(float).sum()
                    prev_qav_24h = klines.iloc[-25:-1]['quote_volume'].astype(float).sum()
                    
                    if curr_vol_24h > prev_vol_24h and curr_qav_24h > prev_qav_24h:
                        vol_growth_bonus = 5
                        growth_pct = ((curr_vol_24h / prev_vol_24h) - 1) * 100
                        analysis['evidence'].append(f"• Tăng Trưởng Vol 24h: +5 (Thực Tế: {growth_pct:.1f}%)")
            except Exception as e:
                logger.error(f"Error calculating 24h vol trend: {e}")

            # 8. Funding Rate Analysis (Short Squeeze Potential)
            # Negative Funding (< 0) -> Bonus
            # Always show funding rate for visibility
            funding_rate = 0.0
            funding_bonus = 0
            try:
                funding_rate = self.binance.get_funding_rate(symbol)
                
                if funding_rate < 0:
                    funding_bonus = 5
                    if funding_rate < -0.0001: # -0.01%
                        funding_bonus = 10
                        analysis['evidence'].append(f"🩸 Funding Rate Âm: {funding_rate*100:.4f}% (Cảnh báo Short Squeeze)")
                    else:
                        analysis['evidence'].append(f"📉 Funding Rate: {funding_rate*100:.4f}% (Ủng hộ Tăng)")
                else:
                    # Positive funding - Neutral info
                    analysis['evidence'].append(f"Funding Rate: {funding_rate*100:.4f}%")
                    
            except Exception as e:
                pass


            total_score = int(compression_score + volume_score + obv_score + rsi_bonus + buy_bonus + pattern_bonus + vol_growth_bonus + funding_bonus + wyckoff_bonus)
            
            # Store Realtime Volume Data for Smart Alerts
            analysis['vol_24h'] = curr_vol_24h
            analysis['vol_24h_usdt'] = curr_qav_24h
            
            # Store key metrics for Signal Ranking System
            analysis['funding_rate'] = funding_rate
            analysis['vol_ratio'] = vol_ratio
            
            # Store individual scores for alert gating
            analysis['obv_score'] = obv_score
            analysis['buy_bonus'] = buy_bonus
            
            # QUALITY GATE: Penalize if BOTH OBV and Buy Pressure are 0
            # (means only volume spike is driving the score — not real accumulation)
            if obv_score == 0 and buy_bonus == 0:
                penalty = 15
                total_score -= penalty
                analysis['evidence'].append(f"⚠️ Cảnh báo: Không có OBV & Áp Lực Mua (-{penalty} điểm)")
            
            # Bonus: Supply Shock Potential (low MC, high compression)
            if avg_volatility < 0.01:  # Really tight
                total_score += 10
                
            # Cap at 100
            analysis['quality_score'] = min(100, max(0, total_score))
            
            # Strict Mode Filter (> 80 is very high quality, > 60 is good)
            analysis['confidence'] = analysis['quality_score']
            
            analysis['evidence'].append(f"Gom Hàng Ẩn (Stealth): Điểm {analysis['quality_score']}/100")
            analysis['evidence'].append(f"• Độ Nén Giá: {compression_score:.1f}/30 (Biến Động: {avg_volatility*100:.2f}%)")
            analysis['evidence'].append(f"• Dòng Vol Vào: {volume_score:.1f}/25 (Tỷ Lệ: {vol_ratio:.2f}x)")
            analysis['evidence'].append(f"• Dòng Tiền OBV: {obv_score}/25")
            analysis['evidence'].append(f"• Vùng RSI Gom: {rsi_bonus}/10")
            analysis['evidence'].append(f"• Áp Lực Mua: {buy_bonus}/10")
            analysis['evidence'].append(f"• Mô Hình Bonus: {pattern_bonus}/15")
            
            # Calculate Entry Zone
            entry_low, entry_high = self._calculate_entry_zone(klines)
            analysis['entry_zone'] = (entry_low, entry_high)
            
            # Calculate ATR for TP/SL
            atr = self._calculate_atr(klines)
            
            # Calculate TP/SL
            # Use avg entry price for calculation
            avg_entry = (entry_low + entry_high) / 2
            tp_sl_info = self._calculate_dynamic_tp_sl(
                avg_entry, 
                atr, 
                analysis['quality_score'], 
                analysis['vol_ratio']
            )
            analysis['tp_sl_info'] = tp_sl_info
            
        return analysis

    def _detect_early_momentum(self, klines_5m: pd.DataFrame, ticker_data: Optional[Dict] = None, symbol: str = "") -> Dict:
        """
        DETECT EARLY MOMENTUM BREAKOUT (Catches coins like ESPUSDT)
        
        Analyzes 5-minute candles to find the earliest micro-signals of a pump:
        1. Volume Spike > 3x of 6h average (institutional buying burst)
        2. Trades Spike > 3x of 6h average (retail FOMO starting)
        3. Taker Buy Ratio > 65% (whales aggressively buying)
        4. Price momentum > 3% in last 1h (breakout confirmation)
        
        Requires at least 2 of 4 conditions = EARLY MOMENTUM signal
        """
        analysis = {
            'detected': False,
            'confidence': 0,
            'quality_score': 0,
            'signal_type': 'MOMENTUM_BREAKOUT',
            'reason': [],
            'evidence': [],
            'pump_time': "Unknown"
        }
        
        if klines_5m is None or klines_5m.empty or len(klines_5m) < 24:  # Min 24 candles (supports 15m = 6h)
            return analysis
        
        # FILTER: Reject coins that are DUMPING (24h price change < -5%)
        # Prevents false positives on dead cat bounces (e.g., DFUSDT -38%, FIROUSDT -25%)
        if ticker_data:
            try:
                pct_24h = float(ticker_data.get('priceChangePercent', 0))
                if pct_24h < -5:
                    return analysis  # Skip dumping coins entirely
            except:
                pass
        
        try:
            # Dynamic lookback: use all available data up to 72 candles
            lookback = min(72, len(klines_5m))
            recent = klines_5m.tail(lookback)
            
            # ---- Calculate rolling metrics ----
            # Average volume over available lookback
            avg_vol_6h = float(klines_5m['quote_volume'].tail(lookback).mean())
            avg_trades_6h = float(klines_5m['trades'].astype(float).tail(lookback).mean())
            
            # Current candle metrics
            current_candle = klines_5m.iloc[-1]
            current_vol = float(current_candle['quote_volume'])
            current_trades = int(current_candle['trades'])
            current_price = float(current_candle['close'])
            
            # Taker buy ratio on current candle
            taker_buy_quote = float(current_candle.get('taker_buy_quote', 0))
            buy_ratio = taker_buy_quote / current_vol if current_vol > 0 else 0.5
            
            # 1h price momentum (12 candles ago)
            if len(klines_5m) >= 12:
                price_12_ago = float(klines_5m.iloc[-12]['close'])
                price_1h_change = ((current_price - price_12_ago) / price_12_ago) * 100
            else:
                price_1h_change = 0
            
            # Spike ratios
            vol_spike = current_vol / avg_vol_6h if avg_vol_6h > 0 else 1
            trades_spike = current_trades / avg_trades_6h if avg_trades_6h > 0 else 1
            
            # Also check cluster of recent candles (last 3 candles = 15 min)
            last_3_vol = float(klines_5m['quote_volume'].tail(3).mean())
            last_3_trades = float(klines_5m['trades'].astype(float).tail(3).mean())
            vol_spike_cluster = last_3_vol / avg_vol_6h if avg_vol_6h > 0 else 1
            trades_spike_cluster = last_3_trades / avg_trades_6h if avg_trades_6h > 0 else 1
            
            # ---- Multi-signal confluence detection ----
            signals = 0
            signal_score = 0
            
            # Signal 1: Volume Spike > 2.0x
            vol_detected = vol_spike > 2.0 or vol_spike_cluster > 1.8
            if vol_detected:
                signals += 1
                spike_val = max(vol_spike, vol_spike_cluster)
                signal_score += min(25, int(spike_val * 5))
                analysis['evidence'].append(f"⚡ Vol Spike: {spike_val:.1f}x (vs 6h avg)")
            
            # Signal 2: Trades Spike > 2.0x
            trades_detected = trades_spike > 2.0 or trades_spike_cluster > 1.8
            if trades_detected:
                signals += 1
                trd_val = max(trades_spike, trades_spike_cluster)
                signal_score += min(20, int(trd_val * 4))
                analysis['evidence'].append(f"📈 Trades Spike: {trd_val:.1f}x (vs 6h avg)")
            
            # Signal 3: Taker Buy Ratio > 65% (whale buying)
            # Also check smoothed buy ratio over last 3 candles
            last_3_buy = float(klines_5m['taker_buy_quote'].tail(3).sum())
            last_3_total = float(klines_5m['quote_volume'].tail(3).sum())
            buy_ratio_smooth = last_3_buy / last_3_total if last_3_total > 0 else 0.5
            
            whale_buying = buy_ratio > 0.60 or buy_ratio_smooth > 0.58
            if whale_buying:
                signals += 1
                best_buy = max(buy_ratio, buy_ratio_smooth)
                signal_score += min(20, int((best_buy - 0.5) * 100))
                analysis['evidence'].append(f"🐋 Whale Buy: {best_buy:.0%} taker buy ratio")
            
            # Signal 4: Price momentum > 1.5% in 1h
            momentum_detected = price_1h_change > 1.5
            if momentum_detected:
                signals += 1
                signal_score += min(20, int(price_1h_change * 3))
                analysis['evidence'].append(f"🚀 Momentum: +{price_1h_change:.1f}% (1h)")
            
            # Signal 5: Consecutive Whale Buy (NEW — catches ESPUSDT 23:35-23:45 pattern)
            # Check last 6 candles for 3+ consecutive with Taker Buy > 60%
            consecutive_whale = 0
            max_consecutive = 0
            whale_candles_detail = []
            
            check_range = min(6, len(klines_5m))
            for ci in range(len(klines_5m) - check_range, len(klines_5m)):
                candle = klines_5m.iloc[ci]
                c_vol = float(candle['quote_volume'])
                c_buy = float(candle.get('taker_buy_quote', 0))
                c_ratio = c_buy / c_vol if c_vol > 0 else 0.5
                
                if c_ratio > 0.60:
                    consecutive_whale += 1
                    max_consecutive = max(max_consecutive, consecutive_whale)
                    whale_candles_detail.append(f"{c_ratio:.0%}")
                else:
                    consecutive_whale = 0
            
            whale_accumulation = max_consecutive >= 2
            if whale_accumulation:
                signals += 1
                signal_score += 20 + min(15, (max_consecutive - 3) * 5)  # +20 base, +5 per extra
                ratios_str = ', '.join(whale_candles_detail[-max_consecutive:])
                analysis['evidence'].append(f"🐋🐋 Whale Accumulation: {max_consecutive} nến liên tiếp Buy>{60}% [{ratios_str}]")
            
            # ---- Detection Decision ----
            # Need at least 2 of 5 signals
            if signals >= 2:
                analysis['detected'] = True
                
                # Base score + signal score
                base_bonus = 15  # Pattern detection base
                total_score = min(100, signal_score + base_bonus)
                
                # Extra bonus for 3+ signals (strong confluence)
                if signals >= 3:
                    total_score = min(100, total_score + 10)
                    analysis['evidence'].append(f"💎 Strong Confluence: {signals}/4 signals")
                if signals >= 4:
                    total_score = min(100, total_score + 10)
                
                # EARLY WARNING BOOST: For 2-signal detections,
                # boost score if 24h volume is abnormally high vs historical
                if signals == 2 and ticker_data:
                    try:
                        vol_24h = float(ticker_data.get('quoteVolume', 0))
                        # If 24h volume > $1M for a micro-cap, it's unusual
                        if vol_24h > 1000000:
                            total_score = min(100, total_score + 15)
                            analysis['evidence'].append(f"📊 Vol24h Boost: ${vol_24h:,.0f} (>$1M)")
                        elif vol_24h > 500000:
                            total_score = min(100, total_score + 10)
                            analysis['evidence'].append(f"📊 Vol24h Boost: ${vol_24h:,.0f} (>$500K)")
                    except:
                        pass
                
                # Funding rate check
                funding_rate = 0.0
                try:
                    funding_rate = self.binance.get_funding_rate(symbol)
                    if funding_rate < 0:
                        total_score = min(100, total_score + 5)
                        analysis['evidence'].append(f"🩸 Funding Rate: {funding_rate*100:.4f}% (Short Squeeze)")
                    else:
                        analysis['evidence'].append(f"ℹ️ Funding Rate: {funding_rate*100:.4f}%")
                except:
                    pass
                
                analysis['quality_score'] = total_score
                analysis['confidence'] = total_score
                analysis['funding_rate'] = funding_rate
                analysis['vol_ratio'] = vol_spike
                
                # Store volume data
                if ticker_data:
                    analysis['vol_24h'] = float(ticker_data.get('volume', 0))
                    analysis['vol_24h_usdt'] = float(ticker_data.get('quoteVolume', 0))
                    analysis['price_change_24h'] = float(ticker_data.get('priceChangePercent', 0))
                else:
                    analysis['vol_24h'] = 0
                    analysis['vol_24h_usdt'] = 0
                    analysis['price_change_24h'] = 0
                
                analysis['red_candles_6'] = 0  # Not applicable for momentum
                
                # Evidence summary
                analysis['evidence'].append(f"🔥 Early Momentum: Score {total_score}/100 ({signals}/4 signals)")
                
                # Pump time estimate based on signal strength
                if signals >= 3:
                    analysis['pump_time'] = "Trong 1-4h tới"
                else:
                    analysis['pump_time'] = "Trong 4-12h tới"
                analysis['evidence'].append(f"⏳ Dự Kiến Pump: {analysis['pump_time']}")
                
                # Calculate entry zone from recent 5m data
                entry_low = float(klines_5m['low'].tail(12).min())
                entry_high = current_price
                analysis['entry_zone'] = (entry_low, entry_high)
                
                # Dynamic TP/SL for momentum trades (wider targets)
                atr = self._calculate_atr(klines_5m, period=14)
                tp_sl_info = self._calculate_dynamic_tp_sl(
                    current_price, atr, total_score, vol_spike
                )
                analysis['tp_sl_info'] = tp_sl_info
                
        except Exception as e:
            logger.error(f"Error in early momentum detection for {symbol}: {e}")
        
        return analysis

    def _detect_institutional_activity(self, klines: pd.DataFrame, trades: List[Dict], market_data: Dict) -> Dict:
        """
        QUAN TRỌNG NHẤT! (30 points)
        
        Phát hiện institutional/smart money activity:
        - Large block trades
        - Accumulation/Distribution patterns
        - Wyckoff analysis
        - Upgrade: STEALTH ACCUMULATION (Gemini X2 logic)
        """
        
        analysis = {
            'institutional_score': 0,  # 0-100
            'is_institutional': False,
            'activity_type': 'NONE',  # ACCUMULATION | DISTRIBUTION | NEUTRAL
            'block_trades_detected': False,
            'smart_money_flow': 'NEUTRAL',  # INFLOW | OUTFLOW | NEUTRAL
            'confidence': 0,
            'evidence': [],
            'stealth_accumulation': False  # New flag
        }
        
        if klines.empty:
            return analysis
        
        # === 0. STEALTH ACCUMULATION (GEMINI X2) ===
        stealth = self._detect_stealth_accumulation(klines)
        if stealth['detected']:
            analysis['stealth_accumulation'] = True
            analysis['activity_type'] = 'ACCUMULATION'
            analysis['evidence'].extend(stealth['evidence'])
            analysis['evidence'].append("💎 TÍN HIỆU GEMINI X2 DETECTED")

        # === 1. BLOCK TRADES DETECTION ===
        if trades and len(trades) > 100:
            try:
                trade_sizes = [float(t.get('qty', 0)) for t in trades]
                mean_size = np.mean(trade_sizes)
                
                # Block trade = > 10x mean size
                block_trades = [t for t in trades if float(t.get('qty', 0)) > mean_size * 10]
                
                if len(block_trades) > 5:
                    analysis['block_trades_detected'] = True
                    
                    # Check buy vs sell
                    block_buys = [t for t in block_trades if not t.get('isBuyerMaker', True)]
                    block_sells = [t for t in block_trades if t.get('isBuyerMaker', True)]
                    
                    if len(block_buys) > len(block_sells) * 1.5:
                        analysis['smart_money_flow'] = 'INFLOW'
                        analysis['evidence'].append(f"🐋 {len(block_buys)} large buy blocks vs {len(block_sells)} sell → Accumulation")
                    elif len(block_sells) > len(block_buys) * 1.5:
                        analysis['smart_money_flow'] = 'OUTFLOW'
                        analysis['evidence'].append(f"🐋 {len(block_sells)} large sell blocks vs {len(block_buys)} buy → Distribution")
            except:
                pass
        
        # === 2. WYCKOFF ACCUMULATION/DISTRIBUTION ===
        try:
            recent = klines.tail(100)
            
            price_range = recent['high'].max() - recent['low'].min()
            avg_range = (recent['high'] - recent['low']).mean()
            
            if price_range < avg_range * 20:  # Trong range hẹp
                # Check volume declining
                volume_trend = np.polyfit(range(len(recent)), recent['volume'].values, 1)[0]
                
                if volume_trend < 0:  # Volume giảm trong range
                    # Check có spring/test không
                    last_10 = recent.tail(10)
                    
                    if last_10['low'].min() < recent.tail(50)['low'].quantile(0.1):
                        if last_10['volume'].max() > recent['volume'].mean() * 2:
                            analysis['activity_type'] = 'ACCUMULATION'
                            analysis['evidence'].append("📈 Wyckoff Accumulation detected: Range + declining volume + spring")
            
            # Check Distribution
            if recent['high'].max() > recent.tail(50)['high'].quantile(0.9):
                last_10 = recent.tail(10)
                volume_spike = last_10['volume'].max() > recent['volume'].mean() * 2.5
                
                if volume_spike and last_10['close'].iloc[-1] < last_10['open'].iloc[0]:
                    analysis['activity_type'] = 'DISTRIBUTION'
                    analysis['evidence'].append("📉 Wyckoff Distribution detected: New high + volume spike + rejection")
        except:
            pass
        
        # === INSTITUTIONAL SCORE ===
        score = 0
        
        if analysis['stealth_accumulation']:
            score += 50  # Very high weight for Gemini X2 pattern
        
        if analysis['block_trades_detected']:
            score += 40
        
        if analysis['activity_type'] == 'ACCUMULATION':
            score += 35
        elif analysis['activity_type'] == 'DISTRIBUTION':
            score += 25
        
        if analysis['smart_money_flow'] == 'INFLOW':
            score += 15
        elif analysis['smart_money_flow'] == 'OUTFLOW':
            score += 10
        
        analysis['institutional_score'] = min(100, score)
        analysis['is_institutional'] = score >= 50
        analysis['confidence'] = score
        
        return analysis
    
    def _calculate_direction_probability(self, results: Dict) -> Dict:
        """
        Tính xác suất hướng di chuyển dựa trên tất cả indicators
        """
        
        prob = {
            'up': 50,
            'down': 50,
            'sideways': 50
        }
        
        # === INSTITUTIONAL FLOW (tác động mạnh nhất) ===
        inst = results.get('institutional_flow', {})
        
        if inst.get('activity_type') == 'ACCUMULATION':
            prob['up'] += 20
            prob['down'] -= 10
            prob['sideways'] -= 10
        elif inst.get('activity_type') == 'DISTRIBUTION':
            prob['down'] += 20
            prob['up'] -= 10
            prob['sideways'] -= 10
        
        if inst.get('smart_money_flow') == 'INFLOW':
            prob['up'] += 15
            prob['down'] -= 10
        elif inst.get('smart_money_flow') == 'OUTFLOW':
            prob['down'] += 15
            prob['up'] -= 10
        
        # === BOT ACTIVITY ===
        bot = results.get('bot_activity', {})
        
        if bot.get('dump_bot', {}).get('detected'):
            prob['down'] += 15
            prob['up'] -= 10
        
        if bot.get('wash_trading', {}).get('detected'):
            prob['sideways'] += 10
            prob['up'] -= 5
            prob['down'] -= 5
        
        # === VOLUME LEGITIMACY ===
        vol = results.get('volume_analysis', {})
        
        if vol.get('is_legitimate'):
            if vol.get('buy_sell_ratio', 1) > 1.2:
                prob['up'] += 10
                prob['down'] -= 5
            elif vol.get('buy_sell_ratio', 1) < 0.8:
                prob['down'] += 10
                prob['up'] -= 5
        else:
            prob['sideways'] += 10
            prob['down'] += 5
            prob['up'] -= 15
        
        # === ORDER BOOK MANIPULATION ===
        depth = results.get('depth_analysis', {})
        
        if depth.get('is_manipulated'):
            prob['sideways'] += 10
            prob['up'] -= 5
            prob['down'] -= 5
        
        if depth.get('wall_detection', {}).get('bid_wall'):
            prob['up'] += 8
        
        if depth.get('wall_detection', {}).get('ask_wall'):
            prob['down'] += 8
        
        # === PRICE ACTION QUALITY ===
        price_qual = results.get('price_quality', {})
        
        if price_qual.get('is_organic'):
            if price_qual.get('clean_breakouts'):
                prob['up'] += 12
                prob['down'] -= 8
        
        # === NORMALIZE ===
        total = prob['up'] + prob['down'] + prob['sideways']
        prob['up'] = int(prob['up'] / total * 100)
        prob['down'] = int(prob['down'] / total * 100)
        prob['sideways'] = int(prob['sideways'] / total * 100)
        
        return prob
    
    def _calculate_overall_confidence(self, results: Dict) -> int:
        """
        Tính confidence tổng thể (0-100)
        """
        
        weights = {
            'institutional_flow': 0.35,
            'volume_analysis': 0.25,
            'price_quality': 0.20,
            'depth_analysis': 0.15,
            'bot_activity': 0.05
        }
        
        confidence = 0
        
        inst_score = results.get('institutional_flow', {}).get('institutional_score', 0)
        confidence += inst_score * weights['institutional_flow']
        
        vol_score = results.get('volume_analysis', {}).get('legitimacy_score', 50)
        confidence += vol_score * weights['volume_analysis']
        
        price_score = results.get('price_quality', {}).get('quality_score', 50)
        confidence += price_score * weights['price_quality']
        
        # Depth: manipulation_score càng cao càng BAD → reverse
        depth_score = 100 - results.get('depth_analysis', {}).get('manipulation_score', 50)
        confidence += depth_score * weights['depth_analysis']
        
        # Bot: có bot = bad → penalty
        bot_detected = sum([
            results.get('bot_activity', {}).get('wash_trading', {}).get('detected', False),
            results.get('bot_activity', {}).get('spoofing', {}).get('detected', False),
            results.get('bot_activity', {}).get('dump_bot', {}).get('detected', False)
        ])
        bot_score = max(0, 100 - bot_detected * 20)
        confidence += bot_score * weights['bot_activity']
        
        return int(confidence)
    
    def _determine_final_signal(self, direction_prob: Dict, confidence: int, results: Dict) -> str:
        """
        Xác định signal cuối cùng
        """
        
        up_prob = direction_prob.get('up', 50)
        down_prob = direction_prob.get('down', 50)
        
        # Cần confidence >= 70 để đưa ra signal mạnh
        if confidence < 60:
            return 'NEUTRAL'
        
        if up_prob >= 70 and confidence >= 75:
            return 'STRONG_PUMP'
        elif up_prob >= 60 and confidence >= 65:
            return 'PUMP'
        elif down_prob >= 70 and confidence >= 75:
            return 'STRONG_DUMP'
        elif down_prob >= 60 and confidence >= 65:
            return 'DUMP'
        else:
            return 'NEUTRAL'
    
    def _assess_risk_level(self, results: Dict) -> str:
        """
        Đánh giá mức độ rủi ro
        """
        
        risk_score = 0
        
        # BOT activity = risk
        bot = results.get('bot_activity', {})
        if bot.get('wash_trading', {}).get('detected'):
            risk_score += 25
        if bot.get('spoofing', {}).get('detected'):
            risk_score += 20
        if bot.get('dump_bot', {}).get('detected'):
            risk_score += 30
        
        # Order book manipulation = risk
        if results.get('depth_analysis', {}).get('is_manipulated'):
            risk_score += 20
        
        # Volume không legitimate = risk
        if not results.get('volume_analysis', {}).get('is_legitimate'):
            risk_score += 15
        
        # Institutional activity = giảm risk
        if results.get('institutional_flow', {}).get('is_institutional'):
            risk_score -= 20
        
        risk_score = max(0, min(100, risk_score))
        
        if risk_score >= 70:
            return 'EXTREME'
        elif risk_score >= 50:
            return 'HIGH'
        elif risk_score >= 30:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _generate_recommendation(self, results: Dict, symbol: str) -> Dict:
        """
        Tạo recommendation chi tiết
        """
        
        signal = results.get('signal', 'NEUTRAL')
        confidence = results.get('confidence', 0)
        risk = results.get('risk_level', 'MEDIUM')
        direction_prob = results.get('direction_probability', {})
        
        recommendation = {
            'action': 'WAIT',
            'position_size': '0%',
            'entry_strategy': '',
            'stop_loss_note': '',
            'take_profit_note': '',
            'reasoning': [],
            'warnings': []
        }
        
        # === STRONG_PUMP ===
        if signal == 'STRONG_PUMP' and confidence >= 75:
            recommendation['action'] = 'BUY'
            recommendation['position_size'] = '2-3%' if risk == 'LOW' else '1-2%'
            recommendation['entry_strategy'] = 'Enter on pullback to support or breakout confirmation'
            recommendation['stop_loss_note'] = 'Below recent swing low or support level'
            recommendation['take_profit_note'] = 'Scale out at resistance levels, trail stop'
            
            recommendation['reasoning'].append(f"✅ Strong upward probability: {direction_prob.get('up')}%")
            recommendation['reasoning'].append(f"✅ High confidence: {confidence}%")
            
            if results.get('institutional_flow', {}).get('activity_type') == 'ACCUMULATION':
                recommendation['reasoning'].append("✅ Institutional accumulation detected")
            
            if results.get('volume_analysis', {}).get('is_legitimate'):
                recommendation['reasoning'].append("✅ Legitimate volume confirms move")
        
        # === PUMP ===
        elif signal == 'PUMP' and confidence >= 65:
            recommendation['action'] = 'BUY'
            recommendation['position_size'] = '1-2%'
            recommendation['entry_strategy'] = 'Enter with caution, use tight stop loss'
            recommendation['stop_loss_note'] = 'Tight stop below entry 2-3%'
            recommendation['take_profit_note'] = 'Take profit quickly at first resistance'
            
            recommendation['reasoning'].append(f"⚠️ Moderate upward probability: {direction_prob.get('up')}%")
            recommendation['reasoning'].append(f"⚠️ Confidence: {confidence}%")
            
            if risk in ['HIGH', 'EXTREME']:
                recommendation['warnings'].append(f"⚠️ {risk} risk detected - reduce position size")
        
        # === STRONG_DUMP ===
        elif signal == 'STRONG_DUMP':
            recommendation['action'] = 'AVOID/SHORT'
            recommendation['reasoning'].append(f"🚨 Strong downward probability: {direction_prob.get('down')}%")
            
            if results.get('bot_activity', {}).get('dump_bot', {}).get('detected'):
                recommendation['warnings'].append("🚨 Dump BOT detected - avoid long positions")
            
            if results.get('institutional_flow', {}).get('activity_type') == 'DISTRIBUTION':
                recommendation['warnings'].append("🚨 Institutional distribution - smart money exiting")
        
        # === DUMP ===
        elif signal == 'DUMP':
            recommendation['action'] = 'AVOID'
            recommendation['reasoning'].append(f"⚠️ Downward probability: {direction_prob.get('down')}%")
            recommendation['warnings'].append("⚠️ Wait for reversal confirmation before entry")
        
        # === NEUTRAL ===
        else:
            recommendation['action'] = 'WAIT'
            recommendation['reasoning'].append("ℹ️ No clear directional signal")
            recommendation['reasoning'].append(f"Probabilities - Up: {direction_prob.get('up')}%, Down: {direction_prob.get('down')}%, Sideways: {direction_prob.get('sideways')}%")
            
            if confidence < 60:
                recommendation['warnings'].append("⚠️ Low confidence - wait for clearer setup")
            
            if results.get('bot_activity', {}).get('wash_trading', {}).get('detected'):
                recommendation['warnings'].append("⚠️ Wash trading detected - volume may be fake")
        
        return recommendation


def integrate_advanced_detection_to_prompt(results: Dict) -> str:
    """
    Tạo text để insert vào Gemini prompt
    """
    
    signal = results.get('signal', 'NEUTRAL')
    confidence = results.get('confidence', 0)
    direction_prob = results.get('direction_probability', {})
    risk = results.get('risk_level', 'MEDIUM')
    
    prompt_addition = f"""
═══════════════════════════════════════════════════════════════════════════════
🤖 ADVANCED PUMP/DUMP DETECTION SYSTEM (v4.0)
═══════════════════════════════════════════════════════════════════════════════

**FINAL SIGNAL**: {signal} (Confidence: {confidence}%)
**RISK LEVEL**: {risk}

**DIRECTION PROBABILITIES**:
• UP: {direction_prob.get('up', 0)}%
• DOWN: {direction_prob.get('down', 0)}%
• SIDEWAYS: {direction_prob.get('sideways', 0)}%

**BOT ACTIVITY DETECTION**:
"""
    
    bot = results.get('bot_activity', {})
    for bot_type, data in bot.items():
        if data.get('detected'):
            prompt_addition += f"⚠️ {bot_type.upper().replace('_', ' ')} DETECTED (Confidence: {data.get('confidence')}%)\n"
            for evidence in data.get('evidence', []):
                prompt_addition += f"   - {evidence}\n"
    
    if not any([data.get('detected') for data in bot.values()]):
        prompt_addition += "✅ No bot activity detected\n"
    
    prompt_addition += f"""
**VOLUME LEGITIMACY**:
• Score: {results.get('volume_analysis', {}).get('legitimacy_score', 0)}/100
• Quality: {results.get('volume_analysis', {}).get('volume_quality', 'UNKNOWN')}
• Buy/Sell Ratio: {results.get('volume_analysis', {}).get('buy_sell_ratio', 0):.2f}
• Is Legitimate: {'✅ YES' if results.get('volume_analysis', {}).get('is_legitimate') else '❌ NO'}

**ORDER BOOK ANALYSIS**:
• Manipulation Score: {results.get('depth_analysis', {}).get('manipulation_score', 0)}/100
• Bid Wall: {'⚠️ YES' if results.get('depth_analysis', {}).get('wall_detection', {}).get('bid_wall') else '✅ No'}
• Ask Wall: {'⚠️ YES' if results.get('depth_analysis', {}).get('wall_detection', {}).get('ask_wall') else '✅ No'}
• Layering: {'⚠️ DETECTED' if results.get('depth_analysis', {}).get('layering_detected') else '✅ No'}

**INSTITUTIONAL FLOW** (⭐ MOST IMPORTANT):
• Score: {results.get('institutional_flow', {}).get('institutional_score', 0)}/100
• Activity: {results.get('institutional_flow', {}).get('activity_type', 'NONE')}
• Smart Money Flow: {results.get('institutional_flow', {}).get('smart_money_flow', 'NEUTRAL')}
• Block Trades: {'✅ DETECTED' if results.get('institutional_flow', {}).get('block_trades_detected') else 'No'}

**PRICE ACTION QUALITY**:
• Score: {results.get('price_quality', {}).get('quality_score', 0)}/100
• Is Organic: {'✅ YES' if results.get('price_quality', {}).get('is_organic') else '❌ NO'}
• Respects Levels: {'✅ YES' if results.get('price_quality', {}).get('respects_levels') else 'No'}

**RECOMMENDATION**:
Action: {results.get('recommendation', {}).get('action', 'WAIT')}
Position Size: {results.get('recommendation', {}).get('position_size', 'N/A')}

Reasoning:
"""
    
    for reason in results.get('recommendation', {}).get('reasoning', []):
        prompt_addition += f"• {reason}\n"
    
    if results.get('recommendation', {}).get('warnings'):
        prompt_addition += "\nWarnings:\n"
        for warning in results.get('recommendation', {}).get('warnings', []):
            prompt_addition += f"• {warning}\n"
    
    prompt_addition += """
═══════════════════════════════════════════════════════════════════════════════
⚠️ CRITICAL INSTRUCTIONS FOR AI:
═══════════════════════════════════════════════════════════════════════════════

1. **PRIORITIZE INSTITUTIONAL FLOW** (35% weight in your analysis)
   - If ACCUMULATION detected → Strong bias toward BUY
   - If DISTRIBUTION detected → Strong bias toward SELL/WAIT
   - If block trades detected → High confidence signal

2. **ADJUST FOR BOT ACTIVITY** (reduce confidence by 10-30%)
   - Wash Trading → Volume is fake, lower confidence
   - Dump BOT → Avoid BUY, recommend WAIT or SHORT
   - Spoofing → Order book is manipulated, be cautious

3. **VOLUME LEGITIMACY CHECK** (25% weight)
   - If legitimacy_score < 50 → Reduce confidence by 20%
   - If buy/sell ratio > 1.5 → Bullish bias
   - If buy/sell ratio < 0.7 → Bearish bias

4. **ORDER BOOK MANIPULATION** (15% weight)
   - If manipulation_score > 60 → Add warning
   - Bid wall + uptrend → Possible pump setup (but watch for fake)
   - Ask wall + downtrend → Distribution pressure

5. **DIRECTION PROBABILITY INTEGRATION**
   - Use the UP/DOWN/SIDEWAYS percentages in your reasoning
   - If UP > 70% and confidence > 75% → Recommend BUY
   - If DOWN > 70% and confidence > 75% → Recommend WAIT/SHORT
   - If SIDEWAYS > 50% → Recommend WAIT for breakout

6. **RISK LEVEL ADJUSTMENT**
   - EXTREME/HIGH risk → Reduce position size to 0.5-1%
   - MEDIUM risk → Standard 1-2%
   - LOW risk → Can increase to 2-3%

7. **MANDATORY FIELDS TO UPDATE**:
   - confidence: Adjust based on advanced detection results
   - recommendation: Use advanced system's recommendation
   - reasoning_vietnamese: MUST mention institutional flow, bot activity, volume legitimacy
   - warnings: Include all warnings from advanced detection
   - risk_level: Use advanced system's risk_level

═══════════════════════════════════════════════════════════════════════════════
"""
    
    return prompt_addition

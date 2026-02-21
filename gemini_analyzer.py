"""
Gemini AI Trading Analyzer v3.3
Integrates Google Gemini 1.5 Pro for comprehensive trading analysis

Enhanced with:
- Advanced Pump/Dump Detector integration
- Real-time data from 15+ sources
- Sentiment analysis & on-chain data
- Institutional flow detection
- 5 BOT type detection

Author: AI Assistant
Date: November 20, 2025
"""

from google import genai
from google.genai import types as genai_types
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time
import os

logger = logging.getLogger(__name__)

# Import database and price tracker
try:
    from database import get_db, AnalysisDatabase
    from price_tracker import get_tracker, PriceTracker
    DATABASE_AVAILABLE = True
    logger.info("✅ Database and Price Tracker modules loaded")
except ImportError as e:
    logger.warning(f"⚠️ Database/Price Tracker not available: {e}")
    DATABASE_AVAILABLE = False

# Import advanced detection
try:
    from advanced_pump_detector import AdvancedPumpDumpDetector, integrate_advanced_detection_to_prompt
    ADVANCED_DETECTOR_AVAILABLE = True
    logger.info("✅ Advanced Pump/Dump Detector loaded")
except ImportError as e:
    logger.warning(f"⚠️ Advanced Detector not available: {e}")
    ADVANCED_DETECTOR_AVAILABLE = False


class GeminiAnalyzer:
    """
    Google Gemini AI integration for advanced trading analysis v3.3
    
    Features:
    - Comprehensive multi-indicator analysis
    - Historical comparison (week-over-week)
    - Scalping and swing trading recommendations
    - Risk assessment and entry/exit points
    - Vietnamese language output
    - Advanced pump/dump detection with institutional flow
    - 5 BOT type detection (Wash Trading, Spoofing, Iceberg, Market Maker, Dump)
    """
    
    def __init__(self, api_key: str, binance_client, stoch_rsi_analyzer):
        """
        Initialize Gemini analyzer
        
        Args:
            api_key: Google Gemini API key
            binance_client: BinanceClient instance
            stoch_rsi_analyzer: StochRSIAnalyzer instance
        """
        self.api_key = api_key
        self.binance = binance_client
        self.stoch_rsi_analyzer = stoch_rsi_analyzer
        
        # Initialize database connection
        self.db = None
        self.tracker = None
        self.db_available = DATABASE_AVAILABLE  # Store as instance variable
        
        if self.db_available:
            try:
                self.db = get_db()
                self.tracker = get_tracker()
                logger.info("✅ Database and Price Tracker initialized")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize database/tracker: {e}")
                self.db_available = False
        
        # Initialize institutional indicator modules
        from volume_profile import VolumeProfileAnalyzer
        from fair_value_gaps import FairValueGapDetector
        from order_blocks import OrderBlockDetector
        from support_resistance import SupportResistanceDetector
        from smart_money_concepts import SmartMoneyAnalyzer
        
        self.volume_profile = VolumeProfileAnalyzer(binance_client)
        self.fvg_detector = FairValueGapDetector(binance_client)
        self.ob_detector = OrderBlockDetector(binance_client)
        self.sr_detector = SupportResistanceDetector(binance_client)
        self.smc_analyzer = SmartMoneyAnalyzer(binance_client)
        
        # Initialize Advanced Detector (NEW)
        self.advanced_detector = None
        if ADVANCED_DETECTOR_AVAILABLE:
            try:
                self.advanced_detector = AdvancedPumpDumpDetector(binance_client)
                logger.info("✅ Advanced Pump/Dump Detector initialized")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize Advanced Detector: {e}")
        
        # Configure Gemini with new google.genai SDK
        self.client = genai.Client(api_key=api_key)
        self.model_name = 'gemini-2.5-flash'
        # Google Search grounding config
        self.generate_config = genai_types.GenerateContentConfig(
            tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())]
        )
        logger.info("Gemini client initialized with google.genai SDK")
        
        # Cache system (15 minutes)
        self.cache = {}  # {symbol: {'data': result, 'timestamp': time.time()}}
        self.cache_duration = 900  # 15 minutes in seconds
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # 1 second between requests
        
        logger.info("✅ Gemini AI Analyzer v3.3 initialized (gemini-2.5-flash + Google Search Grounding + Advanced Detection)")
    
    def _check_cache(self, symbol: str) -> Optional[Dict]:
        """
        Check if cached result exists and is still valid
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Cached result or None
        """
        if symbol in self.cache:
            cached_data = self.cache[symbol]
            age = time.time() - cached_data['timestamp']
            
            if age < self.cache_duration:
                logger.info(f"Using cached AI analysis for {symbol} (age: {age:.0f}s)")
                return cached_data['data']
            else:
                # Expired, remove from cache
                del self.cache[symbol]
        
        return None
    
    def _update_cache(self, symbol: str, result: Dict):
        """
        Update cache with new result
        
        Args:
            symbol: Trading symbol
            result: Analysis result to cache
        """
        self.cache[symbol] = {
            'data': result,
            'timestamp': time.time()
        }
        logger.info(f"Cached AI analysis for {symbol}")
    
    def _rate_limit(self):
        """Apply rate limiting between requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def collect_data(self, symbol: str, pump_data: Optional[Dict] = None) -> Dict:
        """
        Collect all analysis data for a symbol
        
        Args:
            symbol: Trading symbol
            pump_data: Optional pump detector data
            
        Returns:
            Dict with all indicator data
        """
        try:
            logger.info(f"Collecting data for {symbol}...")
            
            # Get current price and 24h data
            ticker_24h = self.binance.get_24h_data(symbol)
            if not ticker_24h:
                logger.error(f"Failed to get 24h data for {symbol}")
                return None
            
            current_price = ticker_24h['last_price']
            logger.info(f"Current price for {symbol}: ${current_price:,.2f}")
            
            # Get multi-timeframe klines with historical depth
            # Use different limits per timeframe for optimal historical context
            logger.info(f"Fetching historical klines for {symbol}...")
            klines_dict = {}
            
            # 5m: 100 candles (8.3 hours) - for short-term patterns
            df_5m = self.binance.get_klines(symbol, '5m', limit=100)
            if df_5m is not None and not df_5m.empty:
                klines_dict['5m'] = df_5m
            
            # 1h: 168 candles (7 days) - for intraday analysis
            df_1h = self.binance.get_klines(symbol, '1h', limit=168)
            if df_1h is not None and not df_1h.empty:
                klines_dict['1h'] = df_1h
            
            # 4h: 180 candles (30 days) - for swing trading
            df_4h = self.binance.get_klines(symbol, '4h', limit=180)
            if df_4h is not None and not df_4h.empty:
                klines_dict['4h'] = df_4h
            
            # 1d: 90 candles (3 months) - for trend analysis
            df_1d = self.binance.get_klines(symbol, '1d', limit=90)
            if df_1d is not None and not df_1d.empty:
                klines_dict['1d'] = df_1d
            
            if not klines_dict or len(klines_dict) == 0:
                logger.error(f"Failed to get klines data for {symbol}")
                return None
            
            logger.info(f"Got klines for {symbol}: {list(klines_dict.keys())}")
            
            # RSI+MFI analysis
            from indicators import analyze_multi_timeframe
            import config
            logger.info(f"Calculating RSI+MFI for {symbol}...")
            rsi_mfi_result = analyze_multi_timeframe(
                klines_dict,
                config.RSI_PERIOD,
                config.MFI_PERIOD,
                config.RSI_LOWER,
                config.RSI_UPPER,
                config.MFI_LOWER,
                config.MFI_UPPER
            )
            
            # Stoch+RSI analysis
            logger.info(f"Calculating Stoch+RSI for {symbol}...")
            stoch_rsi_result = self.stoch_rsi_analyzer.analyze_multi_timeframe(
                symbol,
                timeframes=['1m', '5m', '1h', '4h', '1d']
            )
            
            # Volume data
            volume_data = {
                'current': ticker_24h['volume'] if ticker_24h else 0,
                'base_volume': ticker_24h['base_volume'] if ticker_24h else 0,
                'trades': ticker_24h['trades'] if ticker_24h else 0
            }
            
            # INSTITUTIONAL INDICATORS
            
            # Volume Profile (1h, 4h, 1d)
            logger.info(f"Analyzing Volume Profile for {symbol}...")
            vp_result = self.volume_profile.analyze_multi_timeframe(symbol, ['1h', '4h', '1d'])
            
            # Fair Value Gaps (1h, 4h, 1d)
            logger.info(f"Detecting Fair Value Gaps for {symbol}...")
            fvg_result = self.fvg_detector.analyze_multi_timeframe(symbol, ['1h', '4h', '1d'])
            
            # Order Blocks (1h, 4h, 1d)
            logger.info(f"Detecting Order Blocks for {symbol}...")
            ob_result = self.ob_detector.analyze_multi_timeframe(symbol, ['1h', '4h', '1d'])
            
            # Support/Resistance zones (1h, 4h, 1d)
            logger.info(f"Analyzing Support/Resistance for {symbol}...")
            sr_result = self.sr_detector.analyze_multi_timeframe(symbol, ['1h', '4h', '1d'])
            
            # Smart Money Concepts (1h, 4h, 1d)
            logger.info(f"Analyzing Smart Money Concepts for {symbol}...")
            smc_result = self.smc_analyzer.analyze_multi_timeframe(symbol, ['1h', '4h', '1d'])
            
            # Historical comparison (week-over-week)
            logger.info(f"Calculating historical comparison for {symbol}...")
            historical = self._get_historical_comparison(symbol, klines_dict)
            
            # Extended historical klines context (reuse klines_dict data)
            logger.info(f"Analyzing extended historical context for {symbol}...")
            historical_klines = {}
            if '1h' in klines_dict and klines_dict['1h'] is not None:
                historical_klines['1h'] = self._analyze_historical_period(klines_dict['1h'], '1H (7 ngày)')
            if '4h' in klines_dict and klines_dict['4h'] is not None:
                historical_klines['4h'] = self._analyze_historical_period(klines_dict['4h'], '4H (30 ngày)')
            if '1d' in klines_dict and klines_dict['1d'] is not None:
                historical_klines['1d'] = self._analyze_historical_period(klines_dict['1d'], '1D (90 ngày)')
            
            logger.info(f"✅ Analyzed historical context for {len(historical_klines)} timeframes")
            
            # Market data
            market_data = {
                'price': current_price,
                'price_change_24h': ticker_24h['price_change_percent'],
                'high_24h': ticker_24h['high'],
                'low_24h': ticker_24h['low'],
                'volume_24h': ticker_24h['volume']
            }
            
            # === ADVANCED PUMP/DUMP DETECTION (NEW!) ===
            advanced_detection = None
            if self.advanced_detector:
                try:
                    logger.info(f"🤖 Running advanced pump/dump detection for {symbol}...")
                    
                    # Get recent trades for advanced analysis
                    recent_trades = []
                    order_book = None
                    try:
                        recent_trades = self.binance.client.get_recent_trades(symbol=symbol, limit=500)
                        order_book = self.binance.client.get_order_book(symbol=symbol, limit=100)
                    except:
                        logger.debug("Could not fetch trades/orderbook for advanced detection")
                    
                    # Run comprehensive analysis
                    advanced_detection = self.advanced_detector.analyze_comprehensive(
                        symbol=symbol,
                        klines_5m=klines_dict.get('5m'),
                        klines_1h=klines_dict.get('1h'),
                        order_book=order_book,
                        trades=recent_trades,
                        market_data=ticker_24h
                    )
                    
                    if advanced_detection:
                        signal = advanced_detection.get('signal', 'NEUTRAL')
                        confidence = advanced_detection.get('confidence', 0)
                        direction_prob = advanced_detection.get('direction_probability', {})
                        
                        logger.info(f"✅ Advanced Detection: Signal={signal}, Confidence={confidence}%, UP={direction_prob.get('up')}%")
                        
                        # Log warnings
                        if signal in ['STRONG_DUMP', 'DUMP']:
                            logger.warning(f"⚠️ {symbol}: {signal} detected - Confidence {confidence}%")
                        
                        bot_activity = advanced_detection.get('bot_activity', {})
                        for bot_type, data in bot_activity.items():
                            if data.get('detected'):
                                logger.warning(f"🚨 {symbol}: {bot_type.upper()} BOT detected (confidence {data.get('confidence')}%)")
                
                except Exception as e:
                    logger.error(f"Error in advanced detection for {symbol}: {e}")
            
            logger.info(f"✅ Data collection complete for {symbol}")
            
            return {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'market_data': market_data,
                'rsi_mfi': rsi_mfi_result,
                'stoch_rsi': stoch_rsi_result,
                'pump_data': pump_data,
                'volume_data': volume_data,
                'historical': historical,
                'historical_klines': historical_klines,  # Extended historical context
                # Institutional indicators
                'volume_profile': vp_result,
                'fair_value_gaps': fvg_result,
                'order_blocks': ob_result,
                'support_resistance': sr_result,
                'smart_money_concepts': smc_result,
                # Advanced detection (NEW)
                'advanced_detection': advanced_detection
            }
            
        except Exception as e:
            logger.error(f"❌ Error collecting data for {symbol}: {e}", exc_info=True)
            return None
    
    def _get_historical_klines_context(self, symbol: str) -> Dict:
        """
        Get extended historical klines for better AI context
        - 1H: Last 7 days (168 candles)
        - 4H: Last 30 days (180 candles)
        - 1D: Last 90 days (90 candles)
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dict with historical klines statistics
        """
        try:
            result = {}
            
            # 1H Historical (7 days = 168 hours)
            logger.info(f"Getting 1H historical data for {symbol}...")
            df_1h = self.binance.get_klines(symbol, '1h', limit=168)
            if df_1h is not None and len(df_1h) > 0:
                result['1h'] = self._analyze_historical_period(df_1h, '1H (7 ngày)')
            
            # 4H Historical (30 days = 180 candles)
            logger.info(f"Getting 4H historical data for {symbol}...")
            df_4h = self.binance.get_klines(symbol, '4h', limit=180)
            if df_4h is not None and len(df_4h) > 0:
                result['4h'] = self._analyze_historical_period(df_4h, '4H (30 ngày)')
            
            # 1D Historical (90 days)
            logger.info(f"Getting 1D historical data for {symbol}...")
            df_1d = self.binance.get_klines(symbol, '1d', limit=90)
            if df_1d is not None and len(df_1d) > 0:
                result['1d'] = self._analyze_historical_period(df_1d, '1D (90 ngày)')
            
            logger.info(f"✅ Got historical context for {len(result)} timeframes")
            return result
            
        except Exception as e:
            logger.error(f"Error getting historical klines context: {e}")
            return {}
    
    def _analyze_historical_period(self, df, period_name: str) -> Dict:
        """
        Analyze a historical period and extract key statistics INCLUDING institutional indicators
        
        Args:
            df: DataFrame with OHLCV data
            period_name: Name of the period for logging
            
        Returns:
            Dict with statistics including institutional analysis
        """
        try:
            from indicators import calculate_rsi, calculate_mfi, calculate_hlcc4
            
            # Price statistics
            high_price = float(df['high'].max())
            low_price = float(df['low'].min())
            current_price = float(df['close'].iloc[-1])
            avg_price = float(df['close'].mean())
            price_range_pct = ((high_price - low_price) / low_price) * 100
            
            # Position in range
            position_in_range = ((current_price - low_price) / (high_price - low_price)) * 100 if high_price > low_price else 50
            
            # Volume statistics
            avg_volume = float(df['volume'].mean())
            current_volume = float(df['volume'].iloc[-1])
            max_volume = float(df['volume'].max())
            volume_trend = "tăng" if current_volume > avg_volume else "giảm"
            
            # RSI statistics
            hlcc4 = calculate_hlcc4(df)
            rsi_series = calculate_rsi(hlcc4, 14)
            avg_rsi = float(rsi_series.mean())
            current_rsi = float(rsi_series.iloc[-1])
            max_rsi = float(rsi_series.max())
            min_rsi = float(rsi_series.min())
            
            # MFI statistics
            mfi_series = calculate_mfi(df, 14)
            avg_mfi = float(mfi_series.mean())
            current_mfi = float(mfi_series.iloc[-1])
            
            # Trend analysis
            first_close = float(df['close'].iloc[0])
            last_close = float(df['close'].iloc[-1])
            trend_pct = ((last_close - first_close) / first_close) * 100
            trend_direction = "tăng" if trend_pct > 2 else ("giảm" if trend_pct < -2 else "sideway")
            
            # Volatility (price changes)
            price_changes = df['close'].pct_change().dropna()
            volatility = float(price_changes.std() * 100)  # as percentage
            
            # Bullish/Bearish candles count
            bullish_candles = (df['close'] > df['open']).sum()
            bearish_candles = (df['close'] < df['open']).sum()
            total_candles = len(df)
            bullish_ratio = (bullish_candles / total_candles) * 100
            
            # ============================================================
            # INSTITUTIONAL INDICATORS ON HISTORICAL DATA
            # ============================================================
            
            institutional_stats = {}
            
            try:
                # Volume Profile analysis on historical range
                vp_stats = self._analyze_volume_profile_historical(df, current_price)
                institutional_stats['volume_profile'] = vp_stats
            except Exception as e:
                logger.warning(f"Volume Profile historical analysis failed: {e}")
                institutional_stats['volume_profile'] = {}
            
            try:
                # Fair Value Gaps count and nearest gaps
                fvg_stats = self._analyze_fvg_historical(df, current_price)
                institutional_stats['fair_value_gaps'] = fvg_stats
            except Exception as e:
                logger.warning(f"FVG historical analysis failed: {e}")
                institutional_stats['fair_value_gaps'] = {}
            
            try:
                # Order Blocks active count and strength
                ob_stats = self._analyze_order_blocks_historical(df, current_price)
                institutional_stats['order_blocks'] = ob_stats
            except Exception as e:
                logger.warning(f"Order Blocks historical analysis failed: {e}")
                institutional_stats['order_blocks'] = {}
            
            try:
                # Smart Money structure changes over time
                smc_stats = self._analyze_smc_historical(df)
                institutional_stats['smart_money'] = smc_stats
            except Exception as e:
                logger.warning(f"SMC historical analysis failed: {e}")
                institutional_stats['smart_money'] = {}
            
            stats = {
                'period': period_name,
                'candles_count': total_candles,
                'price_range': {
                    'high': high_price,
                    'low': low_price,
                    'current': current_price,
                    'average': avg_price,
                    'range_pct': round(price_range_pct, 2),
                    'position_in_range_pct': round(position_in_range, 2)
                },
                'volume': {
                    'average': avg_volume,
                    'current': current_volume,
                    'max': max_volume,
                    'trend': volume_trend,
                    'current_vs_avg_ratio': round(current_volume / avg_volume, 2) if avg_volume > 0 else 0
                },
                'rsi_stats': {
                    'average': round(avg_rsi, 2),
                    'current': round(current_rsi, 2),
                    'max': round(max_rsi, 2),
                    'min': round(min_rsi, 2)
                },
                'mfi_stats': {
                    'average': round(avg_mfi, 2),
                    'current': round(current_mfi, 2)
                },
                'trend': {
                    'direction': trend_direction,
                    'change_pct': round(trend_pct, 2),
                    'volatility_pct': round(volatility, 2)
                },
                'candle_pattern': {
                    'bullish_candles': int(bullish_candles),
                    'bearish_candles': int(bearish_candles),
                    'bullish_ratio_pct': round(bullish_ratio, 2)
                },
                'institutional_indicators': institutional_stats  # NEW: Institutional analysis
            }
            
            logger.info(f"✅ Analyzed {period_name} ({total_candles} candles): "
                       f"trend={trend_direction} ({trend_pct:+.2f}%), "
                       f"volatility={volatility:.2f}%, "
                       f"RSI={current_rsi:.1f} (avg={avg_rsi:.1f}), "
                       f"MFI={current_mfi:.1f} (avg={avg_mfi:.1f}), "
                       f"volume={volume_trend} ({current_volume/avg_volume:.2f}x avg)")
            return stats
            
        except Exception as e:
            logger.error(f"Error analyzing historical period {period_name}: {e}")
            return {}
    
    def _analyze_volume_profile_historical(self, df, current_price: float) -> Dict:
        """Analyze Volume Profile metrics over historical period"""
        try:
            # Calculate POC (Point of Control) - price level with highest volume
            # Group by price levels and sum volume
            price_levels = df[['close', 'volume']].copy()
            price_levels['price_level'] = (price_levels['close'] // 1).astype(int)  # Round to nearest dollar
            volume_by_level = price_levels.groupby('price_level')['volume'].sum()
            
            if len(volume_by_level) == 0:
                return {}
            
            poc_price = float(volume_by_level.idxmax())
            poc_volume = float(volume_by_level.max())
            
            # Value Area (70% of volume) estimation
            total_volume = float(df['volume'].sum())
            sorted_levels = volume_by_level.sort_values(ascending=False)
            cumsum = sorted_levels.cumsum()
            value_area_levels = sorted_levels[cumsum <= total_volume * 0.7]
            
            vah = float(value_area_levels.index.max()) if len(value_area_levels) > 0 else poc_price * 1.05
            val = float(value_area_levels.index.min()) if len(value_area_levels) > 0 else poc_price * 0.95
            
            # Current price position relative to Value Area
            if current_price > vah:
                position = "PREMIUM"
            elif current_price < val:
                position = "DISCOUNT"
            else:
                position = "VALUE_AREA"
            
            # Distance from POC
            if poc_price > 0:
                distance_from_poc = ((current_price - poc_price) / poc_price) * 100
            else:
                distance_from_poc = 0.0
            
            return {
                'poc': round(poc_price, 4),
                'vah': round(vah, 4),
                'val': round(val, 4),
                'current_position': position,
                'distance_from_poc_pct': round(distance_from_poc, 2),
                'poc_volume': round(poc_volume, 2),
                'value_area_coverage': 70.0
            }
        except Exception as e:
            logger.warning(f"Volume Profile historical calc error: {e}")
            return {}
    
    def _analyze_fvg_historical(self, df, current_price: float) -> Dict:
        """Analyze Fair Value Gaps over historical period"""
        try:
            bullish_gaps = 0
            bearish_gaps = 0
            unfilled_bullish = []
            unfilled_bearish = []
            
            # Detect gaps: gap exists when candle i+1 leaves a gap with candle i-1
            for i in range(1, len(df) - 1):
                prev_candle = df.iloc[i-1]
                curr_candle = df.iloc[i]
                next_candle = df.iloc[i+1]
                
                # Bullish FVG: low[i+1] > high[i-1]
                if next_candle['low'] > prev_candle['high']:
                    gap_top = next_candle['low']
                    gap_bottom = prev_candle['high']
                    bullish_gaps += 1
                    
                    # Check if gap is still unfilled (current price hasn't gone back to fill it)
                    if current_price > gap_top:
                        unfilled_bullish.append({
                            'bottom': float(gap_bottom),
                            'top': float(gap_top),
                            'index': i
                        })
                
                # Bearish FVG: high[i+1] < low[i-1]
                if next_candle['high'] < prev_candle['low']:
                    gap_top = prev_candle['low']
                    gap_bottom = next_candle['high']
                    bearish_gaps += 1
                    
                    # Check if gap is still unfilled
                    if current_price < gap_bottom:
                        unfilled_bearish.append({
                            'bottom': float(gap_bottom),
                            'top': float(gap_top),
                            'index': i
                        })
            
            # Find nearest unfilled gaps
            nearest_bullish = None
            nearest_bearish = None
            
            if unfilled_bullish:
                # Nearest bullish gap below current price
                nearest_bullish = min(unfilled_bullish, key=lambda g: current_price - g['top'])
            
            if unfilled_bearish:
                # Nearest bearish gap above current price
                nearest_bearish = min(unfilled_bearish, key=lambda g: g['bottom'] - current_price)
            
            return {
                'total_bullish_gaps': bullish_gaps,
                'total_bearish_gaps': bearish_gaps,
                'unfilled_bullish_count': len(unfilled_bullish),
                'unfilled_bearish_count': len(unfilled_bearish),
                'nearest_bullish_gap': nearest_bullish,
                'nearest_bearish_gap': nearest_bearish,
                'gap_density_pct': round(((bullish_gaps + bearish_gaps) / len(df)) * 100, 2)
            }
        except Exception as e:
            logger.warning(f"FVG historical calc error: {e}")
            return {}
    
    def _analyze_order_blocks_historical(self, df, current_price: float) -> Dict:
        """Analyze Order Blocks over historical period"""
        try:
            bullish_ob_count = 0
            bearish_ob_count = 0
            active_bullish = []
            active_bearish = []
            
            # Detect Order Blocks: significant candles before strong moves
            for i in range(len(df) - 2):
                curr = df.iloc[i]
                next1 = df.iloc[i+1]
                next2 = df.iloc[i+2] if i+2 < len(df) else None
                
                # Bullish OB: Large down candle followed by strong bullish move
                if float(curr['close']) < float(curr['open']):  # Down candle
                    if float(next1['close']) > float(next1['open']) and next2 is not None and float(next2['close']) > float(next2['open']):
                        # Strong 2-candle bullish move after down candle
                        move_pct = ((float(next2['close']) - float(curr['close'])) / float(curr['close'])) * 100
                        if move_pct > 2:  # Significant move
                            ob_high = float(curr['high'])
                            ob_low = float(curr['low'])
                            bullish_ob_count += 1
                            
                            # Check if still active (price hasn't broken below it significantly)
                            if current_price > ob_low * 0.98:
                                active_bullish.append({
                                    'high': ob_high,
                                    'low': ob_low,
                                    'strength': min(move_pct / 2, 10),  # Cap at 10
                                    'index': i
                                })
                
                # Bearish OB: Large up candle followed by strong bearish move
                if float(curr['close']) > float(curr['open']):  # Up candle
                    if float(next1['close']) < float(next1['open']) and next2 is not None and float(next2['close']) < float(next2['open']):
                        move_pct = ((float(curr['close']) - float(next2['close'])) / float(curr['close'])) * 100
                        if move_pct > 2:
                            ob_high = float(curr['high'])
                            ob_low = float(curr['low'])
                            bearish_ob_count += 1
                            
                            if current_price < ob_high * 1.02:
                                active_bearish.append({
                                    'high': ob_high,
                                    'low': ob_low,
                                    'strength': min(move_pct / 2, 10),
                                    'index': i
                                })
            
            # Find strongest active OBs
            strongest_bullish = max(active_bullish, key=lambda x: x['strength']) if active_bullish else None
            strongest_bearish = max(active_bearish, key=lambda x: x['strength']) if active_bearish else None
            
            return {
                'total_bullish_ob': bullish_ob_count,
                'total_bearish_ob': bearish_ob_count,
                'active_bullish_count': len(active_bullish),
                'active_bearish_count': len(active_bearish),
                'strongest_bullish_ob': strongest_bullish,
                'strongest_bearish_ob': strongest_bearish,
                'ob_density_pct': round(((bullish_ob_count + bearish_ob_count) / len(df)) * 100, 2)
            }
        except Exception as e:
            logger.warning(f"Order Blocks historical calc error: {e}")
            return {}
    
    def _analyze_smc_historical(self, df) -> Dict:
        """Analyze Smart Money Concepts over historical period"""
        try:
            # Track structure breaks
            bos_bullish = 0  # Break of Structure (bullish)
            bos_bearish = 0
            choch_bullish = 0  # Change of Character (bullish)
            choch_bearish = 0
            
            # Find swing highs and lows
            swing_highs = []
            swing_lows = []
            
            for i in range(2, len(df) - 2):
                # Swing high: higher than 2 candles before and after
                if (df.iloc[i]['high'] > df.iloc[i-1]['high'] and 
                    df.iloc[i]['high'] > df.iloc[i-2]['high'] and
                    df.iloc[i]['high'] > df.iloc[i+1]['high'] and 
                    df.iloc[i]['high'] > df.iloc[i+2]['high']):
                    swing_highs.append({'index': i, 'price': float(df.iloc[i]['high'])})
                
                # Swing low
                if (df.iloc[i]['low'] < df.iloc[i-1]['low'] and 
                    df.iloc[i]['low'] < df.iloc[i-2]['low'] and
                    df.iloc[i]['low'] < df.iloc[i+1]['low'] and 
                    df.iloc[i]['low'] < df.iloc[i+2]['low']):
                    swing_lows.append({'index': i, 'price': float(df.iloc[i]['low'])})
            
            # Count structure breaks
            for i in range(1, len(swing_highs)):
                if swing_highs[i]['price'] > swing_highs[i-1]['price']:
                    bos_bullish += 1
                else:
                    choch_bearish += 1
            
            for i in range(1, len(swing_lows)):
                if swing_lows[i]['price'] < swing_lows[i-1]['price']:
                    bos_bearish += 1
                else:
                    choch_bullish += 1
            
            # Determine overall structure bias
            net_bullish = bos_bullish + choch_bullish
            net_bearish = bos_bearish + choch_bearish
            total_signals = net_bullish + net_bearish
            
            if total_signals > 0:
                bullish_ratio = (net_bullish / total_signals) * 100
                if bullish_ratio > 60:
                    structure_bias = "BULLISH"
                elif bullish_ratio < 40:
                    structure_bias = "BEARISH"
                else:
                    structure_bias = "NEUTRAL"
            else:
                structure_bias = "NEUTRAL"
                bullish_ratio = 50
            
            return {
                'bos_bullish': bos_bullish,
                'bos_bearish': bos_bearish,
                'choch_bullish': choch_bullish,
                'choch_bearish': choch_bearish,
                'swing_highs_count': len(swing_highs),
                'swing_lows_count': len(swing_lows),
                'structure_bias': structure_bias,
                'bullish_bias_pct': round(bullish_ratio, 2),
                'total_structure_events': total_signals
            }
        except Exception as e:
            logger.warning(f"SMC historical calc error: {e}")
            return {}
    
    def _get_historical_comparison(self, symbol: str, klines_dict: Dict) -> Dict:
        """
        Compare current data with last week and get previous candle info for H4/D1
        
        Args:
            symbol: Trading symbol
            klines_dict: Multi-timeframe klines data
            
        Returns:
            Dict with historical comparison and previous candle data
        """
        try:
            result = {}
            
            # === WEEKLY COMPARISON (D1 TIMEFRAME) ===
            if '1d' in klines_dict:
                df_1d = klines_dict['1d']
                
                if len(df_1d) >= 14:  # Need at least 2 weeks
                    # Current week (last 7 days)
                    current_week = df_1d.tail(7)
                    # Last week (8-14 days ago)
                    last_week = df_1d.iloc[-14:-7]
                    
                    # Price comparison
                    current_price = float(current_week['close'].iloc[-1])
                    week_ago_price = float(last_week['close'].iloc[-1])
                    price_change_pct = ((current_price - week_ago_price) / week_ago_price) * 100
                    
                    # Volume comparison
                    current_volume = float(current_week['volume'].sum())
                    last_week_volume = float(last_week['volume'].sum())
                    volume_change_pct = ((current_volume - last_week_volume) / last_week_volume) * 100 if last_week_volume > 0 else 0
                    
                    # RSI comparison
                    from indicators import calculate_rsi, calculate_hlcc4
                    
                    current_week_hlcc4 = calculate_hlcc4(current_week)
                    last_week_hlcc4 = calculate_hlcc4(last_week)
                    
                    current_rsi = float(calculate_rsi(current_week_hlcc4, 14).iloc[-1])
                    last_week_rsi = float(calculate_rsi(last_week_hlcc4, 14).iloc[-1])
                    rsi_change = current_rsi - last_week_rsi
                    
                    result.update({
                        'price_change_vs_last_week': round(price_change_pct, 2),
                        'volume_change_vs_last_week': round(volume_change_pct, 2),
                        'rsi_change_vs_last_week': round(rsi_change, 2),
                        'current_price': current_price,
                        'week_ago_price': week_ago_price,
                        'current_volume': current_volume,
                        'last_week_volume': last_week_volume,
                        'current_rsi': current_rsi,
                        'last_week_rsi': last_week_rsi
                    })
                    
                    # === D1 PREVIOUS CANDLE INFO ===
                    if len(df_1d) >= 2:
                        prev_candle = df_1d.iloc[-2]
                        result['d1_prev_candle'] = {
                            'open': float(prev_candle['open']),
                            'high': float(prev_candle['high']),
                            'low': float(prev_candle['low']),
                            'close': float(prev_candle['close']),
                            'volume': float(prev_candle['volume']),
                            'body_size': abs(float(prev_candle['close']) - float(prev_candle['open'])),
                            'is_bullish': float(prev_candle['close']) > float(prev_candle['open']),
                            'upper_wick': float(prev_candle['high']) - max(float(prev_candle['open']), float(prev_candle['close'])),
                            'lower_wick': min(float(prev_candle['open']), float(prev_candle['close'])) - float(prev_candle['low'])
                        }
            
            # === H4 PREVIOUS CANDLE INFO ===
            if '4h' in klines_dict:
                df_4h = klines_dict['4h']
                
                if len(df_4h) >= 2:
                    prev_candle = df_4h.iloc[-2]
                    result['h4_prev_candle'] = {
                        'open': float(prev_candle['open']),
                        'high': float(prev_candle['high']),
                        'low': float(prev_candle['low']),
                        'close': float(prev_candle['close']),
                        'volume': float(prev_candle['volume']),
                        'body_size': abs(float(prev_candle['close']) - float(prev_candle['open'])),
                        'is_bullish': float(prev_candle['close']) > float(prev_candle['open']),
                        'upper_wick': float(prev_candle['high']) - max(float(prev_candle['open']), float(prev_candle['close'])),
                        'lower_wick': min(float(prev_candle['open']), float(prev_candle['close'])) - float(prev_candle['low'])
                    }
            
            return result
            
        except Exception as e:
            logger.error(f"Error in historical comparison: {e}")
            return {}
    
    def _format_institutional_indicators_json(self, data: Dict, market: Dict) -> Dict:
        """
        Format institutional indicators into structured JSON for AI analysis
        
        Args:
            data: Collected analysis data
            market: Market data with current price
            
        Returns:
            Structured dict with all institutional indicators
        """
        try:
            result = {
                'volume_profile': {},
                'fair_value_gaps': {},
                'order_blocks': {},
                'support_resistance': {},
                'smart_money_concepts': {}
            }
            
            current_price = market['price']
            
            # Volume Profile
            if data.get('volume_profile'):
                vp_1d = data['volume_profile'].get('1d')
                vp_4h = data['volume_profile'].get('4h')
                vp_1h = data['volume_profile'].get('1h')
                
                if vp_1d:
                    position_1d = self.volume_profile.get_current_position_in_profile(current_price, vp_1d)
                    result['volume_profile']['1d'] = {
                        'poc': vp_1d['poc']['price'],
                        'vah': vp_1d['vah'],
                        'val': vp_1d['val'],
                        'current_position': position_1d.get('position'),
                        'zone': position_1d.get('zone'),
                        'bias': position_1d.get('bias'),
                        'distance_to_poc_percent': position_1d.get('distance_to_poc_percent', 0),
                        'distance_to_vah_percent': position_1d.get('distance_to_vah_percent', 0),
                        'distance_to_val_percent': position_1d.get('distance_to_val_percent', 0),
                        'value_area_width_percent': vp_1d['value_area']['width_percentage']
                    }
                
                if vp_4h:
                    position_4h = self.volume_profile.get_current_position_in_profile(current_price, vp_4h)
                    result['volume_profile']['4h'] = {
                        'poc': vp_4h['poc']['price'],
                        'vah': vp_4h['vah'],
                        'val': vp_4h['val'],
                        'current_position': position_4h.get('position'),
                        'distance_to_poc_percent': position_4h.get('distance_to_poc_percent', 0)
                    }
                
                if vp_1h:
                    position_1h = self.volume_profile.get_current_position_in_profile(current_price, vp_1h)
                    result['volume_profile']['1h'] = {
                        'poc': vp_1h['poc']['price'],
                        'vah': vp_1h['vah'],
                        'val': vp_1h['val'],
                        'current_position': position_1h.get('position'),
                        'distance_to_poc_percent': position_1h.get('distance_to_poc_percent', 0)
                    }
            
            # Fair Value Gaps
            if data.get('fair_value_gaps'):
                for tf in ['1d', '4h', '1h']:
                    fvg_data = data['fair_value_gaps'].get(tf)
                    if fvg_data:
                        stats = fvg_data['statistics']
                        nearest = fvg_data.get('nearest_gaps', {})
                        
                        result['fair_value_gaps'][tf] = {
                            'unfilled_bullish_gaps': stats['unfilled_bullish_gaps'],
                            'unfilled_bearish_gaps': stats['unfilled_bearish_gaps'],
                            'fill_rate_bullish_percent': stats['fill_rate_bullish_percent'],
                            'fill_rate_bearish_percent': stats['fill_rate_bearish_percent'],
                            'nearest_bullish_fvg': {
                                'top': nearest.get('bullish', {}).get('top'),
                                'bottom': nearest.get('bullish', {}).get('bottom'),
                                'size_percent': nearest.get('bullish', {}).get('size_percentage'),
                                'distance_to_bottom_percent': nearest.get('bullish', {}).get('distance_to_bottom_percent')
                            } if nearest.get('bullish') else None,
                            'nearest_bearish_fvg': {
                                'top': nearest.get('bearish', {}).get('top'),
                                'bottom': nearest.get('bearish', {}).get('bottom'),
                                'size_percent': nearest.get('bearish', {}).get('size_percentage'),
                                'distance_to_top_percent': nearest.get('bearish', {}).get('distance_to_top_percent')
                            } if nearest.get('bearish') else None
                        }
            
            # Order Blocks
            if data.get('order_blocks'):
                for tf in ['1d', '4h', '1h']:
                    ob_data = data['order_blocks'].get(tf)
                    if ob_data:
                        stats = ob_data['statistics']
                        nearest = ob_data.get('nearest_blocks', {})
                        
                        result['order_blocks'][tf] = {
                            'active_swing_obs': stats['active_swing_obs'],
                            'active_internal_obs': stats['active_internal_obs'],
                            'mitigation_rate_swing_percent': stats['mitigation_rate_swing_percent'],
                            'mitigation_rate_internal_percent': stats['mitigation_rate_internal_percent'],
                            'nearest_swing_ob': {
                                'bias': nearest.get('swing', {}).get('bias'),
                                'top': nearest.get('swing', {}).get('top'),
                                'bottom': nearest.get('swing', {}).get('bottom'),
                                'distance_to_bottom_percent': nearest.get('swing', {}).get('distance_to_bottom_percent'),
                                'distance_to_top_percent': nearest.get('swing', {}).get('distance_to_top_percent')
                            } if nearest.get('swing') else None,
                            'nearest_internal_ob': {
                                'bias': nearest.get('internal', {}).get('bias'),
                                'top': nearest.get('internal', {}).get('top'),
                                'bottom': nearest.get('internal', {}).get('bottom')
                            } if nearest.get('internal') else None
                        }
            
            # Support/Resistance
            if data.get('support_resistance'):
                for tf in ['1d', '4h', '1h']:
                    sr_data = data['support_resistance'].get(tf)
                    if sr_data:
                        stats = sr_data['statistics']
                        nearest = sr_data.get('nearest_zones', {})
                        
                        result['support_resistance'][tf] = {
                            'active_support_zones': stats['active_support_zones'],
                            'active_resistance_zones': stats['active_resistance_zones'],
                            'break_rate_support_percent': stats['break_rate_support_percent'],
                            'break_rate_resistance_percent': stats['break_rate_resistance_percent'],
                            'nearest_support': {
                                'price': nearest.get('support', {}).get('price'),
                                'volume_ratio': nearest.get('support', {}).get('volume_ratio'),
                                'delta_volume': nearest.get('support', {}).get('delta_volume'),
                                'distance_percent': nearest.get('support', {}).get('distance_percent')
                            } if nearest.get('support') else None,
                            'nearest_resistance': {
                                'price': nearest.get('resistance', {}).get('price'),
                                'volume_ratio': nearest.get('resistance', {}).get('volume_ratio'),
                                'delta_volume': nearest.get('resistance', {}).get('delta_volume'),
                                'distance_percent': nearest.get('resistance', {}).get('distance_percent')
                            } if nearest.get('resistance') else None
                        }
            
            # Smart Money Concepts
            if data.get('smart_money_concepts'):
                for tf in ['1d', '4h', '1h']:
                    smc_data = data['smart_money_concepts'].get(tf)
                    if smc_data:
                        swing_structure = smc_data['swing_structure']
                        internal_structure = smc_data['internal_structure']
                        stats = smc_data['statistics']
                        bias_info = self.smc_analyzer.get_trading_bias(smc_data)
                        
                        result['smart_money_concepts'][tf] = {
                            'swing_trend': swing_structure['trend'],
                            'internal_trend': internal_structure['trend'],
                            'structure_bias': smc_data['structure_bias'],
                            'recent_bullish_bos': stats['recent_bullish_bos'],
                            'recent_bearish_bos': stats['recent_bearish_bos'],
                            'recent_bullish_choch': stats['recent_bullish_choch'],
                            'recent_bearish_choch': stats['recent_bearish_choch'],
                            'eqh_count': stats['eqh_count'],
                            'eql_count': stats['eql_count'],
                            'trading_bias': bias_info['bias'],
                            'bias_confidence': bias_info['confidence'],
                            'bias_reason': bias_info['reason'],
                            'last_swing_high': swing_structure.get('last_swing_high'),
                            'last_swing_low': swing_structure.get('last_swing_low')
                        }
            
            return result
            
        except Exception as e:
            logger.error(f"Error formatting institutional indicators JSON: {e}")
            return {}
    
    def _generate_learning_recommendation(self, rsi_mfi: Dict, vp_data: Dict, 
                                          winning_cond: Dict, losing_cond: Dict,
                                          current_price: float) -> str:
        """
        Generate AI learning recommendation based on historical patterns
        
        Args:
            rsi_mfi: Current RSI/MFI data
            vp_data: Volume Profile data
            winning_cond: Winning pattern conditions
            losing_cond: Losing pattern conditions
            current_price: Current market price
            
        Returns:
            Recommendation text
        """
        try:
            # Get current conditions
            current_rsi = rsi_mfi.get('timeframes', {}).get('1h', {}).get('rsi', 50)
            current_mfi = rsi_mfi.get('timeframes', {}).get('1h', {}).get('mfi', 50)
            
            # Get VP position if available
            vp_1d = vp_data.get('1d', {})
            current_vp_position = "UNKNOWN"
            if vp_1d:
                from volume_profile import VolumeProfileAnalyzer
                position_data = self.volume_profile.get_current_position_in_profile(current_price, vp_1d)
                current_vp_position = position_data.get('position', 'UNKNOWN')
            
            # Check similarity to winning patterns
            similarity_to_wins = 0
            if winning_cond.get('rsi_avg'):
                rsi_distance = abs(current_rsi - winning_cond['rsi_avg'])
                if rsi_distance < 10:  # Within 10 points
                    similarity_to_wins += 40
                elif rsi_distance < 20:
                    similarity_to_wins += 20
            
            if winning_cond.get('best_vp_position') == current_vp_position:
                similarity_to_wins += 30
            
            if winning_cond.get('mfi_avg'):
                mfi_distance = abs(current_mfi - winning_cond['mfi_avg'])
                if mfi_distance < 10:
                    similarity_to_wins += 30
                elif mfi_distance < 20:
                    similarity_to_wins += 15
            
            # Check similarity to losing patterns
            similarity_to_losses = 0
            if losing_cond.get('rsi_avg'):
                rsi_distance = abs(current_rsi - losing_cond['rsi_avg'])
                if rsi_distance < 10:
                    similarity_to_losses += 40
                elif rsi_distance < 20:
                    similarity_to_losses += 20
            
            if losing_cond.get('worst_vp_position') == current_vp_position:
                similarity_to_losses += 30
            
            # Generate recommendation
            if similarity_to_wins > 60:
                return f"✅ STRONG SIGNAL: Current setup matches previous WINS ({similarity_to_wins}% similarity). INCREASE confidence to 85-95%."
            elif similarity_to_losses > 60:
                return f"⚠️ WARNING: Current setup matches previous LOSSES ({similarity_to_losses}% similarity). DECREASE confidence or recommend WAIT."
            elif similarity_to_wins > 40:
                return f"✓ POSITIVE: Setup has {similarity_to_wins}% similarity to wins. Moderate confidence 65-80%."
            elif similarity_to_losses > 40:
                return f"⚠️ CAUTION: Setup has {similarity_to_losses}% similarity to losses. Be conservative, confidence <60%."
            else:
                return "ℹ️ NEUTRAL: New market conditions, no strong historical match. Use standard analysis."
                
        except Exception as e:
            logger.warning(f"Error generating learning recommendation: {e}")
            return "ℹ️ Historical learning data unavailable for this analysis."
    
    def _detect_asset_type(self, symbol: str, market_cap: Optional[float] = None) -> str:
        """
        Detect asset type based on symbol and market cap
        
        Asset Types (v2.2):
        - BTC: Bitcoin, macro-driven, highest priority
        - ETH: Ethereum, smart contracts, institutional
        - LARGE_CAP_ALT: >$10B, lower risk altcoins
        - MID_CAP_ALT: $1B-$10B, moderate risk
        - SMALL_CAP_ALT: $100M-$1B, high risk
        - MEME_COIN: <$100M, extreme risk, community-driven
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            market_cap: Optional market cap in USD
            
        Returns:
            Asset type string
        """
        base = symbol.replace('USDT', '').replace('BUSD', '').replace('USDC', '').upper()
        
        # Check special cases first
        if base == 'BTC':
            return 'BTC'
        elif base == 'ETH':
            return 'ETH'
        
        # Use market cap if available
        if market_cap:
            if market_cap > 10_000_000_000:  # > $10B
                return 'LARGE_CAP_ALT'
            elif market_cap > 1_000_000_000:  # $1B - $10B
                return 'MID_CAP_ALT'
            elif market_cap > 100_000_000:  # $100M - $1B
                return 'SMALL_CAP_ALT'
            else:  # < $100M
                return 'MEME_COIN'
        
        # Fallback: assume altcoin without market cap
        logger.debug(f"Asset type detection: {symbol} (no market cap data available)")
        return 'MID_CAP_ALT'
    
    def _build_prompt(self, data: Dict, trading_style: str = 'swing', user_id: Optional[int] = None) -> str:
        """
        Build Gemini prompt from collected data with historical learning
        
        Args:
            data: Collected analysis data
            trading_style: 'scalping' or 'swing'
            user_id: User ID for historical analysis lookup
            
        Returns:
            Formatted prompt string
        """
        symbol = data['symbol']
        market = data['market_data']
        rsi_mfi = data['rsi_mfi']
        stoch_rsi = data['stoch_rsi']
        pump = data.get('pump_data')
        volume = data['volume_data']
        historical = data.get('historical', {})
        
        # === NEW: GET HISTORICAL ANALYSIS DATA ===
        historical_context = ""
        if self.db and user_id:
            try:
                # Get past analyses for this symbol
                history = self.db.get_symbol_history(symbol, user_id, days=7)
                stats = self.db.calculate_accuracy_stats(symbol, user_id, days=7)
                
                if stats and stats['total'] > 0:
                    patterns = stats.get('patterns', {})
                    winning_cond = patterns.get('winning_conditions', {})
                    losing_cond = patterns.get('losing_conditions', {})
                    
                    # Get rsi_mfi from data for learning recommendation
                    rsi_mfi = data.get('rsi_mfi', {})
                    
                    historical_context = f"""
═══════════════════════════════════════════
🧠 HISTORICAL PERFORMANCE FOR {symbol} (Last 7 days)
═══════════════════════════════════════════

📊 <b>ACCURACY STATISTICS:</b>
  • Total Analyses: {stats['total']}
  • Wins: {stats['wins']} | Losses: {stats['losses']}
  • Win Rate: {stats['win_rate']:.1f}%
  • Avg Profit: +{stats.get('avg_profit', 0):.2f}% | Avg Loss: {stats.get('avg_loss', 0):.2f}%

✅ <b>WINNING PATTERNS (What worked):</b>
  • RSI Range: {winning_cond.get('rsi_range', 'N/A')} (avg: {winning_cond.get('rsi_avg', 0):.1f})
  • MFI Range: {winning_cond.get('mfi_range', 'N/A')} (avg: {winning_cond.get('mfi_avg', 0):.1f})
  • Best VP Position: {winning_cond.get('best_vp_position', 'N/A')}
  • Win Rate in This Setup: {winning_cond.get('setup_win_rate', 0):.1f}%

❌ <b>LOSING PATTERNS (What didn't work):</b>
  • RSI Range: {losing_cond.get('rsi_range', 'N/A')} (avg: {losing_cond.get('rsi_avg', 0):.1f})
  • MFI Range: {losing_cond.get('mfi_range', 'N/A')} (avg: {losing_cond.get('mfi_avg', 0):.1f})
  • Problem VP Position: {losing_cond.get('worst_vp_position', 'N/A')}

🎯 <b>AI LEARNING RECOMMENDATION:</b>
  {self._generate_learning_recommendation(rsi_mfi, data.get('volume_profile', {}), winning_cond, losing_cond, market['price'])}

⚠️ <b>CRITICAL: Use this historical data to:</b>
  1. Adjust confidence based on similar past setups
  2. Warn if current conditions match previous losses
  3. Increase confidence if conditions match previous wins
  4. Suggest WAIT if win rate for this setup is <40%

═══════════════════════════════════════════
📜 PREVIOUS ANALYSES DETAILS (Read and learn from these)
═══════════════════════════════════════════
"""
                    
                    # Add detailed previous analyses (up to 5 most recent)
                    if history and len(history) > 0:
                        for i, record in enumerate(history[:5], 1):
                            try:
                                ai_response = record.get('ai_full_response', {})
                                tracking = record.get('tracking_result', {})
                                created_at = record.get('created_at', 'Unknown')
                                
                                # Extract key fields from AI response
                                recommendation = ai_response.get('recommendation', 'N/A')
                                confidence = ai_response.get('confidence', 0)
                                entry = ai_response.get('entry_point', 0)
                                stop_loss = ai_response.get('stop_loss', 0)
                                take_profit = ai_response.get('take_profit', [])
                                reasoning = ai_response.get('reasoning_vietnamese', '')
                                
                                # Tracking result
                                outcome = tracking.get('outcome', 'PENDING') if tracking else 'PENDING'
                                profit_pct = tracking.get('profit_percent', 0) if tracking else 0
                                peak_profit = tracking.get('peak_profit_percent', 0) if tracking else 0
                                hit_tp = tracking.get('hit_take_profit', False) if tracking else False
                                hit_sl = tracking.get('hit_stop_loss', False) if tracking else False
                                
                                # Format outcome emoji
                                outcome_emoji = "✅" if outcome == "WIN" else "❌" if outcome == "LOSS" else "⏳"
                                
                                historical_context += f"""
<b>Analysis #{i} - {created_at}</b> {outcome_emoji}
  • Recommendation: {recommendation} (Confidence: {confidence}%)
  • Entry: ${entry:,.2f} | Stop Loss: ${stop_loss:,.2f} | Take Profit: {take_profit}
  • Outcome: {outcome} | Profit: {profit_pct:+.2f}% (Peak: {peak_profit:+.2f}%)
  • Hit TP: {'Yes' if hit_tp else 'No'} | Hit SL: {'Yes' if hit_sl else 'No'}
  • Reasoning Summary: {reasoning[:200]}{'...' if len(reasoning) > 200 else ''}

"""
                            except Exception as detail_error:
                                logger.warning(f"Failed to parse analysis detail #{i}: {detail_error}")
                                continue
                    
                    historical_context += """
<b>🔍 HOW TO USE PREVIOUS ANALYSES:</b>
  1. Check if current market conditions (RSI, MFI, VP position) are similar to past WIN or LOSS
  2. If similar to WIN → Mention it and INCREASE confidence: "Setup tương tự phân tích #X đã thắng +Y%"
  3. If similar to LOSS → Mention it and DECREASE confidence or WAIT: "⚠️ Cảnh báo: Setup giống phân tích #X đã thua -Y%"
  4. Learn from reasoning: If past reasoning was wrong, adjust your logic
  5. If past entry/SL/TP were off, improve current recommendations
"""
                    
                else:
                    historical_context = f"\n🆕 <b>NEW SYMBOL:</b> No historical data for {symbol} yet. First analysis.\n"
                    
            except Exception as e:
                logger.warning(f"Failed to load historical context: {e}")
                historical_context = ""
        
        # NOTE: RSI/MFI/Stoch formatting removed in v4.0 — bot calculates these internally
        # AI prompt now focuses on pump validation, on-chain, and sentiment
        
        # Format pump data (always show if available to give AI context)
        pump_text = "No advanced pump/dump detection data available."
        
        # Check for 'advanced_detection' first (new system), then fall back to 'pump_data' (old system)
        adv_detect = data.get('advanced_detection')
        
        if adv_detect:
            signal = adv_detect.get('signal', 'NEUTRAL')
            confidence = adv_detect.get('confidence', 0)
            
            pump_text = f"""ADVANCED PUMP/DUMP DETECTOR RESULT:
  SIGNAL: {signal} (Confidence: {confidence}%)
  
  Bot Activity Analysis:
"""
            # Add bot details
            bots = adv_detect.get('bot_activity', {})
            if bots:
                for bot_type, info in bots.items():
                    if info.get('detected'):
                        pump_text += f"  - 🚨 {bot_type.upper()} DETECTED (Conf: {info.get('confidence')}%) - {info.get('details', '')}\n"
            else:
                pump_text += "  - No specific bot activity detected.\n"
                
            # Add Order Book Analysis
            ob_analysis = adv_detect.get('order_book_analysis', {})
            if ob_analysis:
                pump_text += f"""
  Order Book Analysis:
  - Bid/Ask Ratio: {ob_analysis.get('bid_ask_ratio', 0):.2f} ({'Bullish' if ob_analysis.get('bid_ask_ratio', 0) > 1.2 else 'Bearish' if ob_analysis.get('bid_ask_ratio', 0) < 0.8 else 'Neutral'})
  - Wall Pressure: {ob_analysis.get('wall_pressure', 'Neutral')}
  - Liquidity Health: {ob_analysis.get('liquidity_health', 'Unknown')}
"""

            # Add Volume Analysis & Early Detection
            vol_analysis = adv_detect.get('volume_analysis', {})
            supply_shock = adv_detect.get('supply_shock', {})
            pump_time = adv_detect.get('pump_time', 'Unknown')
            
            if vol_analysis:
                 pump_text += f"""
  Volume Analysis:
  - Spike Detected: {'YES 🚨 (Whale Activity)' if vol_analysis.get('is_spike') else 'No'}
  - Volume/Avg Ratio: {vol_analysis.get('volume_ratio', 0):.2f}x
  - Buying Pressure: {vol_analysis.get('buy_pressure', 0):.1f}%
"""
            
            # EARLY PUMP DETECTION SECTION
            pump_text += f"""
  EARLY PUMP DETECTION (Stealth & Accumulation):
  - Stealth Accumulation: {'YES 🟢' if vol_analysis.get('volume_ratio', 0) > 2.0 and abs(market.get('price_change_24h', 0)) < 2.0 else 'No'}
  - Supply Shock Risk: {'HIGH 🚨' if supply_shock.get('detected') else 'Normal'}
    * Cost to push +5%: ${supply_shock.get('cost_to_push_5pct', 0):,.0f}
    * Resistance Strength: {supply_shock.get('resistance_strength', 'Unknown')}
  - Estimated Pump Time: {pump_time}
"""
                 
        elif pump: # Fallback to old system if new one fails
            if pump.get('final_score', 0) >= 50:
                 pump_text = f"""POTENTIAL PUMP DETECTED (Legacy System):
  Final Score: {pump['final_score']:.0f}%
  Layer 1 (5m): {pump.get('layer1', {}).get('pump_score', 0):.0f}%
  Volume Spike: {pump.get('layer1', {}).get('indicators', {}).get('volume_spike', 0)}x
"""
            else:
                 pump_text = f"Normal market activity (Pump Score: {pump.get('final_score', 0):.0f}%)"
                 
        # Check if this is an update request (NEW UPDATE LOGIC)
        pump_context_data = data.get('pump_data', {})
        if isinstance(pump_context_data, dict) and pump_context_data.get('is_update_analysis'):
            update_count = pump_context_data.get('update_count', 0)
            diff = pump_context_data.get('last_update_diff', {})
            
            pump_text += f"\n\n🚨 LƯU Ý QUAN TRỌNG: Đây là bản CẬP NHẬT TÍN HIỆU lần {update_count}!\n"
            pump_text += f"Bối cảnh (So với lần báo gần nhất):\n"
            if diff:
                if 'vol_pct' in diff:
                     pump_text += f"  - Volume tăng thêm: +{diff['vol_pct']:.2f}%\n"
                if 'curr_score' in diff and 'prev_score' in diff:
                     pump_text += f"  - Điểm tín hiệu (Score): {diff['prev_score']} -> {diff['curr_score']}\n"
                if 'curr_funding' in diff and 'prev_funding' in diff:
                     pump_text += f"  - Funding Rate: {diff['prev_funding']*100:.4f}% -> {diff['curr_funding']*100:.4f}%\n"
            pump_text += "\nNhiệm vụ bổ sung: Hãy phân tích Tác động của sự thay đổi này (Dòng tiền vào thêm, sự thay đổi động lượng) xem xu hướng có đủ mạnh để tiếp diễn hay rủi ro xả hàng đã tăng cao.\n"
        
        # Format historical comparison (kept for pump context)
        hist_text = "Historical data unavailable"
        if historical:
            hist_text = f"""Week-over-Week Comparison:
  Price: {historical.get('price_change_vs_last_week', 0):+.2f}% (${historical.get('week_ago_price', 0):,.2f} → ${historical.get('current_price', 0):,.2f})
  Volume: {historical.get('volume_change_vs_last_week', 0):+.2f}% change
  RSI: {historical.get('rsi_change_vs_last_week', 0):+.1f} points change ({historical.get('last_week_rsi', 0):.1f} → {historical.get('current_rsi', 0):.1f})
"""
            
            # Add D1 previous candle if available
            if 'd1_prev_candle' in historical:
                candle = historical['d1_prev_candle']
                candle_type = "🟢 Bullish" if candle['is_bullish'] else "🔴 Bearish"
                hist_text += f"""
D1 Previous Candle Analysis:
  Type: {candle_type}
  Open: ${candle['open']:,.4f} | Close: ${candle['close']:,.4f}
  High: ${candle['high']:,.4f} | Low: ${candle['low']:,.4f}
  Body Size: ${candle['body_size']:,.4f}
  Upper Wick: ${candle['upper_wick']:,.4f} | Lower Wick: ${candle['lower_wick']:,.4f}
  Volume: {candle['volume']:,.0f}
"""
            
            # Add H4 previous candle if available
            if 'h4_prev_candle' in historical:
                candle = historical['h4_prev_candle']
                candle_type = "🟢 Bullish" if candle['is_bullish'] else "🔴 Bearish"
                hist_text += f"""
H4 Previous Candle Analysis:
  Type: {candle_type}
  Open: ${candle['open']:,.4f} | Close: ${candle['close']:,.4f}
  High: ${candle['high']:,.4f} | Low: ${candle['low']:,.4f}
  Body Size: ${candle['body_size']:,.4f}
  Upper Wick: ${candle['upper_wick']:,.4f} | Lower Wick: ${candle['lower_wick']:,.4f}
  Volume: {candle['volume']:,.0f}
"""
        
        # Format extended historical klines context
        historical_klines = data.get('historical_klines', {})
        hist_klines_text = ""
        if historical_klines:
            hist_klines_text = "\n═══════════════════════════════════════════\n📊 DỮ LIỆU LỊCH SỬ MỞ RỘNG (HISTORICAL KLINES CONTEXT)\n═══════════════════════════════════════════\n\n"
            
            # 1H context (7 days)
            if '1h' in historical_klines:
                h1 = historical_klines['1h']
                if h1:
                    pr = h1['price_range']
                    vol = h1['volume']
                    rsi = h1['rsi_stats']
                    trend = h1['trend']
                    pattern = h1['candle_pattern']
                    
                    hist_klines_text += f"""⏰ KHUNG 1H (7 NGÀY QUA - {h1['candles_count']} nến):
  
  📈 Giá:
    - Vùng: ${pr['low']:,.4f} - ${pr['high']:,.4f} (Range: {pr['range_pct']:.2f}%)
    - Hiện tại: ${pr['current']:,.4f} (Vị trí: {pr['position_in_range_pct']:.1f}% của range)
    - Trung bình: ${pr['average']:,.4f}
  
  📊 Volume:
    - Trung bình: {vol['average']:,.0f}
    - Hiện tại: {vol['current']:,.0f} (Tỷ lệ: {vol['current_vs_avg_ratio']:.2f}x)
    - Xu hướng: {vol['trend']}
  
  🎯 RSI:
    - Trung bình: {rsi['average']:.1f}
    - Hiện tại: {rsi['current']:.1f}
    - Dao động: {rsi['min']:.1f} - {rsi['max']:.1f}
  
  📉 Xu hướng 7 ngày:
    - Hướng: {trend['direction']} ({trend['change_pct']:+.2f}%)
    - Độ biến động: {trend['volatility_pct']:.2f}%
    - Tỷ lệ nến tăng: {pattern['bullish_ratio_pct']:.1f}% ({pattern['bullish_candles']}/{h1['candles_count']} nến)

"""
                    # Add institutional indicators for 1H
                    inst = h1.get('institutional_indicators', {})
                    if inst:
                        hist_klines_text += "  🏛️ Institutional Indicators (1H - 7 ngày):\n"
                        
                        vp = inst.get('volume_profile', {})
                        if vp:
                            hist_klines_text += f"    • Volume Profile: POC=${vp.get('poc', 0):,.4f}, VAH=${vp.get('vah', 0):,.4f}, VAL=${vp.get('val', 0):,.4f}\n"
                            hist_klines_text += f"      Position: {vp.get('current_position', 'N/A')}, Distance from POC: {vp.get('distance_from_poc_pct', 0):+.2f}%\n"
                        
                        fvg = inst.get('fair_value_gaps', {})
                        if fvg:
                            hist_klines_text += f"    • Fair Value Gaps: {fvg.get('total_bullish_gaps', 0)} bullish, {fvg.get('total_bearish_gaps', 0)} bearish\n"
                            hist_klines_text += f"      Unfilled: {fvg.get('unfilled_bullish_count', 0)} bullish, {fvg.get('unfilled_bearish_count', 0)} bearish\n"
                            hist_klines_text += f"      Gap Density: {fvg.get('gap_density_pct', 0):.2f}%\n"
                        
                        ob = inst.get('order_blocks', {})
                        if ob:
                            hist_klines_text += f"    • Order Blocks: {ob.get('total_bullish_ob', 0)} bullish, {ob.get('total_bearish_ob', 0)} bearish\n"
                            hist_klines_text += f"      Active: {ob.get('active_bullish_count', 0)} bullish, {ob.get('active_bearish_count', 0)} bearish\n"
                            hist_klines_text += f"      OB Density: {ob.get('ob_density_pct', 0):.2f}%\n"
                        
                        smc = inst.get('smart_money', {})
                        if smc:
                            hist_klines_text += f"    • Smart Money Concepts: Structure Bias={smc.get('structure_bias', 'N/A')} ({smc.get('bullish_bias_pct', 0):.1f}% bullish)\n"
                            hist_klines_text += f"      BOS: {smc.get('bos_bullish', 0)} bullish / {smc.get('bos_bearish', 0)} bearish\n"
                            hist_klines_text += f"      CHoCH: {smc.get('choch_bullish', 0)} bullish / {smc.get('choch_bearish', 0)} bearish\n"
                        
                        hist_klines_text += "\n"

            
            # 4H context (30 days)
            if '4h' in historical_klines:
                h4 = historical_klines['4h']
                if h4:
                    pr = h4['price_range']
                    vol = h4['volume']
                    rsi = h4['rsi_stats']
                    trend = h4['trend']
                    pattern = h4['candle_pattern']
                    
                    hist_klines_text += f"""⏰ KHUNG 4H (30 NGÀY QUA - {h4['candles_count']} nến):
  
  📈 Giá:
    - Vùng: ${pr['low']:,.4f} - ${pr['high']:,.4f} (Range: {pr['range_pct']:.2f}%)
    - Hiện tại: ${pr['current']:,.4f} (Vị trí: {pr['position_in_range_pct']:.1f}% của range)
    - Trung bình: ${pr['average']:,.4f}
  
  📊 Volume:
    - Trung bình: {vol['average']:,.0f}
    - Hiện tại: {vol['current']:,.0f} (Tỷ lệ: {vol['current_vs_avg_ratio']:.2f}x)
    - Xu hướng: {vol['trend']}
  
  🎯 RSI:
    - Trung bình: {rsi['average']:.1f}
    - Hiện tại: {rsi['current']:.1f}
    - Dao động: {rsi['min']:.1f} - {rsi['max']:.1f}
  
  📉 Xu hướng 30 ngày:
    - Hướng: {trend['direction']} ({trend['change_pct']:+.2f}%)
    - Độ biến động: {trend['volatility_pct']:.2f}%
    - Tỷ lệ nến tăng: {pattern['bullish_ratio_pct']:.1f}% ({pattern['bullish_candles']}/{h4['candles_count']} nến)

"""
                    # Add institutional indicators for 4H
                    inst = h4.get('institutional_indicators', {})
                    if inst:
                        hist_klines_text += "  🏛️ Institutional Indicators (4H - 30 ngày):\n"
                        
                        vp = inst.get('volume_profile', {})
                        if vp:
                            hist_klines_text += f"    • Volume Profile: POC=${vp.get('poc', 0):,.4f}, VAH=${vp.get('vah', 0):,.4f}, VAL=${vp.get('val', 0):,.4f}\n"
                            hist_klines_text += f"      Position: {vp.get('current_position', 'N/A')}, Distance from POC: {vp.get('distance_from_poc_pct', 0):+.2f}%\n"
                        
                        fvg = inst.get('fair_value_gaps', {})
                        if fvg:
                            hist_klines_text += f"    • Fair Value Gaps: {fvg.get('total_bullish_gaps', 0)} bullish, {fvg.get('total_bearish_gaps', 0)} bearish\n"
                            hist_klines_text += f"      Unfilled: {fvg.get('unfilled_bullish_count', 0)} bullish, {fvg.get('unfilled_bearish_count', 0)} bearish\n"
                            hist_klines_text += f"      Gap Density: {fvg.get('gap_density_pct', 0):.2f}%\n"
                        
                        ob = inst.get('order_blocks', {})
                        if ob:
                            hist_klines_text += f"    • Order Blocks: {ob.get('total_bullish_ob', 0)} bullish, {ob.get('total_bearish_ob', 0)} bearish\n"
                            hist_klines_text += f"      Active: {ob.get('active_bullish_count', 0)} bullish, {ob.get('active_bearish_count', 0)} bearish\n"
                            hist_klines_text += f"      OB Density: {ob.get('ob_density_pct', 0):.2f}%\n"
                        
                        smc = inst.get('smart_money', {})
                        if smc:
                            hist_klines_text += f"    • Smart Money Concepts: Structure Bias={smc.get('structure_bias', 'N/A')} ({smc.get('bullish_bias_pct', 0):.1f}% bullish)\n"
                            hist_klines_text += f"      BOS: {smc.get('bos_bullish', 0)} bullish / {smc.get('bos_bearish', 0)} bearish\n"
                            hist_klines_text += f"      CHoCH: {smc.get('choch_bullish', 0)} bullish / {smc.get('choch_bearish', 0)} bearish\n"
                        
                        hist_klines_text += "\n"

            
            # 1D context (90 days)
            if '1d' in historical_klines:
                d1 = historical_klines['1d']
                if d1:
                    pr = d1['price_range']
                    vol = d1['volume']
                    rsi = d1['rsi_stats']
                    mfi = d1['mfi_stats']
                    trend = d1['trend']
                    pattern = d1['candle_pattern']
                    
                    hist_klines_text += f"""⏰ KHUNG 1D (90 NGÀY QUA - {d1['candles_count']} nến):
  
  📈 Giá:
    - Vùng: ${pr['low']:,.4f} - ${pr['high']:,.4f} (Range: {pr['range_pct']:.2f}%)
    - Hiện tại: ${pr['current']:,.4f} (Vị trí: {pr['position_in_range_pct']:.1f}% của range)
    - Trung bình: ${pr['average']:,.4f}
  
  📊 Volume:
    - Trung bình: {vol['average']:,.0f}
    - Hiện tại: {vol['current']:,.0f} (Tỷ lệ: {vol['current_vs_avg_ratio']:.2f}x)
    - Xu hướng: {vol['trend']}
  
  🎯 RSI & MFI:
    - RSI trung bình: {rsi['average']:.1f} | Hiện tại: {rsi['current']:.1f}
    - RSI dao động: {rsi['min']:.1f} - {rsi['max']:.1f}
    - MFI trung bình: {mfi['average']:.1f} | Hiện tại: {mfi['current']:.1f}
  
  📉 Xu hướng 90 ngày:
    - Hướng: {trend['direction']} ({trend['change_pct']:+.2f}%)
    - Độ biến động: {trend['volatility_pct']:.2f}%
    - Tỷ lệ nến tăng: {pattern['bullish_ratio_pct']:.1f}% ({pattern['bullish_candles']}/{d1['candles_count']} nến)

"""
                    # Add institutional indicators for 1D
                    inst = d1.get('institutional_indicators', {})
                    if inst:
                        hist_klines_text += "  🏛️ Institutional Indicators (1D - 90 ngày):\n"
                        
                        vp = inst.get('volume_profile', {})
                        if vp:
                            hist_klines_text += f"    • Volume Profile: POC=${vp.get('poc', 0):,.4f}, VAH=${vp.get('vah', 0):,.4f}, VAL=${vp.get('val', 0):,.4f}\n"
                            hist_klines_text += f"      Position: {vp.get('current_position', 'N/A')}, Distance from POC: {vp.get('distance_from_poc_pct', 0):+.2f}%\n"
                        
                        fvg = inst.get('fair_value_gaps', {})
                        if fvg:
                            hist_klines_text += f"    • Fair Value Gaps: {fvg.get('total_bullish_gaps', 0)} bullish, {fvg.get('total_bearish_gaps', 0)} bearish\n"
                            hist_klines_text += f"      Unfilled: {fvg.get('unfilled_bullish_count', 0)} bullish, {fvg.get('unfilled_bearish_count', 0)} bearish\n"
                            hist_klines_text += f"      Gap Density: {fvg.get('gap_density_pct', 0):.2f}%\n"
                        
                        ob = inst.get('order_blocks', {})
                        if ob:
                            hist_klines_text += f"    • Order Blocks: {ob.get('total_bullish_ob', 0)} bullish, {ob.get('total_bearish_ob', 0)} bearish\n"
                            hist_klines_text += f"      Active: {ob.get('active_bullish_count', 0)} bullish, {ob.get('active_bearish_count', 0)} bearish\n"
                            hist_klines_text += f"      OB Density: {ob.get('ob_density_pct', 0):.2f}%\n"
                        
                        smc = inst.get('smart_money', {})
                        if smc:
                            hist_klines_text += f"    • Smart Money Concepts: Structure Bias={smc.get('structure_bias', 'N/A')} ({smc.get('bullish_bias_pct', 0):.1f}% bullish)\n"
                            hist_klines_text += f"      BOS: {smc.get('bos_bullish', 0)} bullish / {smc.get('bos_bearish', 0)} bearish\n"
                            hist_klines_text += f"      CHoCH: {smc.get('choch_bullish', 0)} bullish / {smc.get('choch_bearish', 0)} bearish\n"
                            hist_klines_text += f"      Swing Highs/Lows: {smc.get('swing_highs_count', 0)} / {smc.get('swing_lows_count', 0)}\n"
                        
                        hist_klines_text += "\n"

            
            hist_klines_text += """HƯỚNG DẪN PHÂN TÍCH DỮ LIỆU LỊCH SỬ:
1. VỊ TRÍ TRONG RANGE: 
   - <30%: Gần đáy range → Cơ hội mua nếu trend tăng
   - 30-70%: Giữa range → Chờ xác nhận
   - >70%: Gần đỉnh range → Cẩn trọng nếu đang long

2. VOLUME RATIO:
   - >1.5x: Volume tăng mạnh → Quan tâm đột biến
   - 0.8-1.2x: Volume bình thường
   - <0.8x: Volume yếu → Thiếu conviction

3. RSI CONTEXT:
   - RSI hiện tại vs trung bình: Đánh giá momentum
   - RSI dao động: Range hẹp (<20) = sideway, Range rộng (>40) = trending
   - So sánh RSI các timeframe: Xác định trend đa khung

4. TREND CONSISTENCY:
   - Tỷ lệ nến tăng >60%: Uptrend rõ ràng
   - Tỷ lệ nến tăng 40-60%: Sideway/Consolidation
   - Tỷ lệ nến tăng <40%: Downtrend

5. VOLATILITY:
   - >3%: Biến động cao → Rủi ro cao, cơ hội cao
   - 1-3%: Biến động trung bình
   - <1%: Biến động thấp → Sideway

6. INSTITUTIONAL INDICATORS (HISTORICAL):
   - Volume Profile Position: 
     * PREMIUM (>VAH): Giá cao, có thể điều chỉnh xuống POC
     * VALUE_AREA: Giá fair, cân bằng
     * DISCOUNT (<VAL): Giá rẻ, có thể bật lên POC
   - Fair Value Gaps:
     * Unfilled gaps = magnets (giá có xu hướng fill gaps)
     * High gap density (>10%) = nhiều vùng trống, biến động mạnh
     * Nearest unfilled gap = S/R tiềm năng
   - Order Blocks:
     * Active OB = vùng institutional footprint, S/R mạnh
     * High OB density (>5%) = smart money tích cực
     * Strongest OB (strength >5) = vùng quan trọng
   - Smart Money Concepts:
     * Structure Bias: BULLISH/BEARISH/NEUTRAL
     * BOS (Break of Structure) = continuation signal
     * CHoCH (Change of Character) = reversal signal
     * High swing count = nhiều cấu trúc, trending market

SỬ DỤNG DỮ LIỆU NÀY ĐỂ:
- Xác định vùng giá quan trọng (support/resistance lịch sử)
- Đánh giá độ mạnh của trend hiện tại
- So sánh volume hiện tại với lịch sử
- Nhận biết pattern đảo chiều sớm
- Tính toán risk/reward dựa trên range lịch sử
- Phát hiện institutional accumulation/distribution zones
- Dự đoán price targets dựa trên POC và gaps
- Xác định trend consistency qua SMC structure
"""
        
        # === v4.0: ASSET TYPE DETECTION ===
        asset_type = self._detect_asset_type(symbol)
        
        # Build PUMP-FOCUSED prompt (v4.0 — no traditional indicators)
        prompt = f"""You are a specialized PUMP DETECTION AI. Your job is to VALIDATE the bot's pump signals using on-chain data, sentiment analysis, and news.

DO NOT analyze RSI, MFI, MACD, Stochastic, Volume Profile, FVG, Order Blocks, or SMC — the bot already calculates these internally.
Focus ONLY on: Pump validation, whale tracking, funding rates, news, and social sentiment.

═══════════════════════════════════════════
🎯 ASSET CLASSIFICATION
═══════════════════════════════════════════

SYMBOL: {symbol}
TYPE: {asset_type}
CURRENT PRICE: ${market['price']:,.2f}
24H CHANGE: {market['price_change_24h']:+.2f}%
24H HIGH: ${market['high_24h']:,.2f} | LOW: ${market['low_24h']:,.2f}
24H VOLUME: ${volume['current']:,.0f} USDT
24H TRADES: {volume['trades']:,}

═══════════════════════════════════════════
🚀 BOT'S PUMP DETECTION RESULT (VALIDATE THIS)
═══════════════════════════════════════════

{pump_text}

YOUR TASK: Use Google Search to VALIDATE or REFUTE the bot's detection.
VALIDATION CHECKLIST:
1. Does on-chain data support the volume spike? (Real buying vs wash trading?)
2. Are whales actually accumulating this coin? (Arkham/Whale Alert data)
3. Is there a news catalyst driving the move? (Partnership, listing, upgrade?)
4. Is the funding rate supporting the direction? (Short squeeze potential?)
5. What is the dump risk? (Token unlock, whale distribution, exchange inflow?)

═══════════════════════════════════════════
🔗 ON-CHAIN & DERIVATIVES DATA (SEARCH FOR THIS)
═══════════════════════════════════════════

Use Google Search to find real-time data:

A. WHALE & SMART MONEY:
   Search: "{symbol} whale alert large transfer today", "{symbol} exchange inflow outflow today"
   - Large transfers TO exchanges = SELL pressure (dump risk)
   - Large transfers FROM exchanges = Accumulation (bullish)

B. FUNDING RATE & DERIVATIVES:
   Search: "{symbol} funding rate current", "{symbol} open interest trend", "Coinglass {symbol}"
   - Funding > +0.05%: Longs overheated → long squeeze risk
   - Funding < -0.03%: Shorts dominant → SHORT SQUEEZE potential (bullish)
   - OI rising + price rising: Trend continuation
   - OI falling + price rising: Short covering rally (may fade)

C. EXCHANGE FLOW:
   Search: "{symbol} exchange reserve trend", "Glassnode {symbol} exchange flow"
   - Net outflows > $1M: Accumulation (coins leaving exchanges)
   - Net inflows > $1M: Distribution (coins entering exchanges for sale)

D. TOKEN SUPPLY EVENTS:
   Search: "{symbol} token unlock schedule 2026", "{symbol} tokenomics vesting"
   - Large unlock within 30 days = sell pressure risk
   - Team/VC tokens vesting = distribution risk

═══════════════════════════════════════════
📰 NEWS & SENTIMENT (SEARCH FOR THIS)
═══════════════════════════════════════════

A. BREAKING NEWS:
   Search: "{symbol} crypto news today", "{symbol} partnership announcement", "{symbol} exchange listing"
   Impact: CEX listing (+20%), Partnership (+10-15%), Hack/exploit (-30%), Delisting (SELL)

B. SOCIAL MEDIA HYPE:
   Search: "{symbol} crypto Twitter trending", "{symbol} Reddit discussion today"
   - EXTREME HYPE + pump signal = likely near local top
   - LOW HYPE + pump signal = stealth accumulation (BULLISH)

C. FEAR & GREED INDEX:
   Search: "crypto fear and greed index today"
   - <20 (Extreme Fear): CONTRARIAN BUY
   - >80 (Extreme Greed): CONTRARIAN SELL

D. BTC CONTEXT:
   Search: "Bitcoin price today", "Bitcoin ETF net flow today"
   - BTC dropping > 3%: ALL alts at risk → reduce confidence 20-30%

═══════════════════════════════════════════
⏱️ PUMP TIMING & RISK
═══════════════════════════════════════════

Assess which phase the pump is in:
1. PRE-PUMP: Low hype + whale accumulation + price flat → BEST ENTRY (24-72h to breakout)
2. EARLY PUMP: Volume spike + breakout → GOOD ENTRY (6-24h continuation)
3. MID PUMP: Extreme hype + massive volume → RISKY ENTRY (2-12h, dump risk HIGH)
4. LATE PUMP: Whale selling into FOMO → DO NOT ENTER (dump imminent)

DUMP RISK FACTORS:
- Token unlock < 7 days: +30 risk
- Whale transferring to exchange: +25 risk
- Extreme social hype: +20 risk
- Funding rate > +0.1%: +15 risk
- Low liquidity (vol < $5M): +10 risk
- Total > 50: HIGH DUMP RISK

═══════════════════════════════════════════
📋 HISTORICAL COMPARISON
═══════════════════════════════════════════

{hist_text}

═══════════════════════════════════════════
🧠 HISTORICAL LEARNING
═══════════════════════════════════════════

{historical_context}

═══════════════════════════════════════════
📊 JSON RESPONSE FORMAT
═══════════════════════════════════════════

Return analysis in this EXACT JSON format:

{{{{
  "recommendation": "BUY" | "SELL" | "HOLD" | "WAIT",
  "confidence": 0-100,
  "entry_point": price_in_USD,
  "stop_loss": price_in_USD,
  "take_profit": [TP1, TP2, TP3],
  "risk_level": "LOW" | "MEDIUM" | "HIGH",
  "reasoning_vietnamese": "300-500 từ phân tích tiếng Việt, tập trung: pump validation, on-chain evidence, news impact, entry/exit reasoning, dump risk",

  "pump_validation": {{{{
    "agrees_with_bot": true | false,
    "ai_pump_score": 0-100,
    "pump_type": "STEALTH_ACCUMULATION" | "WHALE_PUSH" | "RETAIL_FOMO" | "FAKE_PUMP" | "ORGANIC_GROWTH" | "NONE",
    "pump_phase": "PRE_PUMP" | "EARLY_PUMP" | "MID_PUMP" | "LATE_PUMP" | "NO_PUMP",
    "estimated_pump_time": "1-4h" | "4-12h" | "12-24h" | "24-48h" | "Already peaked" | "None",
    "dump_risk_score": 0-100,
    "reasoning": "Lý do xác nhận/phản bác pump (tiếng Việt)"
  }}}},

  "onchain_analysis": {{{{
    "whale_activity": "ACCUMULATING" | "DISTRIBUTING" | "NEUTRAL" | "UNKNOWN",
    "exchange_flow": "NET_INFLOW" | "NET_OUTFLOW" | "NEUTRAL" | "UNKNOWN",
    "large_transfers_detected": true | false,
    "funding_rate_signal": "SHORT_SQUEEZE_POTENTIAL" | "NEUTRAL" | "OVERHEATED_LONGS" | "LONG_SQUEEZE_RISK" | "UNKNOWN",
    "open_interest_trend": "INCREASING" | "STABLE" | "DECREASING" | "UNKNOWN",
    "liquidation_risk": "HIGH" | "MODERATE" | "LOW" | "UNKNOWN",
    "smart_money_direction": "BUYING" | "SELLING" | "NEUTRAL" | "UNKNOWN",
    "token_unlock_risk": "HIGH" | "MODERATE" | "LOW" | "NONE" | "UNKNOWN"
  }}}},

  "sentiment_analysis": {{{{
    "news_sentiment": "VERY_POSITIVE" | "POSITIVE" | "NEUTRAL" | "NEGATIVE" | "VERY_NEGATIVE",
    "latest_headline": "Tiêu đề tin tức liên quan nhất (tiếng Việt)",
    "social_hype_level": "EXTREME" | "HIGH" | "MODERATE" | "LOW" | "NONE",
    "fear_greed_index": 0-100,
    "fear_greed_signal": "EXTREME_FEAR_BUY" | "FEAR" | "NEUTRAL" | "GREED" | "EXTREME_GREED_SELL",
    "upcoming_catalyst": "Mô tả catalyst sắp tới (tiếng Việt)" | null,
    "btc_impact": "BULLISH_SUPPORT" | "NEUTRAL" | "BEARISH_DRAG" | "UNKNOWN"
  }}}},

  "key_points": ["Điểm chính 1 (tiếng Việt)", "Điểm chính 2", ...],
  "warnings": ["Cảnh báo 1 (tiếng Việt)", "Cảnh báo 2", ...],
  "market_sentiment": "BULLISH" | "BEARISH" | "NEUTRAL"
}}}}

CRITICAL RULES:
1. ALL text fields MUST be in VIETNAMESE
2. Use Google Search to find REAL data — do not fabricate numbers
3. If data unavailable, use "UNKNOWN" or null — NOT fabricated data
4. entry_point = current price or nearest support for BUY
5. stop_loss = 3-5% below entry for small caps, 2-3% for large caps
6. take_profit: TP1 (5-10%), TP2 (15-25%), TP3 (30-50%)
7. Always include dump_risk_score assessment
8. reasoning_vietnamese must explain: pump signal validation + on-chain evidence + news impact
"""
        
        # Old prompt sections removed in v4.0 (RSI/MFI/Stoch/VP/FVG/OB/SMC/institutional JSON)
        # AI now focuses on pump validation, on-chain, and sentiment
        

        # === NEW: ADD PATTERN RECOGNITION CONTEXT ===
        pattern_context = data.get('pattern_context')
        if pattern_context:
            regime = pattern_context.get('market_regime', {})
            patterns = pattern_context.get('universal_patterns', [])
            recommendations = pattern_context.get('recommendations', [])
            
            prompt += f"""

═══════════════════════════════════════════
🌍 CROSS-SYMBOL PATTERN RECOGNITION
═══════════════════════════════════════════

🔮 <b>MARKET REGIME: {regime.get('regime', 'UNKNOWN')}</b>
  • Confidence: {regime.get('confidence', 0) * 100:.0f}%
  • EMA Trend: {regime.get('metrics', {}).get('ema_trend', 'N/A')}
  • Volatility: {regime.get('metrics', {}).get('volatility', 'N/A')}
  • Volume: {regime.get('metrics', {}).get('volume', 'N/A')}

🎯 <b>REGIME-BASED RECOMMENDATIONS:</b>
"""
            for rec in recommendations:
                prompt += f"  {rec}\n"
            
            if patterns:
                prompt += "\n📊 <b>UNIVERSAL PATTERNS (Work across multiple symbols):</b>\n"
                for i, pattern in enumerate(patterns[:5], 1):  # Top 5
                    prompt += f"""  {i}. {pattern['condition']}
     • Win Rate: {pattern['win_rate']}% ({pattern['sample_size']} trades)
     • Symbols: {', '.join(pattern['symbols'])}
"""
            else:
                prompt += "\n⚠️ No universal patterns detected yet (insufficient data)\n"
            
            prompt += """
⚠️ <b>CRITICAL: Adjust your analysis based on market regime:</b>
  - BULL market → Favor BUY signals, tighter stops, look for dips to buy
  - BEAR market → Favor SELL signals, avoid longs unless strong reversal
  - SIDEWAYS → Range trading, buy support / sell resistance
  - If universal patterns match current setup → Increase confidence
"""
        
        prompt += "\nReturn ONLY valid JSON, no markdown formatting.\n"
        
        # === INJECT ADVANCED DETECTION RESULTS (NEW!) ===
        if data.get('advanced_detection') and ADVANCED_DETECTOR_AVAILABLE:
            try:
                advanced_section = integrate_advanced_detection_to_prompt(data['advanced_detection'])
                prompt += "\n" + advanced_section
                logger.info("✅ Injected advanced detection results into prompt")
            except Exception as e:
                logger.error(f"Error injecting advanced detection: {e}")
        
        return prompt
    
    def analyze(self, symbol: str, pump_data: Optional[Dict] = None, 
                trading_style: str = 'swing', use_cache: bool = True,
                user_id: Optional[int] = None) -> Optional[Dict]:
        """
        Perform AI analysis using Gemini with historical learning
        
        Args:
            symbol: Trading symbol
            pump_data: Optional pump detector data
            trading_style: 'scalping' or 'swing'
            use_cache: Whether to use cached results
            user_id: User ID for saving analysis and historical lookup
            
        Returns:
            Analysis result dict or None
        """
        try:
            # Check cache first
            if use_cache:
                cached = self._check_cache(symbol)
                if cached:
                    return cached
            
            logger.info(f"Starting Gemini AI analysis for {symbol} ({trading_style})")
            
            # Collect data
            data = self.collect_data(symbol, pump_data)
            if not data:
                logger.error(f"Failed to collect data for {symbol}")
                return None
            
            # === NEW: GET PATTERN RECOGNITION CONTEXT ===
            if self.db and user_id:
                try:
                    from pattern_recognition import get_pattern_context
                    pattern_context = get_pattern_context(self.db, self.binance, user_id, symbol)
                    data['pattern_context'] = pattern_context
                    logger.info(f"✅ Pattern context: {pattern_context['market_regime']['regime']} market")
                except Exception as e:
                    logger.warning(f"⚠️ Pattern recognition failed: {e}")
                    data['pattern_context'] = None
            
            # Build prompt with historical context and patterns
            prompt = self._build_prompt(data, trading_style, user_id)
            
            # Rate limit
            self._rate_limit()
            
            # Call Gemini API
            logger.info(f"Calling Gemini API for {symbol}...")
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=self.generate_config
                )
            except Exception as api_error:
                logger.error(f"Gemini API call failed for {symbol}: {api_error}")
                # Check for specific errors
                error_msg = str(api_error).lower()
                if 'quota' in error_msg or 'rate' in error_msg:
                    logger.error("⚠️ Rate limit exceeded or quota exhausted")
                elif 'key' in error_msg or 'auth' in error_msg:
                    logger.error("⚠️ API key authentication failed")
                elif 'timeout' in error_msg:
                    logger.error("⚠️ API request timeout")
                return None
            
            if not response:
                logger.error(f"Empty response from Gemini for {symbol}")
                return None

            # Extract text - handle search grounding response structure
            response_text_raw = None
            try:
                if response.text:
                    response_text_raw = response.text
            except Exception:
                pass

            # Fallback: iterate through candidates/parts for text
            if not response_text_raw:
                try:
                    for candidate in response.candidates:
                        for part in candidate.content.parts:
                            if hasattr(part, 'text') and part.text:
                                response_text_raw = (response_text_raw or '') + part.text
                except Exception as e:
                    logger.warning(f"Could not extract parts text: {e}")

            if not response_text_raw:
                logger.error(f"Empty response from Gemini for {symbol}")
                return None

            logger.info(f"Got response from Gemini for {symbol} (length: {len(response_text_raw)} chars)")

            # Parse JSON response
            response_text = response_text_raw.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            # Validate JSON before parsing
            if not response_text:
                logger.error(f"Empty response text after cleaning for {symbol}")
                return None
            
            # Parse JSON
            try:
                # STEP 1: Remove dangerous control characters (0x00-0x1F except tab, newline, carriage return)
                # Keep Unicode characters for Vietnamese text
                import re
                # Remove control chars except \t (09), \n (0A), \r (0D)
                response_text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]', '', response_text)
                
                # STEP 2: Additional JSON cleaning (MORE AGGRESSIVE)
                # Fix trailing commas in arrays/objects
                response_text = re.sub(r',\s*}', '}', response_text)
                response_text = re.sub(r',\s*]', ']', response_text)
                
                # Fix missing commas between object properties (common Gemini error)
                # Pattern: "value"\n  "key" -> "value",\n  "key"
                response_text = re.sub(r'"\s*\n\s*"', '",\n  "', response_text)
                
                # Fix missing commas after numbers in arrays
                response_text = re.sub(r'(\d)\s*\n\s*(\d)', r'\1,\2', response_text)
                
                # Fix missing commas in arrays: 100.00 200.00 -> 100.00, 200.00
                response_text = re.sub(r'(\d+\.?\d*)\s+(\d+\.?\d*)', r'\1, \2', response_text)
                
                # STEP 3: Handle long reasoning_vietnamese WITHOUT truncating
                # Instead of truncating, escape special characters properly
                def escape_json_string(text):
                    """Properly escape string for JSON"""
                    # Escape backslashes first
                    text = text.replace('\\', '\\\\')
                    # Escape quotes
                    text = text.replace('"', '\\"')
                    # Escape newlines (keep them as \n)
                    text = text.replace('\n', '\\n')
                    text = text.replace('\r', '\\r')
                    text = text.replace('\t', '\\t')
                    return text
                
                # Find and properly escape reasoning_vietnamese
                reasoning_match = re.search(r'"reasoning_vietnamese"\s*:\s*"(.*?)(?:"\s*[,}])', response_text, re.DOTALL)
                if reasoning_match:
                    reasoning_text = reasoning_match.group(1)
                    # Check if already escaped (contains \\n)
                    if '\\n' not in reasoning_text and '\n' in reasoning_text:
                        # Not escaped - needs escaping
                        escaped_reasoning = escape_json_string(reasoning_text)
                        # Replace in response_text
                        response_text = response_text.replace(
                            reasoning_match.group(0),
                            f'"reasoning_vietnamese": "{escaped_reasoning}",'
                        )
                        logger.info(f"✅ Escaped reasoning_vietnamese ({len(reasoning_text)} chars)")
                
                # Try to parse
                analysis = json.loads(response_text)
            except json.JSONDecodeError as json_err:
                logger.error(f"JSON parsing failed for {symbol}: {json_err}")
                logger.error(f"Response preview: {response_text[:500]}...")
                
                # Try to fix common JSON issues
                try:
                    # Strategy 1: Find matching braces and truncate after last complete object
                    brace_count = 0
                    last_valid_pos = -1
                    
                    for i, char in enumerate(response_text):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                last_valid_pos = i + 1
                                break
                    
                    if last_valid_pos > 0:
                        fixed_json = response_text[:last_valid_pos]
                        analysis = json.loads(fixed_json)
                        logger.info(f"✅ Fixed JSON by truncating at position {last_valid_pos}")
                    else:
                        raise ValueError("Could not find complete JSON object")
                        
                except Exception as fix_err:
                    logger.warning(f"JSON auto-fix failed: {fix_err}")
                    
                    # Strategy 2: Extract minimal required fields manually
                    try:
                        import re
                        
                        # Extract required fields with regex
                        rec_match = re.search(r'"recommendation"\s*:\s*"([^"]+)"', response_text)
                        conf_match = re.search(r'"confidence"\s*:\s*(\d+)', response_text)
                        entry_match = re.search(r'"entry_point"\s*:\s*([\d.]+)', response_text)
                        sl_match = re.search(r'"stop_loss"\s*:\s*([\d.]+)', response_text)
                        tp_match = re.search(r'"take_profit"\s*:\s*\[([\d.,\s]+)\]', response_text)
                        period_match = re.search(r'"expected_holding_period"\s*:\s*"([^"]+)"', response_text)
                        risk_match = re.search(r'"risk_level"\s*:\s*"([^"]+)"', response_text)
                        # Extract full reasoning without truncating
                        reason_match = re.search(r'"reasoning_vietnamese"\s*:\s*"(.*?)(?:"\s*[,}])', response_text, re.DOTALL)
                        
                        if rec_match and conf_match:
                            # Get full reasoning text (don't truncate)
                            full_reasoning = reason_match.group(1) if reason_match else 'Không có phân tích chi tiết.'
                            # Clean but don't truncate
                            full_reasoning = full_reasoning.replace('\\n', '\n').replace('\\r', '\r').replace('\\"', '"')
                            
                            # Build minimal valid JSON
                            analysis = {
                                'recommendation': rec_match.group(1),
                                'confidence': int(conf_match.group(1)),
                                'trading_style': 'swing',
                                'entry_point': float(entry_match.group(1)) if entry_match else 0,
                                'stop_loss': float(sl_match.group(1)) if sl_match else 0,
                                'take_profit': [float(x.strip()) for x in tp_match.group(1).split(',')] if tp_match else [],
                                'expected_holding_period': period_match.group(1) if period_match else '3-7 days',
                                'risk_level': risk_match.group(1) if risk_match else 'MEDIUM',
                                'reasoning_vietnamese': full_reasoning  # Keep full text
                            }
                            logger.info(f"✅ Extracted partial JSON with regex for {symbol} (reasoning: {len(full_reasoning)} chars)")
                        else:
                            logger.error(f"❌ Cannot extract minimal required fields (recommendation, confidence)")
                            return None
                    except Exception as extract_err:
                        logger.error(f"❌ Regex extraction also failed: {extract_err}")
                        return None
            
            # Add metadata
            analysis['symbol'] = symbol
            analysis['analyzed_at'] = datetime.now().isoformat()
            
            # === NEW v2.2: Add default values for new fields if missing ===
            # Asset Type (auto-detected if not in response)
            if 'asset_type' not in analysis:
                analysis['asset_type'] = self._detect_asset_type(symbol)
            
            # Sector Analysis (8 new fields - v2.2)
            if 'sector_analysis' not in analysis:
                analysis['sector_analysis'] = {
                    'sector': 'Unknown',
                    'sector_momentum': 'NEUTRAL',
                    'rotation_risk': 'None',
                    'sector_leadership': 'Not available'
                }
            
            # Correlation Analysis (3 new fields - v2.2)
            if 'correlation_analysis' not in analysis:
                analysis['correlation_analysis'] = {
                    'btc_correlation': 0,
                    'eth_correlation': 0,
                    'independent_move_probability': 50
                }
            
            # Fundamental Analysis (4 new fields - v2.2)
            if 'fundamental_analysis' not in analysis:
                analysis['fundamental_analysis'] = {
                    'health_score': 50,
                    'tokenomics': 'Unknown',
                    'centralization_risk': 'Medium',
                    'ecosystem_strength': 'Moderate'
                }
            
            # Position Sizing Recommendation (4 new fields - v2.2)
            if 'position_sizing_recommendation' not in analysis:
                analysis['position_sizing_recommendation'] = {
                    'position_size_percent': '1-2% of portfolio',
                    'risk_per_trade': '1-2%',
                    'recommended_leverage': '1x (no leverage)',
                    'liquidity_notes': 'Check liquidity before trading'
                }
            
            # Macro Context (conditional - v2.2)
            if 'macro_context' not in analysis:
                analysis['macro_context'] = {}
            
            # Legacy fields for backward compatibility
            analysis['data_used'] = {
                'rsi_mfi_consensus': data['rsi_mfi'].get('consensus', 'N/A') if isinstance(data.get('rsi_mfi'), dict) else 'N/A',
                'stoch_rsi_consensus': data['stoch_rsi'].get('consensus', 'N/A') if isinstance(data.get('stoch_rsi'), dict) else 'N/A',
                'pump_score': pump_data.get('final_score', 0) if pump_data and isinstance(pump_data, dict) else 0,
                'current_price': data['market_data']['price']
            }
            
            # === NEW: SAVE TO DATABASE AND START TRACKING ===
            if self.db and user_id:
                try:
                    # Prepare market snapshot (current indicators)
                    # Convert all data to JSON-serializable format (no pandas Series/Timestamp)
                    def make_serializable(obj):
                        """Convert pandas Series/Timestamp and other non-serializable objects to JSON-safe format"""
                        # Handle pandas Timestamp
                        if hasattr(obj, 'isoformat'):
                            return obj.isoformat()
                        # Handle pandas Series/DataFrame - convert first, then serialize recursively
                        elif hasattr(obj, 'to_dict'):
                            result = obj.to_dict()
                            # Recursively serialize the result (may have Timestamp keys)
                            return make_serializable(result)
                        elif hasattr(obj, 'tolist'):
                            result = obj.tolist()
                            return make_serializable(result)
                        # Handle dict with potential Timestamp keys
                        elif isinstance(obj, dict):
                            return {
                                (k.isoformat() if hasattr(k, 'isoformat') else str(k) if not isinstance(k, (str, int, float, bool, type(None))) else k): 
                                make_serializable(v) 
                                for k, v in obj.items()
                            }
                        # Handle list/tuple
                        elif isinstance(obj, (list, tuple)):
                            return [make_serializable(item) for item in obj]
                        # Handle primitives
                        elif isinstance(obj, (int, float, str, bool, type(None))):
                            return obj
                        # Fallback: convert to string
                        else:
                            return str(obj)
                    
                    market_snapshot = {
                        'price': float(data['market_data']['price']),
                        'rsi_mfi': data.get('rsi_mfi', {}),
                        'stoch_rsi': data.get('stoch_rsi', {}),
                        'volume_profile': data.get('volume_profile', {}),
                        'order_blocks': data.get('order_blocks', {}),
                        'smart_money': data.get('smart_money', {}),
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Convert entire market_snapshot (handles nested Timestamp keys)
                    market_snapshot = make_serializable(market_snapshot)
                    
                    # Get timeframe from trading style
                    timeframe = '5m' if trading_style == 'scalping' else '1h'
                    
                    # Save analysis to database (including WAIT recommendations)
                    analysis_id = self.db.save_analysis(
                        user_id=user_id,
                        symbol=symbol,
                        timeframe=timeframe,
                        ai_response=analysis,
                        market_snapshot=market_snapshot
                    )
                    
                    if analysis_id:
                        logger.info(f"✅ Saved analysis to database: {analysis_id}")
                        
                        # Check if analysis is dict before modifying
                        if isinstance(analysis, dict):
                            analysis['analysis_id'] = analysis_id
                            
                            # Start price tracking ONLY for BUY/SELL (not WAIT/HOLD)
                            recommendation = analysis.get('recommendation', '').upper()
                            if (self.tracker and 
                                recommendation in ['BUY', 'SELL'] and
                                analysis.get('entry_point') and 
                                analysis.get('stop_loss') and 
                                analysis.get('take_profit')):
                                
                                self.tracker.start_tracking(
                                    analysis_id=analysis_id,
                                    symbol=symbol,
                                    ai_response=analysis,
                                    entry_price=data['market_data']['price']
                                )
                                logger.info(f"✅ Started price tracking for {analysis_id}")
                            else:
                                logger.info(f"ℹ️ Analysis saved but not tracked (recommendation: {recommendation})")
                        else:
                            logger.warning(f"⚠️ Analysis is not dict (type: {type(analysis)}), cannot add analysis_id or start tracking")
                        
                        
                except Exception as db_error:
                    logger.error(f"❌ Failed to save analysis or start tracking: {db_error}", exc_info=True)
                    # Don't fail the whole analysis if DB save fails
            
            # Cache result
            self._update_cache(symbol, analysis)
            
            # Safe logging (check if analysis is dict)
            if isinstance(analysis, dict):
                logger.info(f"✅ Gemini analysis complete for {symbol}: {analysis.get('recommendation', 'N/A')} (confidence: {analysis.get('confidence', 0)}%)")
            else:
                logger.info(f"✅ Gemini analysis complete for {symbol} (type: {type(analysis)})")
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error in Gemini analysis for {symbol}: {e}", exc_info=True)
            return None
    
    def format_response(self, analysis: Dict) -> Tuple[str, str, str]:
        """
        Format analysis into 3 separate messages focusing on pump detection
        """
        def split_long_message(msg: str, max_length: int = 4000) -> list:
            if len(msg) <= max_length:
                return [msg]
            
            parts = []
            current_part = ""
            lines = msg.split('\n')
            
            for line in lines:
                if len(current_part) + len(line) + 1 > max_length:
                    if current_part:
                        parts.append(current_part.rstrip())
                        current_part = ""
                current_part += line + '\n'
            
            if current_part:
                parts.append(current_part.rstrip())
            return parts

        def encode_vietnamese(text):
            if not isinstance(text, str):
                text = str(text)
            
            vietnamese_map = {
                'à': '&#224;', 'á': '&#225;', 'ả': '&#7843;', 'ã': '&#227;', 'ạ': '&#7841;',
                'ă': '&#259;', 'ằ': '&#7857;', 'ắ': '&#7855;', 'ẳ': '&#7859;', 'ẵ': '&#7861;', 'ặ': '&#7863;',
                'â': '&#226;', 'ầ': '&#7847;', 'ấ': '&#7845;', 'ẩ': '&#7849;', 'ẫ': '&#7851;', 'ậ': '&#7853;',
                'đ': '&#273;',
                'è': '&#232;', 'é': '&#233;', 'ẻ': '&#7867;', 'ẽ': '&#7869;', 'ẹ': '&#7865;',
                'ê': '&#234;', 'ề': '&#7873;', 'ế': '&#7871;', 'ể': '&#7875;', 'ễ': '&#7877;', 'ệ': '&#7879;',
                'ì': '&#236;', 'í': '&#237;', 'ỉ': '&#7881;', 'ĩ': '&#297;', 'ị': '&#7883;',
                'ò': '&#242;', 'ó': '&#243;', 'ỏ': '&#7887;', 'õ': '&#245;', 'ọ': '&#7885;',
                'ô': '&#244;', 'ồ': '&#7891;', 'ố': '&#7889;', 'ổ': '&#7893;', 'ỗ': '&#7895;', 'ộ': '&#7897;',
                'ơ': '&#417;', 'ờ': '&#7901;', 'ớ': '&#7899;', 'ở': '&#7903;', 'ỡ': '&#7905;', 'ợ': '&#7907;',
                'ù': '&#249;', 'ú': '&#250;', 'ủ': '&#7911;', 'ũ': '&#361;', 'ụ': '&#7909;',
                'ư': '&#432;', 'ừ': '&#7915;', 'ứ': '&#7913;', 'ử': '&#7917;', 'ữ': '&#7919;', 'ự': '&#7921;',
                'ỳ': '&#7923;', 'ý': '&#253;', 'ỷ': '&#7927;', 'ỹ': '&#7929;', 'ỵ': '&#7925;',
                'À': '&#192;', 'Á': '&#193;', 'Ả': '&#7842;', 'Ã': '&#195;', 'Ạ': '&#7840;',
                'Ă': '&#258;', 'Ằ': '&#7856;', 'Ắ': '&#7854;', 'Ẳ': '&#7858;', 'Ẵ': '&#7860;', 'Ặ': '&#7862;',
                'Â': '&#194;', 'Ầ': '&#7846;', 'Ấ': '&#7844;', 'Ẩ': '&#7848;', 'Ẫ': '&#7850;', 'Ậ': '&#7852;',
                'Đ': '&#272;',
                'È': '&#200;', 'É': '&#201;', 'Ẻ': '&#7866;', 'Ẽ': '&#7868;', 'Ẹ': '&#7864;',
                'Ê': '&#202;', 'Ề': '&#7872;', 'Ế': '&#7870;', 'Ể': '&#7874;', 'Ễ': '&#7876;', 'Ệ': '&#7878;',
                'Ì': '&#204;', 'Í': '&#205;', 'Ỉ': '&#7880;', 'Ĩ': '&#296;', 'Ị': '&#7882;',
                'Ò': '&#210;', 'Ó': '&#211;', 'Ỏ': '&#7886;', 'Õ': '&#213;', 'Ọ': '&#7884;',
                'Ô': '&#212;', 'Ồ': '&#7890;', 'Ố': '&#7888;', 'Ổ': '&#7892;', 'Ỗ': '&#7894;', 'Ộ': '&#7896;',
                'Ơ': '&#416;', 'Ờ': '&#7900;', 'Ớ': '&#7898;', 'Ở': '&#7902;', 'Ỡ': '&#7904;', 'Ợ': '&#7906;',
                'Ù': '&#217;', 'Ú': '&#218;', 'Ủ': '&#7910;', 'Ũ': '&#360;', 'Ụ': '&#7908;',
                'Ư': '&#431;', 'Ừ': '&#7914;', 'Ứ': '&#7912;', 'Ử': '&#7916;', 'Ữ': '&#7918;', 'Ự': '&#7920;',
                'Ỳ': '&#7922;', 'Ý': '&#221;', 'Ỷ': '&#7926;', 'Ỹ': '&#7928;', 'Ỵ': '&#7924;',
            }
            text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
            for viet_char, html_entity in vietnamese_map.items():
                text = text.replace(viet_char, html_entity)
            return text

        try:
            symbol = analysis.get('symbol', 'UNKNOWN')
            rec = analysis.get('recommendation', 'WAIT')
            conf = analysis.get('confidence', 0)
            entry = analysis.get('entry_point', 0)
            stop = analysis.get('stop_loss', 0)
            targets = analysis.get('take_profit', [])
            risk = analysis.get('risk_level', 'UNKNOWN')
            
            # --- Message 1: SUMMARY PLAN ---
            rec_emoji = "🟢" if rec == "BUY" else "🔴" if rec == "SELL" else "🟡" if rec == "HOLD" else "⚪"
            
            summary = "🤖 <b>GEMINI AI PUMP DETECTOR v4.0</b>\n\n"
            summary += f"💎 <b>{symbol}</b>\n\n"
            summary += f"{rec_emoji} <b>KHUYẾN NGHỊ:</b> {rec}\n"
            summary += f"🎯 <b>Độ Tin Cậy:</b> {conf}%\n"
            summary += f"⚠️ <b>Mức Rủi Ro:</b> {risk}\n\n"
            
            if rec in ["BUY", "SELL", "HOLD"] and entry > 0:
                summary += "💰 <b>KẾ HOẠCH GIAO DỊCH</b>\n"
                summary += f"📍 <b>Điểm Vào:</b> ${self.binance.format_price(symbol, entry)}\n"
                summary += f"🛑 <b>Cắt Lỗ:</b> ${self.binance.format_price(symbol, stop)}\n"
                summary += "🎯 <b>Chốt Lời:</b>\n"
                for i, target in enumerate(targets, 1):
                    summary += f"   • TP{i}: ${self.binance.format_price(symbol, target)}\n\n"
            elif rec == "WAIT":
                summary += "⏸ <b>KHÔNG NÊN GIAO DỊCH</b>\n"
                summary += "📋 Tín hiệu chưa rõ ràng hoặc rủi ro xả hàng (dump risk) quá cao.\n\n"
                
            # --- Message 2: PUMP & ON-CHAIN ANALYSIS ---
            tech = "📊 <b>CHI TIẾT PUMP & ON-CHAIN</b>\n\n"
            tech += f"💎 <b>{symbol}</b>\n\n"
            
            pump = analysis.get('pump_validation', {})
            if pump:
                tech += "🚀 <b>XÁC NHẬN PUMP:</b>\n"
                bot_match = "Đồng thuận" if pump.get('agrees_with_bot') else "Phản bác"
                tech += f"• AI với Bot: {bot_match}\n"
                tech += f"• Điểm AI Pump: {pump.get('ai_pump_score', 0)}/100\n"
                tech += f"• Loại: {encode_vietnamese(pump.get('pump_type', ''))}\n"
                tech += f"• Giai đoạn: {encode_vietnamese(pump.get('pump_phase', ''))}\n"
                tech += f"• Rủi ro xả (Dump Risk): {pump.get('dump_risk_score', 0)}/100\n\n"

            onchain = analysis.get('onchain_analysis', {})
            if onchain:
                tech += "🔗 <b>ON-CHAIN & PHÁI SINH:</b>\n"
                tech += f"• Cá mập (Whales): {encode_vietnamese(onchain.get('whale_activity', ''))}\n"
                tech += f"• Dòng tiền sàn: {encode_vietnamese(onchain.get('exchange_flow', ''))}\n"
                tech += f"• Funding Rate: {encode_vietnamese(onchain.get('funding_rate_signal', ''))}\n"
                tech += f"• Xu hướng OI: {encode_vietnamese(onchain.get('open_interest_trend', ''))}\n"
                tech += f"• Rủi ro Token Unlock: {encode_vietnamese(onchain.get('token_unlock_risk', ''))}\n\n"
                
            sentiment = analysis.get('sentiment_analysis', {})
            if sentiment:
                tech += "📰 <b>TÂM LÝ & TIN TỨC:</b>\n"
                tech += f"• Tin tức: {encode_vietnamese(sentiment.get('news_sentiment', ''))}\n"
                tech += f"• Hype Mạng Xã Hội: {encode_vietnamese(sentiment.get('social_hype_level', ''))}\n"
                tech += f"• Fear & Greed: {sentiment.get('fear_greed_index', 'N/A')} ({encode_vietnamese(sentiment.get('fear_greed_signal', ''))})\n"
                if sentiment.get('latest_headline'):
                    tech += f"• Tin HOT: {encode_vietnamese(sentiment.get('latest_headline'))}\n\n"

            market_sent = analysis.get('market_sentiment', 'NEUTRAL')
            sent_emoji = "🟢" if market_sent == "BULLISH" else "🔴" if market_sent == "BEARISH" else "🟡"
            tech += f"💭 <b>Tổng Quan Thị Trường:</b> {sent_emoji} {encode_vietnamese(market_sent)}\n\n"

            warnings = analysis.get('warnings', [])
            if warnings:
                tech += "🚨 <b>CẢNH BÁO MỨC ĐỘ NGUY HIỂM:</b>\n"
                for warning in warnings:
                    tech += f"⚠️ {encode_vietnamese(warning)}\n"

            # --- Message 3: AI REASONING ---
            reasoning = "🧠 <b>LẬP LUẬN TỪ AI DỰA TRÊN DỮ LIỆU</b>\n\n"
            reasoning += f"💎 <b>{symbol}</b>\n\n"
            reasoning += encode_vietnamese(analysis.get('reasoning_vietnamese', 'Không có phân tích chi tiết.'))
            reasoning += "\n\n🎯 <b>Điểm Chính:</b>\n"
            for point in analysis.get('key_points', []):
                reasoning += f"✓ {encode_vietnamese(point)}\n"
            reasoning += f"\n⏰ <b>Thời gian cập nhật:</b> {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            reasoning += "<i>⚠️ Đây là phân tích AI định lượng, không phải lời khuyên đầu tư.</i>"
            
            self._split_message = split_long_message
            return summary, tech, reasoning
            
        except Exception as e:
            logger.error(f"Error formatting response: {e}")
            error_msg = f"❌ Lỗi khi format kết quả AI analysis: {str(e)}"

            return error_msg, "", ""

"""
Binance API Client Module
Handles all interactions with Binance API
"""

from binance.client import Client
from binance.exceptions import BinanceAPIException
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd
import logging
from datetime import datetime, timedelta
import time

logger = logging.getLogger(__name__)


class BinanceClient:
    def __init__(self, api_key, api_secret):
        """Initialize Binance client"""
        self.client = Client(api_key, api_secret)
        self.last_error = None
        # Ensure the underlying requests session has a sufficiently large connection pool
        # to avoid "Connection pool is full" warnings when the application makes many
        # concurrent requests (e.g., scanning hundreds of symbols).
        try:
            sess = getattr(self.client, 'session', None)
            if isinstance(sess, requests.Session):
                # Configure retries and larger pool sizes
                retry_strategy = Retry(total=3, status_forcelist=[429, 500, 502, 503, 504], backoff_factor=0.3)
                adapter = HTTPAdapter(pool_connections=50, pool_maxsize=50, max_retries=retry_strategy)
                sess.mount('https://', adapter)
                sess.mount('http://', adapter)
                logger.info('Configured HTTPAdapter for Binance client (pool_maxsize=50)')
        except Exception as e:
            logger.warning(f'Unable to configure Binance client session adapter: {e}')
        # Cache for symbol exchange info (to get precisions)
        self._symbol_info_cache = {}
        
        # Cache for klines data - reduce API calls
        # {(symbol, interval): {'data': df, 'timestamp': datetime}}
        self._klines_cache = {}
        self._cache_duration = 60  # Cache for 60 seconds
        
        # Rate limiting - track API weight usage
        self._last_request_time = 0
        self._min_request_interval = 0.1  # Minimum 100ms between requests
        
        logger.info("Binance client initialized")
    
    def _apply_rate_limit(self):
        """Apply rate limiting between API requests"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()
    
    def _get_cached_klines(self, symbol, interval, min_limit=None):
        """Get klines from cache if available, fresh, and sufficient"""
        cache_key = (symbol, interval)
        if cache_key in self._klines_cache:
            cached = self._klines_cache[cache_key]
            
            # Check age
            age = datetime.now() - cached['timestamp']
            if age.total_seconds() < self._cache_duration:
                # Check if we have enough data
                df = cached['data']
                if min_limit and len(df) < min_limit:
                    logger.debug(f"Cache hit but insufficient data for {symbol} {interval} (have {len(df)}, need {min_limit})")
                    return None
                
                logger.debug(f"Cache hit for {symbol} {interval} (age: {age.total_seconds():.1f}s)")
                return df
            else:
                # Cache expired, remove it - safe deletion of specific key
                try:
                    del self._klines_cache[cache_key]
                except KeyError:
                    pass  # Already deleted by another thread
        return None
    
    def _cache_klines(self, symbol, interval, df):
        """Cache klines data"""
        cache_key = (symbol, interval)
        self._klines_cache[cache_key] = {
            'data': df,
            'timestamp': datetime.now()
        }
        # Keep cache size under control (max 100 entries)
        if len(self._klines_cache) > 100:
            try:
                # Remove oldest entry - use list() to avoid "dictionary changed during iteration" error
                # Create items list to avoid KeyError if cache changes during min() operation
                cache_items = [(k, v['timestamp']) for k, v in list(self._klines_cache.items())]
                if cache_items:
                    oldest_key = min(cache_items, key=lambda x: x[1])[0]
                    if oldest_key in self._klines_cache and oldest_key != cache_key:
                        del self._klines_cache[oldest_key]
            except (KeyError, ValueError) as e:
                # Cache was modified by another thread, skip cleanup
                logger.debug(f"Cache cleanup skipped due to concurrent modification")

    def _load_symbol_info(self, symbol):
        """Load and cache symbol info from exchange info for precision calculation"""
        try:
            if not self._symbol_info_cache:
                exchange_info = self.client.get_exchange_info()
                for s in exchange_info.get('symbols', []):
                    self._symbol_info_cache[s['symbol']] = s
            return self._symbol_info_cache.get(symbol)
        except Exception as e:
            logger.error(f"Error loading exchange info: {e}")
            return None

    def get_price_precision(self, symbol):
        """Return number of decimal places for price for given symbol based on PRICE_FILTER.tickSize

        Falls back to 8 decimals if unknown.
        """
        try:
            info = self._load_symbol_info(symbol)
            if not info:
                return 8

            for f in info.get('filters', []):
                if f.get('filterType') == 'PRICE_FILTER':
                    tick = f.get('tickSize', '0.00000001')
                    # Count decimals in tickSize
                    if '.' in tick:
                        return max(0, len(tick.rstrip('0').split('.')[-1]))
                    else:
                        return 0
            return 8
        except Exception as e:
            logger.error(f"Error getting price precision for {symbol}: {e}")
            return 8

    def format_price(self, symbol, price):
        """Format price according to symbol precision, including thousand separators.

        Returns formatted string (no currency symbol).
        """
        try:
            if price is None:
                return '0'
            precision = self.get_price_precision(symbol)
            return f"{price:,.{precision}f}"
        except Exception as e:
            logger.error(f"Error formatting price for {symbol}: {e}")
            return str(price)
    
    def get_all_symbols(self, quote_asset='USDT', excluded_keywords=None, min_volume=0):
        """
        Get all trading symbols, filtered by criteria
        
        Args:
            quote_asset: Quote currency (default USDT)
            excluded_keywords: List of keywords to exclude (e.g., ['BEAR', 'BULL'])
            min_volume: Minimum 24h volume in quote asset (0 = no filter)
        
        Returns:
            List of symbol dictionaries with accurate volume data
        """
        if excluded_keywords is None:
            excluded_keywords = []
        
        try:
            # Get exchange info
            exchange_info = self.client.get_exchange_info()
            
            # Get 24h ticker for accurate volume data
            tickers = self.client.get_ticker()
            # Create dict: symbol -> {volume, price_change, etc}
            ticker_dict = {}
            for t in tickers:
                ticker_dict[t['symbol']] = {
                    'volume': float(t.get('quoteVolume', 0)),  # Volume in quote asset (USDT)
                    'base_volume': float(t.get('volume', 0)),  # Volume in base asset
                    'price_change_percent': float(t.get('priceChangePercent', 0)),
                    'last_price': float(t.get('lastPrice', 0))
                }
            
            valid_symbols = []
            
            for symbol_info in exchange_info['symbols']:
                symbol = symbol_info['symbol']
                
                # Check if it ends with quote asset
                if not symbol.endswith(quote_asset):
                    continue
                
                # Check if trading is enabled
                if symbol_info['status'] != 'TRADING':
                    continue
                
                # Check for excluded keywords
                if any(keyword in symbol for keyword in excluded_keywords):
                    logger.debug(f"Excluding {symbol} - contains excluded keyword")
                    continue
                
                # Get ticker data
                ticker_data = ticker_dict.get(symbol, {})
                quote_volume = ticker_data.get('volume', 0)  # Volume in USDT (quoteVolume)
                
                # Check minimum volume (if min_volume > 0)
                if min_volume > 0 and quote_volume < min_volume:
                    logger.debug(f"Excluding {symbol} - volume {quote_volume:,.0f} < {min_volume:,.0f}")
                    continue
                
                valid_symbols.append({
                    'symbol': symbol,
                    'base_asset': symbol_info['baseAsset'],
                    'quote_asset': symbol_info['quoteAsset'],
                    'volume': quote_volume,  # Accurate 24h volume in USDT
                    'price_change_percent': ticker_data.get('price_change_percent', 0)
                })
            
            logger.info(f"Found {len(valid_symbols)} valid symbols (volume filter: {min_volume:,.0f})")
            return valid_symbols
            
        except BinanceAPIException as e:
            logger.error(f"Binance API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting symbols: {e}")
            return []

    def get_all_usdt_symbols(self, limit=None, min_volume=0, excluded_keywords=None):
        """
        Convenience wrapper that returns a list of USDT symbol strings sorted by 24h quote volume (descending).

        Args:
            limit: If provided, returns only the top-N symbols by volume.
            min_volume: Minimum 24h volume in quote asset (USDT) to include.
            excluded_keywords: List of keywords to exclude from symbols.

        Returns:
            List of symbol strings (e.g., ['BTCUSDT', 'ETHUSDT', ...])
        """
        try:
            symbols = self.get_all_symbols(quote_asset='USDT', excluded_keywords=excluded_keywords, min_volume=min_volume)
            # symbols is a list of dicts with 'symbol' and 'volume'
            symbols_sorted = sorted(symbols, key=lambda x: x.get('volume', 0), reverse=True)
            symbol_list = [s['symbol'] for s in symbols_sorted]
            if limit is not None:
                return symbol_list[:limit]
            return symbol_list
        except Exception as e:
            logger.error(f"Error in get_all_usdt_symbols: {e}")
            return []
    
    def get_klines(self, symbol, interval, limit=500):
        """
        Get candlestick data for a symbol with caching and rate limiting
        
        Args:
            symbol: Trading pair symbol
            interval: Kline interval (e.g., '5m', '1h', '4h', '1d')
            limit: Number of candles to fetch (max 1000)
        
        Returns:
            pandas DataFrame with OHLCV data
        """
        self.last_error = None  # Reset error
        self.last_debug_info = "Init"
        try:
            # Check cache first
            cached_data = self._get_cached_klines(symbol, interval, min_limit=limit)
            if cached_data is not None:
                self.last_debug_info = f"Cache HIT len={len(cached_data)}"
                logger.info(f"DEBUG: Cache HIT for {symbol} {interval} len={len(cached_data)}")
                return cached_data
            
            self.last_debug_info = f"Cache MISS limit={limit} -> Calling API"
            logger.info(f"DEBUG: Cache MISS for {symbol} {interval} limit={limit}. Calling API...")
            
            # Apply rate limiting before API call
            self._apply_rate_limit()
            
            klines = self.client.get_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            self.last_debug_info += f" -> API returned {len(klines)}"
            logger.info(f"DEBUG: API returned {len(klines)} klines for {symbol} {interval} (requested {limit})")
            
            # Convert to DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            # Convert types - ensure all numeric columns are float
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume', 'quote_volume', 
                       'taker_buy_base', 'taker_buy_quote']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df.set_index('timestamp', inplace=True)
            
            # Cache the data
            self._cache_klines(symbol, interval, df)
            
            logger.debug(f"Fetched {symbol} {interval} from API (cached for {self._cache_duration}s)")
            return df
            
        except Exception as e:
            self.last_error = f"{type(e).__name__}: {e}"
            logger.error(f"Error getting klines for {symbol}: {e}")
            return None
    
    def get_multi_timeframe_data(self, symbol, intervals, limit=500):
        """
        Get kline data for multiple timeframes
        
        Args:
            symbol: Trading pair symbol
            intervals: List of intervals (e.g., ['5m', '1h', '4h', '1d'])
            limit: Number of candles per timeframe
        
        Returns:
            Dictionary of {interval: DataFrame}
        """
        data = {}
        
        for interval in intervals:
            df = self.get_klines(symbol, interval, limit)
            if df is not None and len(df) > 0:
                data[interval] = df
            else:
                logger.warning(f"No data for {symbol} on {interval}")
        
        return data
    
    def get_current_price(self, symbol):
        """Get current price for a symbol"""
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            return None
    
    def get_24h_data(self, symbol):
        """
        Get 24h market data for a symbol with accurate volume
        
        Returns:
            Dictionary with high, low, volume, price_change_percent, last_price
        """
        try:
            ticker = self.client.get_ticker(symbol=symbol)
            
            # Get accurate volume data
            quote_volume = float(ticker.get('quoteVolume', 0))  # Volume in USDT
            base_volume = float(ticker.get('volume', 0))        # Volume in base asset
            
            return {
                'high': float(ticker['highPrice']),
                'low': float(ticker['lowPrice']),
                'volume': quote_volume,  # Volume in quote asset (USDT) - ACCURATE
                'base_volume': base_volume,  # Volume in base asset
                'price_change_percent': float(ticker['priceChangePercent']),
                'price_change': float(ticker['priceChange']),
                'last_price': float(ticker.get('lastPrice', ticker.get('price', 0))),
                'trades': int(ticker.get('count', 0))  # Number of trades
            }
        except Exception as e:
            logger.error(f"Error getting 24h data for {symbol}: {e}")
            return None
    
    def test_connection(self):
        """Test Binance API connection"""
        try:
            self.client.ping()
            logger.info("Binance API connection successful")
            return True
        except Exception as e:
            logger.error(f"Binance API connection failed: {e}")
            return False

    def get_funding_rate(self, symbol):
        """
        Get latest Futures Funding Rate for a symbol
        Returns: float (e.g. 0.0001 for 0.01%, -0.0005 for -0.05%)
        """
        try:
            # futures_mark_price returns {'symbol': '...', 'lastFundingRate': '...', ...}
            # Note: client.futures_mark_price is the correct endpoint for real-time funding
            data = self.client.futures_mark_price(symbol=symbol)
            if isinstance(data, dict):
                return float(data.get('lastFundingRate', 0))
            return 0.0
        except Exception as e:
            # logger.debug(f"Funding rate not available for {symbol}: {e}") # Reduce noise
            return 0.0
            
    def get_order_book(self, symbol, limit=100):
        """
        Get order book (depth)
        """
        try:
            return self.client.get_order_book(symbol=symbol, limit=limit)
        except Exception as e:
            logger.error(f"Error getting order book for {symbol}: {e}")
            return None

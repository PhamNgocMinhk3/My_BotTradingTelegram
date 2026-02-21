"""
Telegram Bot Module
Handles sending messages and charts to Telegram
"""

import telebot
from telebot import types
import logging
import re
import io
import time
import os
import base64
from datetime import datetime
from vietnamese_messages import *
import config

logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self, token, chat_id):
        """Initialize Telegram bot"""
        self.bot = telebot.TeleBot(token)
        self.chat_id = chat_id
        logger.info("Telegram bot initialized")
    
    @staticmethod
    def sanitize_for_telegram(html_text: str) -> str:
        """
        Convert HTML text to Telegram-compatible format.
        
        Telegram supports: <b>, <i>, <u>, <s>, <code>, <pre>, <a>, <em>, <strong>
        Unsupported: <ul>, <li>, <ol>, <div>, <span>, <p>, etc.
        
        Args:
            html_text: HTML text from Gemini AI
            
        Returns:
            Telegram-compatible HTML text
        """
        import re
        
        text = html_text
        
        # Convert <ul><li> lists to bullet points
        # <ul><li>item1</li><li>item2</li></ul> → • item1\n• item2
        text = re.sub(r'<ul[^>]*>\s*', '', text)  # Remove <ul> tags
        text = re.sub(r'<li[^>]*>(.*?)</li>', r'• \1\n', text, flags=re.DOTALL)  # Convert <li> to bullets
        text = re.sub(r'</ul>', '', text)  # Remove </ul>
        
        # Convert <ol><li> ordered lists to numbered bullets
        # Find all <ol> blocks and number them
        ol_pattern = r'<ol[^>]*>(.*?)</ol>'
        def replace_ol(match):
            ol_content = match.group(1)
            items = re.findall(r'<li[^>]*>(.*?)</li>', ol_content, re.DOTALL)
            numbered = '\n'.join(f'{i}. {item.strip()}' for i, item in enumerate(items, 1))
            return numbered
        text = re.sub(ol_pattern, replace_ol, text, flags=re.DOTALL)
        
        # Remove any remaining <li>, <ul>, <ol> tags (shouldn't be any now)
        text = re.sub(r'</?li[^>]*>', '', text)
        text = re.sub(r'</?ul[^>]*>', '', text)
        text = re.sub(r'</?ol[^>]*>', '', text)
        
        # Remove unsupported tags but keep content
        unsupported_tags = ['div', 'span', 'p', 'article', 'section', 'nav', 'header', 'footer', 'main']
        for tag in unsupported_tags:
            # <div>content</div> → content
            text = re.sub(rf'</?{tag}[^>]*>', '', text)
        
        # Clean up excessive whitespace
        text = re.sub(r'\n\n\n+', '\n\n', text)  # Multiple newlines → double newline
        text = re.sub(r' +', ' ', text)  # Multiple spaces → single space
        
        return text.strip()
    
    def send_message(self, message, parse_mode='HTML', reply_markup=None, chat_id=None):
        """
        Send a text message
        
        Args:
            message: Message text
            parse_mode: 'HTML' or 'Markdown'
            reply_markup: Optional keyboard markup
            chat_id: Optional chat ID to send to (defaults to self.chat_id)
        """
        # Use provided chat_id or default to group chat
        target_chat_id = chat_id if chat_id is not None else self.chat_id
        
        try:
            # Telegram limit is 4096 characters
            MAX_LENGTH = 4096
            
            if len(message) > MAX_LENGTH:
                logger.warning(f"Message too long ({len(message)} chars), splitting...")
                # Split message into chunks
                chunks = []
                current_chunk = ""
                
                for line in message.split('\n'):
                    if len(current_chunk) + len(line) + 1 > MAX_LENGTH:
                        chunks.append(current_chunk)
                        current_chunk = line + '\n'
                    else:
                        current_chunk += line + '\n'
                
                if current_chunk:
                    chunks.append(current_chunk)
                
                # Send chunks
                for i, chunk in enumerate(chunks):
                    # Send with retry logic for 429 responses
                    sent = False
                    retries = 0
                    while not sent and retries < 3:
                        try:
                            self.bot.send_message(
                                chat_id=target_chat_id,
                                text=chunk,
                                parse_mode=parse_mode,
                                reply_markup=reply_markup if i == len(chunks) - 1 else None
                            )
                            logger.info(f"Message chunk {i+1}/{len(chunks)} sent ({len(chunk)} chars)")
                            sent = True
                        except Exception as e:
                            err = str(e)
                            # Detect rate limit and retry after specified seconds
                            if 'Too Many Requests' in err or '429' in err:
                                m = re.search(r'retry after (\d+)', err)
                                wait = int(m.group(1)) if m else 30
                                retries += 1
                                logger.warning(f"Rate limited by Telegram, retrying after {wait}s (attempt {retries})")
                                time.sleep(wait + 1)
                                continue
                            else:
                                logger.error(f"Error sending message chunk: {e}")
                                break
                
                return True
            else:
                # Send with retry logic for 429 responses
                sent = False
                retries = 0
                while not sent and retries < 3:
                    try:
                        self.bot.send_message(
                            chat_id=target_chat_id,
                            text=message,
                            parse_mode=parse_mode,
                            reply_markup=reply_markup
                        )
                        logger.info(f"Message sent successfully to chat {target_chat_id} ({len(message)} chars)")
                        sent = True
                    except Exception as e:
                        err = str(e)
                        if 'Too Many Requests' in err or '429' in err:
                            m = re.search(r'retry after (\d+)', err)
                            wait = int(m.group(1)) if m else 30
                            retries += 1
                            logger.warning(f"Rate limited by Telegram, retrying after {wait}s (attempt {retries})")
                            time.sleep(wait + 1)
                            continue
                        else:
                            logger.error(f"Error sending message: {e}")
                            break
                return sent
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            logger.error(f"Message length: {len(message) if message else 0} chars")
            # Log first 500 chars of message for debugging
            if message:
                logger.error(f"Message preview: {message[:500]}")
            return False
    
    def create_main_menu_keyboard(self):
        """Create main menu inline keyboard with updated info"""
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        
        # Row 1: Analysis
        keyboard.row(
            types.InlineKeyboardButton("📊 Quét Thị Trường", callback_data="cmd_scan"),
            types.InlineKeyboardButton("⭐ Quét Watchlist", callback_data="cmd_scanwatch")
        )
        
        # Row 2: Watchlist
        keyboard.row(
            types.InlineKeyboardButton("📝 Watchlist", callback_data="cmd_watchlist"),
            types.InlineKeyboardButton("🗑️ Xóa Watchlist", callback_data="cmd_clearwatch")
        )
        
        # Row 3: Volume
        keyboard.row(
            types.InlineKeyboardButton("🔥 Quét Volume", callback_data="cmd_volumescan"),
            types.InlineKeyboardButton("🎯 Cài Đặt Volume", callback_data="cmd_volumesensitivity")
        )
        
        # Row 4: Monitor
        keyboard.row(
            types.InlineKeyboardButton("🔔 Bật Monitor", callback_data="cmd_startmonitor"),
            types.InlineKeyboardButton("⏸️ Dừng Monitor", callback_data="cmd_stopmonitor")
        )
        
        # Row 5: Bot Monitor (70% threshold)
        keyboard.row(
            types.InlineKeyboardButton("🤖 Bot Monitor (70%)", callback_data="cmd_startbotmonitor"),
            types.InlineKeyboardButton("🛑 Dừng Bot Monitor", callback_data="cmd_stopbotmonitor")
        )
        
        # Row 6: Market Scanner
        keyboard.row(
            types.InlineKeyboardButton("🌍 Bật Market Scan", callback_data="cmd_startmarketscan"),
            types.InlineKeyboardButton("🛑 Dừng Market Scan", callback_data="cmd_stopmarketscan")
        )
        
        # Row 7: Pump Detector (3-Layer + Auto-save)
        keyboard.row(
            types.InlineKeyboardButton("🚀 Pump Watch (Auto-Save)", callback_data="cmd_startpumpwatch"),
            types.InlineKeyboardButton("⏸️ Dừng Pump Watch", callback_data="cmd_stoppumpwatch")
        )
        
        # Row 8: Info & Analysis
        keyboard.row(
            types.InlineKeyboardButton("📈 Top Coins", callback_data="cmd_top"),
            types.InlineKeyboardButton("🔍 Phân Tích Nhanh", callback_data="cmd_quickanalysis")
        )
        
        # Row 9: Status & Settings
        keyboard.row(
            types.InlineKeyboardButton("📊 Trạng Thái Bot", callback_data="cmd_status"),
            types.InlineKeyboardButton("⚙️ Cài Đặt", callback_data="cmd_settings")
        )
        
        # Row 10: Monitor Statuses
        keyboard.row(
            types.InlineKeyboardButton("📡 Monitor Status", callback_data="cmd_monitorstatus"),
            types.InlineKeyboardButton("🌐 Market Status", callback_data="cmd_marketstatus")
        )
        
        # Row 11: Advanced Features
        keyboard.row(
            types.InlineKeyboardButton("🤖 Bot Scan", callback_data="cmd_botmonitorstatus"),
            types.InlineKeyboardButton("🚀 Pump Scan", callback_data="cmd_pumpstatus")
        )
        
        # Row 12: Stoch+RSI Analysis (NEW)
        keyboard.row(
            types.InlineKeyboardButton("📊 Stoch+RSI (4 TF)", callback_data="cmd_stochrsi_menu")
        )
        
        # Row 13: Performance & Help
        keyboard.row(
            types.InlineKeyboardButton("⚡ Hiệu Suất", callback_data="cmd_performance"),
            types.InlineKeyboardButton("ℹ️ Trợ Giúp", callback_data="cmd_help")
        )
        
        return keyboard
    
    def create_watchlist_keyboard(self):
        """Create watchlist management keyboard"""
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        
        # View and scan
        keyboard.row(
            types.InlineKeyboardButton("📝 Xem Danh Sách", callback_data="cmd_watchlist"),
            types.InlineKeyboardButton("⭐ Quét Tất Cả", callback_data="cmd_scanwatch")
        )
        
        # Volume scan and clear
        keyboard.row(
            types.InlineKeyboardButton("🔥 Quét Volume", callback_data="cmd_volumescan"),
            types.InlineKeyboardButton("🗑️ Xóa Tất Cả", callback_data="cmd_clearwatch")
        )
        
        # Info about auto-save
        keyboard.row(
            types.InlineKeyboardButton("💡 Auto-Save từ Pump >= 80%", callback_data="cmd_pumpstatus")
        )
        
        keyboard.row(
            types.InlineKeyboardButton("🔙 Menu Chính", callback_data="cmd_menu")
        )
        
        return keyboard
    
    def create_private_chat_keyboard(self):
        """
        Create simplified keyboard for private chat users
        Only shows popular symbol shortcuts - users can also use /SYMBOL commands
        """
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        
        # Row 1: Popular Symbols - Direct analysis
        keyboard.row(
            types.InlineKeyboardButton("₿ Bitcoin", callback_data="cmd_BTC"),
            types.InlineKeyboardButton("� Ethereum", callback_data="cmd_ETH")
        )
        
        # Row 2: More Popular Symbols
        keyboard.row(
            types.InlineKeyboardButton("💎 BNB", callback_data="cmd_BNB"),
            types.InlineKeyboardButton("🔷 XRP", callback_data="cmd_XRP")
        )
        
        # Row 3: Additional Symbols
        keyboard.row(
            types.InlineKeyboardButton("☀️ SOL", callback_data="cmd_SOL"),
            types.InlineKeyboardButton("� ADA", callback_data="cmd_ADA")
        )
        
        # Row 4: More Symbols
        keyboard.row(
            types.InlineKeyboardButton("� DOGE", callback_data="cmd_DOGE"),
            types.InlineKeyboardButton("� MATIC", callback_data="cmd_MATIC")
        )
        
        # Row 5: Help
        keyboard.row(
            types.InlineKeyboardButton("ℹ️ Trợ Giúp", callback_data="cmd_help")
        )
        
        return keyboard
    
    def create_ai_analysis_keyboard(self, symbol, user_id=None, chat_id=None, chat_type='private'):
        """
        Create AI analysis and Live Chart buttons
        
        Args:
            symbol: Trading symbol (e.g., BTCUSDT)
            user_id: User ID who clicked the button (for logging)
            chat_id: Chat ID where button was clicked (for logging)
            chat_type: Type of chat ('private', 'group', 'supergroup')
        """
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        
        # Row 1: AI Analysis and TradingView buttons
        from chart_generator import get_tradingview_chart_url
        tradingview_url = get_tradingview_chart_url(symbol, interval='60')  # 1 hour chart
        
        keyboard.row(
            types.InlineKeyboardButton(f"🤖 AI Phân Tích", callback_data=f"ai_analyze_{symbol}"),
            types.InlineKeyboardButton(f"📊 TradingView", url=tradingview_url)
        )
        
        # Row 2: Live Chart - Different behavior based on chat type
        webapp_url = self._get_webapp_url()
        if webapp_url:
            if chat_type == 'private':
                # In private chat: Use WebApp (opens IN Telegram)
                # Add timestamp to bust Telegram's WebApp URL cache
                cache_buster = int(time.time())
                chart_webapp_url = f"{webapp_url}/webapp/chart.html?symbol={symbol}&timeframe=1h&_t={cache_buster}"
                logger.info(f"🔗 [ai_keyboard] WebApp URL: {chart_webapp_url}")
                keyboard.row(
                    types.InlineKeyboardButton(
                        "📊 Live Chart (in Telegram)", 
                        web_app=types.WebAppInfo(url=chart_webapp_url)
                    )
                )
            else:
                # In groups: Use t.me link to open private chat with bot
                # This will start bot in PM with user, then open WebApp
                bot_username = self._get_bot_username()
                if bot_username:
                    # Format: chart:SYMBOL:USERID:CHATID (use : instead of _ to avoid parsing issues)
                    # Then base64 encode to make it URL-safe and shorter
                    data_string = f"chart:{symbol}:{user_id}:{chat_id}" if user_id and chat_id else f"chart:{symbol}"
                    
                    # Base64 encode (URL-safe)
                    encoded = base64.urlsafe_b64encode(data_string.encode()).decode().rstrip('=')
                    bot_link = f"https://t.me/{bot_username}?start={encoded}"
                    
                    # Debug log
                    logger.info(f"🔗 Creating group link - Symbol: {symbol}, User: {user_id}, Chat: {chat_id}")
                    logger.info(f"🔗 Data string: {data_string}")
                    logger.info(f"🔗 Encoded: {encoded}")
                    logger.info(f"🔗 Full link: {bot_link}")
                    
                    keyboard.row(
                        types.InlineKeyboardButton(
                            "📊 Open Live Chart in Bot", 
                            url=bot_link
                        )
                    )
                    # Log access attempt
                    if user_id and chat_id:
                        logger.info(f"📊 Chart access from group - User ID: {user_id}, Chat ID: {chat_id}, Symbol: {symbol}")
        
        return keyboard
    
    def create_symbol_analysis_keyboard(self, symbol, user_id=None, chat_id=None, chat_type='private'):
        """
        Create keyboard with AI analysis, Chart and Live Chart buttons
        
        Args:
            symbol: Trading symbol (e.g., BTCUSDT)
            user_id: User ID who clicked the button (for logging)
            chat_id: Chat ID where button was clicked (for logging)
            chat_type: Type of chat ('private', 'group', 'supergroup')
        """
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        
        # Row 1: AI Analysis and TradingView buttons
        from chart_generator import get_tradingview_chart_url
        tradingview_url = get_tradingview_chart_url(symbol, interval='60')  # 1 hour chart
        
        keyboard.row(
            types.InlineKeyboardButton(f"🤖 AI Phân Tích", callback_data=f"ai_analyze_{symbol}"),
            types.InlineKeyboardButton(f"📊 TradingView", url=tradingview_url)
        )
        
        # Row 2: Live Chart - Different behavior based on chat type
        webapp_url = self._get_webapp_url()
        if webapp_url:
            if chat_type == 'private':
                # In private chat: Use WebApp (opens IN Telegram)
                # Add timestamp to bust Telegram's WebApp URL cache
                cache_buster = int(time.time())
                chart_webapp_url = f"{webapp_url}/webapp/chart.html?symbol={symbol}&timeframe=1h&_t={cache_buster}"
                logger.info(f"🔗 [symbol_keyboard] WebApp URL: {chart_webapp_url}")
                keyboard.row(
                    types.InlineKeyboardButton(
                        "📊 Live Chart (in Telegram)", 
                        web_app=types.WebAppInfo(url=chart_webapp_url)
                    )
                )
            else:
                # In groups: Use t.me link to open private chat with bot
                bot_username = self._get_bot_username()
                if bot_username:
                    # Format: chart:SYMBOL:USERID:CHATID (use : instead of _ to avoid parsing issues)
                    # Then base64 encode to make it URL-safe and shorter
                    data_string = f"chart:{symbol}:{user_id}:{chat_id}" if user_id and chat_id else f"chart:{symbol}"
                    
                    # Base64 encode (URL-safe)
                    encoded = base64.urlsafe_b64encode(data_string.encode()).decode().rstrip('=')
                    bot_link = f"https://t.me/{bot_username}?start={encoded}"
                    
                    # Debug log
                    logger.info(f"🔗 Creating group link (symbol_analysis) - Symbol: {symbol}, User: {user_id}, Chat: {chat_id}")
                    logger.info(f"🔗 Data string: {data_string}")
                    logger.info(f"🔗 Encoded: {encoded}")
                    
                    keyboard.row(
                        types.InlineKeyboardButton(
                            "📊 Open Live Chart in Bot", 
                            url=bot_link
                        )
                    )
                    # Log access attempt
                    if user_id and chat_id:
                        logger.info(f"📊 Chart access from group - User ID: {user_id}, Chat ID: {chat_id}, Symbol: {symbol}")
        
        return keyboard
    
    def _get_webapp_url(self):
        """Get WebApp URL from environment variables"""
        # Railway automatically provides RAILWAY_PUBLIC_DOMAIN
        railway_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")
        if railway_domain:
            webapp_url = f"https://{railway_domain}"
            logger.info(f"✅ Using Railway domain for WebApp: {webapp_url}")
            logger.info(f"🔗 Buttons will use: {webapp_url}/webapp/chart.html")
            return webapp_url
        
        # Fallback to manual WEBAPP_URL
        webapp_url = os.getenv("WEBAPP_URL", "")
        
        # Validate URL - must be real, not placeholder
        if webapp_url and not any(placeholder in webapp_url for placeholder in ['your-app', 'example', 'placeholder']):
            logger.info(f"✅ Using manual WEBAPP_URL: {webapp_url}")
            logger.info(f"🔗 Buttons will use: {webapp_url}/webapp/chart.html")
            return webapp_url
        elif webapp_url:
            logger.warning(f"⚠️ WEBAPP_URL is set but appears to be a placeholder: {webapp_url}")
        
        # For testing/development - you can uncomment and set your Railway URL here
        # Example: return "https://your-app-name.up.railway.app"
        
        logger.warning("⚠️ No valid WEBAPP_URL or RAILWAY_PUBLIC_DOMAIN found - Live Chart button disabled")
        logger.warning("⚠️ Please set RAILWAY_PUBLIC_DOMAIN or WEBAPP_URL environment variable")
        logger.warning("⚠️ Example: WEBAPP_URL=https://rsi-mfi-bot-production.up.railway.app")
        return None
    
    def _get_bot_username(self):
        """Get bot username (cached)"""
        if not hasattr(self, '_bot_username'):
            try:
                bot_info = self.bot.get_me()
                self._bot_username = bot_info.username
                logger.info(f"✅ Bot username: @{self._bot_username}")
            except Exception as e:
                logger.error(f"❌ Error getting bot username: {e}")
                self._bot_username = None
        return self._bot_username
    
    def create_update_keyboard(self, symbol, webapp_url=None):
        """
        Create keyboard for update/priority alerts with explicit Update Context
        
        Args:
            symbol: Trading symbol (e.g., BTCUSDT)
            webapp_url: Optional URL for Telegram WebApp
        """
        import time
        from chart_generator import get_tradingview_chart_url
        
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        
        # WebApp Live Chart button (opens in Telegram)
        if webapp_url:
            cache_buster = int(time.time())
            chart_webapp_url = f"{webapp_url}/webapp/chart.html?symbol={symbol}&timeframe=1h&_t={cache_buster}"
            keyboard.row(
                types.InlineKeyboardButton(
                    "📊 Live Chart (Cập Nhật)", 
                    web_app=types.WebAppInfo(url=chart_webapp_url)
                )
            )
        
        # TradingView fallback buttons
        keyboard.row(
            types.InlineKeyboardButton("📈 TradingView 1H", url=get_tradingview_chart_url(symbol, '60')),
            types.InlineKeyboardButton("📈 TradingView 4H", url=get_tradingview_chart_url(symbol, '240'))
        )
        
        # AI Analysis specifically for Updates (bypasses cache and compares old/new data)
        keyboard.row(
            types.InlineKeyboardButton("🤖 AI Phân Tích (Cập Nhật)", callback_data=f"ai_update_{symbol}")
        )
        
        return keyboard
        
    def create_chart_keyboard(self, symbol, webapp_url=None):
        """Create keyboard with Live Chart (WebApp) and timeframe options"""
        from chart_generator import get_tradingview_chart_url
        
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        
        # WebApp Live Chart button (opens in Telegram)
        if webapp_url:
            # Add timestamp to bust Telegram's WebApp URL cache
            cache_buster = int(time.time())
            chart_webapp_url = f"{webapp_url}/webapp/chart.html?symbol={symbol}&timeframe=1h&_t={cache_buster}"
            logger.info(f"🔗 [chart_keyboard] WebApp URL: {chart_webapp_url}")
            keyboard.row(
                types.InlineKeyboardButton(
                    "📊 Live Chart (in Telegram)", 
                    web_app=types.WebAppInfo(url=chart_webapp_url)
                )
            )
        
        # TradingView buttons (opens in browser) - as fallback
        keyboard.row(
            types.InlineKeyboardButton("📈 TradingView 1H", url=get_tradingview_chart_url(symbol, '60')),
            types.InlineKeyboardButton("📈 TradingView 4H", url=get_tradingview_chart_url(symbol, '240'))
        )
        keyboard.row(
            types.InlineKeyboardButton("📈 TradingView 1D", url=get_tradingview_chart_url(symbol, 'D')),
            types.InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_chart_{symbol}")
        )
        
        # Back to analysis
        keyboard.row(
            types.InlineKeyboardButton("🤖 AI Phân Tích", callback_data=f"ai_analyze_{symbol}")
        )
        
        return keyboard
    
    def create_group_chart_keyboard(self, symbol):
        """
        Create keyboard for group chat with t.me link to open Live Chart in private
        
        Args:
            symbol: Trading symbol (e.g., BTCUSDT)
        """
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        
        # Get bot username for t.me link
        bot_username = self._get_bot_username()
        if bot_username:
            # Create t.me link to open bot in private and show Live Chart
            # Format: chart:SYMBOL (simple format for deep linking)
            data_string = f"chart:{symbol}"
            encoded = base64.urlsafe_b64encode(data_string.encode()).decode().rstrip('=')
            bot_link = f"https://t.me/{bot_username}?start={encoded}"
            
            logger.info(f"🔗 Creating group chart link - Symbol: {symbol}, Encoded: {encoded}")
            
            # Button to open Live Chart in private chat
            keyboard.row(
                types.InlineKeyboardButton(
                    "📊 Xem Live Chart", 
                    url=bot_link
                )
            )
        
        # TradingView fallback buttons (always work in groups)
        from chart_generator import get_tradingview_chart_url
        keyboard.row(
            types.InlineKeyboardButton("📈 TradingView 1H", url=get_tradingview_chart_url(symbol, '60')),
            types.InlineKeyboardButton("📈 TradingView 4H", url=get_tradingview_chart_url(symbol, '240'))
        )
        
        return keyboard
    
    def create_monitor_keyboard(self):
        """Create monitor control keyboard"""
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        
        # Control buttons
        keyboard.row(
            types.InlineKeyboardButton("🔔 Bật Monitor", callback_data="cmd_startmonitor"),
            types.InlineKeyboardButton("⏸️ Dừng Monitor", callback_data="cmd_stopmonitor")
        )
        
        # Status
        keyboard.row(
            types.InlineKeyboardButton("📊 Trạng Thái (5 phút/lần)", callback_data="cmd_monitorstatus")
        )
        
        keyboard.row(
            types.InlineKeyboardButton("🔙 Menu Chính", callback_data="cmd_menu")
        )
        
        return keyboard
    
    def create_volume_keyboard(self):
        """Create volume settings keyboard"""
        keyboard = types.InlineKeyboardMarkup(row_width=3)
        
        keyboard.row(
            types.InlineKeyboardButton("🔥 Quét Ngay", callback_data="cmd_volumescan")
        )
        keyboard.row(
            types.InlineKeyboardButton("🔴 Thấp", callback_data="vol_low"),
            types.InlineKeyboardButton("🟡 Trung Bình", callback_data="vol_medium"),
            types.InlineKeyboardButton("🟢 Cao", callback_data="vol_high")
        )
        keyboard.row(
            types.InlineKeyboardButton("🔙 Menu Chính", callback_data="cmd_menu")
        )
        
        return keyboard
    
    def create_quick_analysis_keyboard(self):
        """Create quick analysis keyboard for popular coins"""
        keyboard = types.InlineKeyboardMarkup(row_width=3)
        
        keyboard.row(
            types.InlineKeyboardButton("₿ BTC", callback_data="analyze_BTCUSDT"),
            types.InlineKeyboardButton("Ξ ETH", callback_data="analyze_ETHUSDT"),
            types.InlineKeyboardButton("₿ BNB", callback_data="analyze_BNBUSDT")
        )
        keyboard.row(
            types.InlineKeyboardButton("🔗 LINK", callback_data="analyze_LINKUSDT"),
            types.InlineKeyboardButton("⚪ DOT", callback_data="analyze_DOTUSDT"),
            types.InlineKeyboardButton("🔵 ADA", callback_data="analyze_ADAUSDT")
        )
        keyboard.row(
            types.InlineKeyboardButton("🟣 SOL", callback_data="analyze_SOLUSDT"),
            types.InlineKeyboardButton("⚫ AVAX", callback_data="analyze_AVAXUSDT"),
            types.InlineKeyboardButton("🔴 MATIC", callback_data="analyze_MATICUSDT")
        )
        keyboard.row(
            types.InlineKeyboardButton("🔙 Menu Chính", callback_data="cmd_menu")
        )
        
        return keyboard
    
    def create_action_keyboard(self):
        """Create action keyboard for commands that completed an action"""
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        
        keyboard.row(
            types.InlineKeyboardButton("📊 Quét Thị Trường", callback_data="cmd_scan"),
            types.InlineKeyboardButton("⭐ Quét Watchlist", callback_data="cmd_scanwatch")
        )
        keyboard.row(
            types.InlineKeyboardButton("📝 Xem Watchlist", callback_data="cmd_watchlist"),
            types.InlineKeyboardButton("🔥 Quét Volume", callback_data="cmd_volumescan")
        )
        keyboard.row(
            types.InlineKeyboardButton("🔙 Menu Chính", callback_data="cmd_menu")
        )
        
        return keyboard
    
    def create_bot_monitor_keyboard(self):
        """Create bot monitor control keyboard"""
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        
        # Control buttons
        keyboard.row(
            types.InlineKeyboardButton("🤖 Bật Bot Monitor", callback_data="cmd_startbotmonitor"),
            types.InlineKeyboardButton("🛑 Dừng Bot Monitor", callback_data="cmd_stopbotmonitor")
        )
        
        # Status and scan
        keyboard.row(
            types.InlineKeyboardButton("📊 Trạng Thái", callback_data="cmd_botmonitorstatus"),
            types.InlineKeyboardButton("🔍 Quét Bot Ngay", callback_data="cmd_botscan")
        )
        
        # Settings info
        keyboard.row(
            types.InlineKeyboardButton("⚙️ Ngưỡng: 70% (High Confidence)", callback_data="cmd_botthreshold")
        )
        
        keyboard.row(
            types.InlineKeyboardButton("🔙 Menu Chính", callback_data="cmd_menu")
        )
        
        return keyboard
    
    def create_pump_detector_keyboard(self):
        """Create pump detector control keyboard with auto-save info"""
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        
        # Control buttons
        keyboard.row(
            types.InlineKeyboardButton("🚀 Bật Pump Watch", callback_data="cmd_startpumpwatch"),
            types.InlineKeyboardButton("⏸️ Dừng Pump Watch", callback_data="cmd_stoppumpwatch")
        )
        
        # Status and full scan
        keyboard.row(
            types.InlineKeyboardButton("📊 Trạng Thái & Settings", callback_data="cmd_pumpstatus")
        )
        keyboard.row(
            types.InlineKeyboardButton("🌐 Quét TẤT CẢ Coins (Top 200)", callback_data="pumpscan_all")
        )
        
        # Quick scan popular coins
        keyboard.row(
            types.InlineKeyboardButton("₿ BTC", callback_data="pumpscan_BTCUSDT"),
            types.InlineKeyboardButton("Ξ ETH", callback_data="pumpscan_ETHUSDT")
        )
        keyboard.row(
            types.InlineKeyboardButton("� BNB", callback_data="pumpscan_BNBUSDT"),
            types.InlineKeyboardButton("� SOL", callback_data="pumpscan_SOLUSDT")
        )
        
        # Info
        keyboard.row(
            types.InlineKeyboardButton("💡 Auto-Save >= 80%", callback_data="cmd_pumpstatus")
        )
        
        keyboard.row(
            types.InlineKeyboardButton("🔙 Menu Chính", callback_data="cmd_menu")
        )
        
        return keyboard
    
    def create_market_scanner_keyboard(self):
        """Create market scanner control keyboard"""
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        
        # Control buttons
        keyboard.row(
            types.InlineKeyboardButton("🌍 Bật Market Scan", callback_data="cmd_startmarketscan"),
            types.InlineKeyboardButton("🛑 Dừng Market Scan", callback_data="cmd_stopmarketscan")
        )
        
        # Status
        keyboard.row(
            types.InlineKeyboardButton("📊 Trạng Thái (15 phút/lần)", callback_data="cmd_marketstatus")
        )
        
        keyboard.row(
            types.InlineKeyboardButton("🔙 Menu Chính", callback_data="cmd_menu")
        )
        
        return keyboard
    
    def create_stoch_rsi_keyboard(self):
        """Create Stoch+RSI multi-timeframe analysis keyboard"""
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        
        keyboard.row(
            types.InlineKeyboardButton("📊 Stoch+RSI Analysis", callback_data="cmd_stochrsi_info")
        )
        
        # Quick analysis for popular coins
        keyboard.row(
            types.InlineKeyboardButton("₿ BTC", callback_data="stochrsi_BTCUSDT"),
            types.InlineKeyboardButton("Ξ ETH", callback_data="stochrsi_ETHUSDT")
        )
        keyboard.row(
            types.InlineKeyboardButton("🔶 BNB", callback_data="stochrsi_BNBUSDT"),
            types.InlineKeyboardButton("🟣 SOL", callback_data="stochrsi_SOLUSDT")
        )
        keyboard.row(
            types.InlineKeyboardButton("🔗 LINK", callback_data="stochrsi_LINKUSDT"),
            types.InlineKeyboardButton("🔵 ADA", callback_data="stochrsi_ADAUSDT")
        )
        
        keyboard.row(
            types.InlineKeyboardButton("💡 Combines: Stoch + RSI (4 TF)", callback_data="cmd_stochrsi_info")
        )
        
        keyboard.row(
            types.InlineKeyboardButton("🔙 Menu Chính", callback_data="cmd_menu")
        )
        
        return keyboard
    
    def send_photo(self, chat_id=None, photo_bytes=None, caption='', parse_mode='HTML', reply_markup=None):
        """
        Send a photo
        
        Args:
            chat_id: Chat ID (optional, uses default if not provided)
            photo_bytes: Bytes of image data
            caption: Optional caption (max 1024 chars to avoid HTTP 431)
            parse_mode: Parse mode for caption ('HTML' or 'Markdown')
            reply_markup: Optional inline keyboard
        """
        try:
            # Use default chat_id if not provided (backward compatibility)
            if chat_id is None:
                chat_id = self.chat_id
            
            # Truncate caption to avoid HTTP 431 (Request Header Too Large)
            # Telegram's limit is 1024 characters for photo captions
            max_caption_length = 1000  # Leave some buffer
            if len(caption) > max_caption_length:
                logger.warning(f"Caption too long ({len(caption)} chars), truncating to {max_caption_length}")
                caption = caption[:max_caption_length-3] + "..."
            
            sent = False
            retries = 0
            while not sent and retries < 3:
                try:
                    self.bot.send_photo(
                        chat_id=chat_id,
                        photo=photo_bytes,
                        caption=caption,
                        parse_mode=parse_mode,
                        reply_markup=reply_markup
                    )
                    logger.info("Photo sent successfully")
                    sent = True
                except Exception as e:
                    err = str(e)
                    if 'Too Many Requests' in err or '429' in err:
                        m = re.search(r'retry after (\d+)', err)
                        wait = int(m.group(1)) if m else 30
                        retries += 1
                        logger.warning(f"Rate limited by Telegram (photo), retrying after {wait}s (attempt {retries})")
                        time.sleep(wait + 1)
                        continue
                    elif 'Request Header Fields Too Large' in err or '431' in err:
                        # Caption too long, truncate further and retry
                        logger.warning(f"HTTP 431 error, caption still too long. Truncating to 500 chars")
                        caption = caption[:497] + "..."
                        retries += 1
                        continue
                    else:
                        logger.error(f"Error sending photo: {e}")
                        break
            return sent
        except Exception as e:
            logger.error(f"Error sending photo: {e}")
            return False
    
    def send_signal_alert(self, symbol, timeframe_data, consensus, consensus_strength, price=None, market_data=None, volume_data=None, stoch_rsi_data=None, chat_id=None):
        """
        Send a formatted signal alert with detailed information in Vietnamese
        
        Args:
            symbol: Trading symbol
            timeframe_data: Dictionary of timeframe analysis
            consensus: Overall consensus (BUY/SELL/NEUTRAL)
            consensus_strength: Strength of consensus (0-4)
            price: Current price (optional)
            market_data: Dictionary with 24h data (high, low, change, volume)
            volume_data: Dictionary with volume analysis (current, last, avg, ratios)
            stoch_rsi_data: Dictionary with Stoch+RSI analysis (optional)
            chat_id: Chat ID to send to (if None, uses default)
        """
        try:
            # Use Vietnamese message generator
            message = get_signal_alert(symbol, timeframe_data, consensus, consensus_strength, price, market_data, volume_data, stoch_rsi_data)
            
            # Determine chat type
            target_chat_id = chat_id if chat_id else self.chat_id
            
            # Check if it's the group chat
            is_group = str(target_chat_id) == str(config.GROUP_CHAT_ID) if hasattr(config, 'GROUP_CHAT_ID') else False
            
            # Create keyboard based on chat type
            keyboard = None
            if not is_group:
                # Private chat: Full buttons with WebApp
                keyboard = self.create_symbol_analysis_keyboard(symbol)
            else:
                # Group chat: Add button to open Live Chart in private chat with bot
                keyboard = self.create_group_chart_keyboard(symbol)
                logger.info(f"📢 Sending to group {target_chat_id} - Using group keyboard with t.me link")
            
            logger.info(f"✅ Đang gửi cảnh báo tín hiệu cho {symbol}")
            result = self.send_message(message, reply_markup=keyboard, chat_id=target_chat_id)
            
            if result:
                logger.info(f"✅ Đã gửi cảnh báo tín hiệu cho {symbol}")
            else:
                logger.error(f"❌ Gửi cảnh báo thất bại cho {symbol}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Lỗi gửi cảnh báo cho {symbol}: {e}")
            try:
                self.send_message(f"❌ <b>Lỗi gửi cảnh báo cho {symbol}</b>\n\n{str(e)}")
            except:
                pass
            return False
            
            # Escape HTML in symbol name to prevent parsing errors
            safe_symbol = html_module.escape(symbol)
            
            # Get current time
            current_time = datetime.now().strftime('%H:%M:%S')
            
            # Header with symbol
            message = f"<b>💎 #{safe_symbol}</b>\n"
            message += f"🕐 {current_time}\n\n"
            
            # Get timeframe list (sorted)
            timeframes = sorted(timeframe_data.keys(), 
                              key=lambda x: {'5m': 1, '1h': 2, '4h': 3, '1d': 4}.get(x, 5))
            
            # RSI Analysis
            message += "\n<b>📊 RSI ANALYSIS</b>\n"
            
            # Find main timeframe (usually first or most important)
            main_tf = timeframes[0] if timeframes else '5m'
            main_rsi = timeframe_data[main_tf]['rsi']
            last_rsi = timeframe_data[main_tf].get('last_rsi', main_rsi)
            rsi_change = timeframe_data[main_tf].get('rsi_change', 0)
            
            # RSI status emoji
            if main_rsi >= 80:
                rsi_status = "🔥"
                rsi_alert = f"⚠️ Overbought Alert: {main_rsi:.0f}+ 🔴🔴"
            elif main_rsi <= 20:
                rsi_status = "❄️"
                rsi_alert = f"💎 Oversold Alert: {main_rsi:.0f}- 🟢🟢"
            else:
                rsi_status = "⚖️"
                rsi_alert = None
            
            # RSI trend indicator
            rsi_trend = "📈" if rsi_change > 0 else ("📉" if rsi_change < 0 else "➡️")
            
            message += f"📍 <b>Main RSI:</b> {main_rsi:.2f} {rsi_status}\n"
            message += f"⏮️ <b>Last RSI:</b> {last_rsi:.2f} {rsi_trend} <i>({rsi_change:+.2f})</i>\n"
            if rsi_alert:
                message += f"{rsi_alert}\n\n"
            else:
                message += "\n"
            
            # All timeframe RSI values
            for tf in timeframes:
                rsi_val = timeframe_data[tf]['rsi']
                last_val = timeframe_data[tf].get('last_rsi', rsi_val)
                change = timeframe_data[tf].get('rsi_change', 0)
                
                if rsi_val >= 80:
                    emoji = "🔴"
                    status = "Overbought"
                elif rsi_val <= 20:
                    emoji = "🟢"
                    status = "Oversold"
                else:
                    emoji = "🔵"
                    status = "Normal"
                
                trend = "↗" if change > 0 else ("↘" if change < 0 else "→")
                message += f"  ├─ {tf.upper()}: {rsi_val:.2f} {emoji} <i>{status}</i> {trend}\n"
            
            # MFI Analysis
            message += "\n<b>💰 MFI ANALYSIS</b>\n"
            main_mfi = timeframe_data[main_tf]['mfi']
            last_mfi = timeframe_data[main_tf].get('last_mfi', main_mfi)
            mfi_change = timeframe_data[main_tf].get('mfi_change', 0)
            
            # MFI status emoji
            if main_mfi >= 80:
                mfi_status = "🔥"
                mfi_alert = f"⚠️ Overbought Alert: {main_mfi:.0f}+ 🔴🔴"
            elif main_mfi <= 20:
                mfi_status = "❄️"
                mfi_alert = f"💎 Oversold Alert: {main_mfi:.0f}- 🟢🟢"
            else:
                mfi_status = "⚖️"
                mfi_alert = None
            
            # MFI trend indicator
            mfi_trend = "📈" if mfi_change > 0 else ("📉" if mfi_change < 0 else "➡️")
            
            message += f"📍 <b>Main MFI:</b> {main_mfi:.2f} {mfi_status}\n"
            message += f"⏮️ <b>Last MFI:</b> {last_mfi:.2f} {mfi_trend} <i>({mfi_change:+.2f})</i>\n"
            if mfi_alert:
                message += f"{mfi_alert}\n\n"
            else:
                message += "\n"
            
            # All timeframe MFI values
            for tf in timeframes:
                mfi_val = timeframe_data[tf]['mfi']
                last_val = timeframe_data[tf].get('last_mfi', mfi_val)
                change = timeframe_data[tf].get('mfi_change', 0)
                
                if mfi_val >= 80:
                    emoji = "🔴"
                    status = "Overbought"
                elif mfi_val <= 20:
                    emoji = "🟢"
                    status = "Oversold"
                else:
                    emoji = "🔵"
                    status = "Normal"
                
                trend = "↗" if change > 0 else ("↘" if change < 0 else "→")
                message += f"  ├─ {tf.upper()}: {mfi_val:.2f} {emoji} <i>{status}</i> {trend}\n"
            
            # Consensus Analysis
            message += "\n<b>🎯 CONSENSUS SIGNALS</b>\n"
            for tf in timeframes:
                data = timeframe_data[tf]
                avg = (data['rsi'] + data['mfi']) / 2
                
                if data['signal'] == 1:
                    signal_text = "🟢 BUY"
                    arrow = "📈"
                elif data['signal'] == -1:
                    signal_text = "🔴 SELL"
                    arrow = "📉"
                else:
                    signal_text = "⚪ NEUTRAL"
                    arrow = "➡️"
                
                message += f"  {arrow} {tf.upper()}: {avg:.1f} → {signal_text}\n"
            
            # Overall consensus
            if consensus == "BUY":
                consensus_icon = "🚀"
                consensus_bar = "🟩" * consensus_strength + "⬜" * (4 - consensus_strength)
            elif consensus == "SELL":
                consensus_icon = "⚠️"
                consensus_bar = "🟥" * consensus_strength + "⬜" * (4 - consensus_strength)
            else:
                consensus_icon = "💤"
                consensus_bar = "⬜" * 4
            
            message += f"\n<b>{consensus_icon} OVERALL: {consensus}</b>\n"
            message += f"<b>Strength: {consensus_bar} ({consensus_strength}/4)</b>\n"
            
            # Price Information
            message += "\n<b>💵 PRICE INFO</b>\n"
            if price:
                message += f"💲 Current: <b>${price:,.4f}</b>\n"
            
            # 24h Market Data
            if market_data:
                change_24h = market_data.get('price_change_percent', 0)
                volume_24h = market_data.get('volume', 0)
                high_24h = market_data.get('high', 0)
                low_24h = market_data.get('low', 0)
                
                # Format volume intelligently
                if volume_24h >= 1e9:  # Billions
                    vol_str = f"${volume_24h/1e9:.2f}B"
                elif volume_24h >= 1e6:  # Millions
                    vol_str = f"${volume_24h/1e6:.2f}M"
                elif volume_24h >= 1e3:  # Thousands
                    vol_str = f"${volume_24h/1e3:.2f}K"
                else:
                    vol_str = f"${volume_24h:.2f}"
                
                change_emoji = "📈" if change_24h >= 0 else "📉"
                change_color = "🟩" if change_24h >= 0 else "🟥"
                message += f"\n📊 <b>24h Change:</b> {change_emoji} {change_color} <b>{change_24h:+.2f}%</b>\n"
                message += f"💎 <b>Volume:</b> {vol_str}\n"
                
                if price and high_24h > 0:
                    high_diff = ((high_24h - price) / price) * 100
                    message += f"🔺 <b>High:</b> ${high_24h:,.4f} <i>(+{high_diff:.2f}%)</i>\n"
                
                if price and low_24h > 0:
                    low_diff = ((price - low_24h) / price) * 100
                    message += f"🔻 <b>Low:</b> ${low_24h:,.4f} <i>(+{low_diff:.2f}%)</i>\n"
            
            # Volume Analysis (if available)
            if volume_data:
                current_vol = volume_data.get('current_volume', 0)
                last_vol = volume_data.get('last_volume', 0)
                avg_vol = volume_data.get('avg_volume', 0)
                is_anomaly = volume_data.get('is_anomaly', False)
                
                # Get 24h volume for comparison
                volume_24h = market_data.get('volume', 0) if market_data else 0
                
                # Format volumes intelligently
                def format_volume(vol):
                    if vol >= 1e9:
                        return f"{vol/1e9:.2f}B"
                    elif vol >= 1e6:
                        return f"{vol/1e6:.2f}M"
                    elif vol >= 1e3:
                        return f"{vol/1e3:.2f}K"
                    else:
                        return f"{vol:.2f}"
                
                message += f"\n<b>📊 PHÂN TÍCH VOLUME</b>\n"
                
                # Show anomaly warning if detected
                if is_anomaly:
                    message += f"⚡ <b>PHÁT HIỆN TĂNG ĐỘT BIẾN VOLUME!</b> ⚡\n"
                
                message += f"💹 <b>Nến Hiện Tại:</b> {format_volume(current_vol)}\n"
                message += f"⏮️ <b>Nến Trước:</b> {format_volume(last_vol)}\n"
                message += f"📊 <b>Nến Trung Bình:</b> {format_volume(avg_vol)}\n"
                
                # Show ratios
                if last_vol > 0:
                    last_ratio = volume_data.get('last_candle_ratio', 0)
                    last_increase = volume_data.get('last_candle_increase_percent', 0)
                    ratio_emoji = "📈" if last_ratio > 1 else ("📉" if last_ratio < 1 else "➡️")
                    message += f"🔄 <b>so với Trước:</b> {last_ratio:.2f}x {ratio_emoji} <i>({last_increase:+.1f}%)</i>\n"
                
                if avg_vol > 0:
                    avg_ratio = volume_data.get('avg_ratio', 0)
                    avg_increase = volume_data.get('avg_increase_percent', 0)
                    avg_emoji = "📈" if avg_ratio > 1 else ("📉" if avg_ratio < 1 else "➡️")
                    message += f"🔄 <b>so với TB:</b> {avg_ratio:.2f}x {avg_emoji} <i>({avg_increase:+.1f}%)</i>\n"
                
                # 24h Volume Impact Analysis
                if volume_24h > 0 and current_vol > 0:
                    # Calculate contribution percentage
                    contribution_pct = (current_vol / volume_24h) * 100
                    
                    # Smart formatting for contribution percentage
                    if contribution_pct >= 0.001:
                        contribution_str = f"{contribution_pct:.3f}%"
                    elif contribution_pct >= 0.00001:
                        contribution_str = f"{contribution_pct:.5f}%"
                    else:
                        # Use scientific notation for very small values
                        contribution_str = f"{contribution_pct:.2e}%"
                    
                    # Calculate trend (current vs last)
                    if last_vol > 0:
                        vol_change = current_vol - last_vol
                        vol_change_pct = ((current_vol - last_vol) / last_vol) * 100
                        
                        # Predict 24h impact if trend continues
                        # Assume 288 candles per day (5-min timeframe)
                        candles_per_day = 288
                        predicted_impact = vol_change * candles_per_day
                        predicted_impact_pct = (predicted_impact / volume_24h) * 100
                        
                        # Determine trend
                        if vol_change > 0:
                            trend_emoji = "🔥"
                            trend_text = "Increasing"
                            impact_sign = "+"
                        elif vol_change < 0:
                            trend_emoji = "❄️"
                            trend_text = "Decreasing"
                            impact_sign = ""
                        else:
                            trend_emoji = "➡️"
                            trend_text = "Stable"
                            impact_sign = ""
                        
                        message += f"\n<b>📈 24h IMPACT ANALYSIS</b>\n"
                        message += f"💎 <b>Current 24h Volume:</b> {format_volume(volume_24h)}\n"
                        message += f"📊 <b>Candle Contribution:</b> {contribution_str} of 24h\n"
                        message += f"{trend_emoji} <b>Trend:</b> {trend_text} <i>({vol_change_pct:+.1f}%)</i>\n"
                        
                        if abs(predicted_impact_pct) > 0.1:  # Only show if significant
                            message += f"🔮 <b>Projected 24h Impact:</b> {impact_sign}{format_volume(abs(predicted_impact))} <i>({predicted_impact_pct:+.1f}%)</i>\n"
            
            # Add inline keyboard for quick actions: View Chart, Add to Watchlist
            keyboard = types.InlineKeyboardMarkup(row_width=2)
            # Button to request chart for this symbol
            # Use uppercase raw symbol for callback data to keep it URL-safe
            keyboard.add(types.InlineKeyboardButton("📈 View Chart", callback_data=f"viewchart_{symbol.upper()}"))
            # Button to add the symbol to the user's watchlist
            keyboard.add(types.InlineKeyboardButton("⭐ Add to Watchlist", callback_data=f"addwatch_{symbol.upper()}"))
            # Also add a back to main menu button
            keyboard.add(types.InlineKeyboardButton("🔙 Main Menu", callback_data="cmd_menu"))
            logger.info(f"✅ Sending signal alert for {symbol} ({len(message)} chars)")
            result = self.send_message(message, reply_markup=keyboard)
            if result:
                logger.info(f"✅ Signal alert sent successfully for {symbol}")
            else:
                logger.error(f"❌ Failed to send signal alert for {symbol}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error building/sending signal alert for {symbol}: {e}")
            logger.exception(e)  # Print full traceback
            # Send a basic error message
            try:
                self.send_message(f"❌ <b>Error sending alert for {symbol}</b>\n\n{str(e)}")
            except:
                pass
            return False    
    def send_summary_table(self, signals_list):
        """
        Send a summary table of multiple signals
        Split into multiple messages if needed to avoid Telegram 4096 char limit
        Only show signals that have signals in 1H, 4H, or 1D timeframes (ignore 5M only)
        
        Args:
            signals_list: List of signal dictionaries
        """
        try:
            logger.info(f"📤 Building summary table for {len(signals_list) if signals_list else 0} signals")
            
            if not signals_list:
                logger.warning("No signals to display in summary")
                return self.send_message("💤 No signals detected at this time.")
            
            # Filter signals: Only show if has signal in 1H, 4H, or 1D (ignore 5M only signals)
            IMPORTANT_TIMEFRAMES = ['1h', '4h', '1d']
            
            def has_important_timeframe_signal(signal):
                """Check if signal has BUY/SELL in important timeframes"""
                if 'timeframe_data' not in signal:
                    return False
                
                consensus = signal.get('consensus')
                if consensus not in ['BUY', 'SELL']:
                    return False
                
                # Check if any important timeframe has the same signal
                for tf in IMPORTANT_TIMEFRAMES:
                    if tf in signal['timeframe_data']:
                        tf_signal = signal['timeframe_data'][tf].get('signal', 0)
                        # BUY = 1, SELL = -1
                        if consensus == 'BUY' and tf_signal == 1:
                            return True
                        elif consensus == 'SELL' and tf_signal == -1:
                            return True
                
                return False
            
            # Filter signals
            original_count = len(signals_list)
            signals_list = [s for s in signals_list if has_important_timeframe_signal(s)]
            filtered_count = original_count - len(signals_list)
            
            logger.info(f"Filtered {filtered_count} signals (5M only), remaining: {len(signals_list)}")
            
            if not signals_list:
                return self.send_message("💤 No signals in important timeframes (1H, 4H, 1D).")
            
            # Sort by consensus strength
            signals_list = sorted(signals_list, key=lambda x: x.get('consensus_strength', 0), reverse=True)
            
            buy_signals = [s for s in signals_list if s.get('consensus') == 'BUY']
            sell_signals = [s for s in signals_list if s.get('consensus') == 'SELL']
            
            logger.info(f"Summary: {len(buy_signals)} BUY, {len(sell_signals)} SELL signals (important timeframes only)")
            
            # Telegram limit is 4096 chars, leave some margin
            MAX_MESSAGE_LENGTH = 3800
            
            messages = []
            
            # Build header
            header = f"<b>📊 MARKET SCAN SUMMARY</b>\n"
            header += f"<i>⏱️ Showing signals in 1H, 4H, 1D only</i>\n\n"
            header += f"<b>📈 Total Signals:</b> {len(signals_list)}\n"
            header += f"   🟢 Buy: {len(buy_signals)} | 🔴 Sell: {len(sell_signals)}\n"
            if filtered_count > 0:
                header += f"   <i>🔕 Filtered: {filtered_count} (5M only)</i>\n"
            header += f"🕐 <i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>\n\n"
            
            # Build BUY signals (split if needed)
            if buy_signals:
                current_msg = header + f"<b>🚀 BUY SIGNALS: ({len(buy_signals)})</b>\n"
                buy_msg_count = 1
                
                for i, signal in enumerate(buy_signals, 1):
                    strength_bar = "🟩" * signal.get('consensus_strength', 0) + "⬜" * (4 - signal.get('consensus_strength', 0))
                    
                    # Get timeframes with BUY signals (only important ones: 1H, 4H, 1D)
                    buy_timeframes = []
                    if 'timeframe_data' in signal:
                        for tf, data in signal['timeframe_data'].items():
                            if tf in IMPORTANT_TIMEFRAMES and data.get('signal') == 1:
                                buy_timeframes.append(tf.upper())
                    
                    # Sort timeframes: 1H, 4H, 1D
                    timeframe_order = {'1H': 1, '4H': 2, '1D': 3}
                    buy_timeframes.sort(key=lambda x: timeframe_order.get(x, 99))
                    
                    timeframes_str = ", ".join(buy_timeframes) if buy_timeframes else "N/A"
                    
                    signal_text = f"  ✅ <b>{signal.get('symbol', 'UNKNOWN')}</b>\n"
                    signal_text += f"     {strength_bar} {signal.get('consensus_strength', 0)}/4\n"
                    signal_text += f"     <i>📊 {timeframes_str}</i>\n"
                    
                    # Check if adding this signal exceeds limit
                    if len(current_msg) + len(signal_text) > MAX_MESSAGE_LENGTH:
                        # Send current message and start new one
                        messages.append(current_msg)
                        buy_msg_count += 1
                        current_msg = f"<b>🚀 BUY SIGNALS (Part {buy_msg_count}):</b>\n"
                    
                    current_msg += signal_text
                
                # Add remaining BUY signals message
                messages.append(current_msg + "\n")
            
            # Build SELL signals (split if needed)
            if sell_signals:
                current_msg = f"<b>⚠️ SELL SIGNALS: ({len(sell_signals)})</b>\n"
                sell_msg_count = 1
                
                for i, signal in enumerate(sell_signals, 1):
                    strength_bar = "🟥" * signal.get('consensus_strength', 0) + "⬜" * (4 - signal.get('consensus_strength', 0))
                    
                    # Get timeframes with SELL signals (only important ones: 1H, 4H, 1D)
                    sell_timeframes = []
                    if 'timeframe_data' in signal:
                        for tf, data in signal['timeframe_data'].items():
                            if tf in IMPORTANT_TIMEFRAMES and data.get('signal') == -1:
                                sell_timeframes.append(tf.upper())
                    
                    # Sort timeframes: 1H, 4H, 1D
                    timeframe_order = {'1H': 1, '4H': 2, '1D': 3}
                    sell_timeframes.sort(key=lambda x: timeframe_order.get(x, 99))
                    
                    timeframes_str = ", ".join(sell_timeframes) if sell_timeframes else "N/A"
                    
                    signal_text = f"  ⛔ <b>{signal.get('symbol', 'UNKNOWN')}</b>\n"
                    signal_text += f"     {strength_bar} {signal.get('consensus_strength', 0)}/4\n"
                    signal_text += f"     <i>📊 {timeframes_str}</i>\n"
                    
                    # Check if adding this signal exceeds limit
                    if len(current_msg) + len(signal_text) > MAX_MESSAGE_LENGTH:
                        # Send current message and start new one
                        messages.append(current_msg)
                        sell_msg_count += 1
                        current_msg = f"<b>⚠️ SELL SIGNALS (Part {sell_msg_count}):</b>\n"
                    
                    current_msg += signal_text
                
                # Add remaining SELL signals message
                messages.append(current_msg)
            
            # Send all messages
            logger.info(f"✅ Sending {len(messages)} summary message(s)")
            success = True
            
            for i, msg in enumerate(messages, 1):
                logger.info(f"Sending summary part {i}/{len(messages)} ({len(msg)} chars)")
                if not self.send_message(msg):
                    logger.error(f"❌ Failed to send summary part {i}/{len(messages)}")
                    success = False
                else:
                    logger.info(f"✅ Summary part {i}/{len(messages)} sent successfully")
                
                # Small delay between messages
                if i < len(messages):
                    time.sleep(0.5)
            
            if success:
                logger.info("✅ All summary messages sent successfully")
            else:
                logger.error("❌ Some summary messages failed to send")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error building summary table: {e}")
            logger.exception(e)
            try:
                self.send_message(f"❌ <b>Error building summary table</b>\n\n{str(e)}")
            except:
                pass
            return False
    
    def test_connection(self):
        """Test Telegram bot connection"""
        try:
            me = self.bot.get_me()
            logger.info(f"Telegram bot connected: @{me.username}")
            return True
        except Exception as e:
            logger.error(f"Telegram bot connection failed: {e}")
            return False

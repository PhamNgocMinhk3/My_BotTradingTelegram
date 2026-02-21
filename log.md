2026-02-21 04:51:35,960 - binance_client - INFO - DEBUG: Cache MISS for USD1USDT 5m limit=100. Calling API...
2026-02-21 04:51:36,191 - binance_client - INFO - DEBUG: API returned 100 klines for USD1USDT 5m (requested 100)
2026-02-21 04:51:36,201 - bot_detector - INFO - Bot detection for USD1USDT: Bot Score=93.0%, Pump Score=0.0%
2026-02-21 04:51:36,201 - bot_detector - WARNING - ⚠️ USD1USDT: Detected BOT types: spoofing, market_maker
2026-02-21 04:51:36,201 - binance_client - INFO - DEBUG: Cache MISS for USD1USDT 5m limit=200. Calling API...
2026-02-21 04:51:36,435 - binance_client - INFO - DEBUG: API returned 200 klines for USD1USDT 5m (requested 200)
/app/advanced_pump_detector.py:323: SettingWithCopyWarning: 
A value is trying to be set on a copy of a slice from a DataFrame.
Try using .loc[row_indexer,col_indexer] = value instead
See the caveats in the documentation: https://pandas.pydata.org/pandas-docs/stable/user_guide/indexing.html#returning-a-view-versus-a-copy
  recent['vwap'] = (recent['volume'] * (recent['high'] + recent['low'] + recent['close']) / 3).cumsum() / recent['volume'].cumsum()
2026-02-21 04:51:37,134 - advanced_pump_detector - INFO - 📊 USD1USDT: Signal=NEUTRAL, Confidence=35%, Risk=MEDIUM
2026-02-21 04:51:37,134 - binance_client - INFO - DEBUG: Cache MISS for LINKUSDT 1h limit=24. Calling API...
2026-02-21 04:51:37,356 - binance_client - INFO - DEBUG: API returned 24 klines for LINKUSDT 1h (requested 24)
2026-02-21 04:51:37,359 - binance_client - INFO - DEBUG: Cache MISS for LINKUSDT 4h limit=24. Calling API...
2026-02-21 04:51:37,586 - binance_client - INFO - DEBUG: API returned 24 klines for LINKUSDT 4h (requested 24)
2026-02-21 04:51:38,516 - binance_client - INFO - DEBUG: Cache MISS for LINKUSDT 5m limit=100. Calling API...
2026-02-21 04:51:38,747 - binance_client - INFO - DEBUG: API returned 100 klines for LINKUSDT 5m (requested 100)
2026-02-21 04:51:38,756 - bot_detector - INFO - Bot detection for LINKUSDT: Bot Score=35.0%, Pump Score=20.0%
2026-02-21 04:51:38,756 - bot_detector - WARNING - ⚠️ LINKUSDT: Detected BOT types: spoofing
2026-02-21 04:51:38,757 - binance_client - INFO - DEBUG: Cache MISS for LINKUSDT 5m limit=200. Calling API...
2026-02-21 04:51:38,991 - binance_client - INFO - DEBUG: API returned 200 klines for LINKUSDT 5m (requested 200)
/app/advanced_pump_detector.py:323: SettingWithCopyWarning: 
A value is trying to be set on a copy of a slice from a DataFrame.
Try using .loc[row_indexer,col_indexer] = value instead
See the caveats in the documentation: https://pandas.pydata.org/pandas-docs/stable/user_guide/indexing.html#returning-a-view-versus-a-copy
  recent['vwap'] = (recent['volume'] * (recent['high'] + recent['low'] + recent['close']) / 3).cumsum() / recent['volume'].cumsum()
2026-02-21 04:51:39,940 - advanced_pump_detector - INFO - 📊 LINKUSDT: Signal=NEUTRAL, Confidence=89%, Risk=LOW
2026-02-21 04:51:39,940 - pump_detector_realtime - INFO - 🐋 LINKUSDT: Institutional accumulation detected
2026-02-21 04:51:39,940 - binance_client - INFO - DEBUG: Cache MISS for EURUSDT 1h limit=24. Calling API...
2026-02-21 04:51:40,168 - binance_client - INFO - DEBUG: API returned 24 klines for EURUSDT 1h (requested 24)
2026-02-21 04:51:40,171 - binance_client - INFO - DEBUG: Cache MISS for EURUSDT 4h limit=24. Calling API...
2026-02-21 04:51:40,398 - binance_client - INFO - DEBUG: API returned 24 klines for EURUSDT 4h (requested 24)
2026-02-21 04:51:41,779 - binance_client - INFO - DEBUG: Cache MISS for EURUSDT 5m limit=200. Calling API...
2026-02-21 04:51:41,538 - binance_client - INFO - DEBUG: Cache MISS for EURUSDT 5m limit=100. Calling API...
2026-02-21 04:51:41,769 - binance_client - INFO - DEBUG: API returned 100 klines for EURUSDT 5m (requested 100)
2026-02-21 04:51:41,779 - bot_detector - INFO - Bot detection for EURUSDT: Bot Score=53.0%, Pump Score=0.0%
2026-02-21 04:51:41,779 - bot_detector - WARNING - ⚠️ EURUSDT: Detected BOT types: spoofing, market_maker
2026-02-21 04:51:42,009 - binance_client - INFO - DEBUG: API returned 200 klines for EURUSDT 5m (requested 200)
/app/advanced_pump_detector.py:323: SettingWithCopyWarning: 
A value is trying to be set on a copy of a slice from a DataFrame.
Try using .loc[row_indexer,col_indexer] = value instead
See the caveats in the documentation: https://pandas.pydata.org/pandas-docs/stable/user_guide/indexing.html#returning-a-view-versus-a-copy
  recent['vwap'] = (recent['volume'] * (recent['high'] + recent['low'] + recent['close']) / 3).cumsum() / recent['volume'].cumsum()
2026-02-21 04:51:42,709 - advanced_pump_detector - INFO - 📊 EURUSDT: Signal=NEUTRAL, Confidence=65%, Risk=LOW
2026-02-21 04:51:42,709 - binance_client - INFO - DEBUG: Cache MISS for SHIBUSDT 1h limit=24. Calling API...
2026-02-21 04:51:42,931 - binance_client - INFO - DEBUG: API returned 24 klines for SHIBUSDT 1h (requested 24)
2026-02-21 04:51:42,934 - binance_client - INFO - DEBUG: Cache MISS for SHIBUSDT 4h limit=24. Calling API...
2026-02-21 04:51:43,165 - binance_client - INFO - DEBUG: API returned 24 klines for SHIBUSDT 4h (requested 24)
2026-02-21 04:51:44,094 - binance_client - INFO - DEBUG: Cache MISS for SHIBUSDT 5m limit=100. Calling API...
2026-02-21 04:51:44,319 - binance_client - INFO - DEBUG: API returned 100 klines for SHIBUSDT 5m (requested 100)
2026-02-21 04:51:44,330 - bot_detector - INFO - Bot detection for SHIBUSDT: Bot Score=65.0%, Pump Score=0.0%
2026-02-21 04:51:44,330 - bot_detector - WARNING - ⚠️ SHIBUSDT: Detected BOT types: spoofing
2026-02-21 04:51:44,331 - binance_client - INFO - DEBUG: Cache MISS for SHIBUSDT 5m limit=200. Calling API...
2026-02-21 04:51:44,555 - binance_client - INFO - DEBUG: API returned 200 klines for SHIBUSDT 5m (requested 200)
/app/advanced_pump_detector.py:323: SettingWithCopyWarning: 
A value is trying to be set on a copy of a slice from a DataFrame.
Try using .loc[row_indexer,col_indexer] = value instead
See the caveats in the documentation: https://pandas.pydata.org/pandas-docs/stable/user_guide/indexing.html#returning-a-view-versus-a-copy
  recent['vwap'] = (recent['volume'] * (recent['high'] + recent['low'] + recent['close']) / 3).cumsum() / recent['volume'].cumsum()
2026-02-21 04:51:45,513 - advanced_pump_detector - INFO - 📊 SHIBUSDT: Signal=NEUTRAL, Confidence=91%, Risk=LOW
2026-02-21 04:51:45,513 - pump_detector_realtime - INFO - 🐋 SHIBUSDT: Institutional accumulation detected
2026-02-21 04:51:45,514 - binance_client - INFO - DEBUG: Cache MISS for HBARUSDT 1h limit=24. Calling API...
2026-02-21 04:51:45,741 - binance_client - INFO - DEBUG: API returned 24 klines for HBARUSDT 1h (requested 24)
2026-02-21 04:51:45,745 - binance_client - INFO - DEBUG: Cache MISS for HBARUSDT 4h limit=24. Calling API...
2026-02-21 04:51:45,976 - binance_client - INFO - DEBUG: API returned 24 klines for HBARUSDT 4h (requested 24)
2026-02-21 04:51:47,011 - binance_client - INFO - DEBUG: Cache MISS for HBARUSDT 5m limit=100. Calling API...
2026-02-21 04:51:47,238 - binance_client - INFO - DEBUG: API returned 100 klines for HBARUSDT 5m (requested 100)
2026-02-21 04:51:47,248 - bot_detector - INFO - Bot detection for HBARUSDT: Bot Score=63.0%, Pump Score=0.0%
2026-02-21 04:51:47,249 - bot_detector - WARNING - ⚠️ HBARUSDT: Detected BOT types: spoofing, market_maker
2026-02-21 04:51:47,249 - binance_client - INFO - DEBUG: Cache MISS for HBARUSDT 5m limit=200. Calling API...
2026-02-21 04:51:47,474 - binance_client - INFO - DEBUG: API returned 200 klines for HBARUSDT 5m (requested 200)
/app/advanced_pump_detector.py:323: SettingWithCopyWarning: 
A value is trying to be set on a copy of a slice from a DataFrame.
Try using .loc[row_indexer,col_indexer] = value instead
See the caveats in the documentation: https://pandas.pydata.org/pandas-docs/stable/user_guide/indexing.html#returning-a-view-versus-a-copy
  recent['vwap'] = (recent['volume'] * (recent['high'] + recent['low'] + recent['close']) / 3).cumsum() / recent['volume'].cumsum()
2026-02-21 04:51:48,427 - advanced_pump_detector - INFO - 📊 HBARUSDT: Signal=NEUTRAL, Confidence=85%, Risk=LOW
2026-02-21 04:51:48,427 - pump_detector_realtime - INFO - 🐋 HBARUSDT: Institutional accumulation detected
2026-02-21 04:51:48,427 - binance_client - INFO - DEBUG: Cache MISS for XUSDUSDT 1h limit=24. Calling API...
2026-02-21 04:51:48,657 - binance_client - INFO - DEBUG: API returned 24 klines for XUSDUSDT 1h (requested 24)
2026-02-21 04:51:48,660 - binance_client - INFO - DEBUG: Cache MISS for XUSDUSDT 4h limit=24. Calling API...
2026-02-21 04:51:48,890 - binance_client - INFO - DEBUG: API returned 24 klines for XUSDUSDT 4h (requested 24)
2026-02-21 04:51:49,812 - binance_client - INFO - DEBUG: Cache MISS for XUSDUSDT 5m limit=100. Calling API...
2026-02-21 04:51:50,042 - binance_client - INFO - DEBUG: API returned 100 klines for XUSDUSDT 5m (requested 100)
2026-02-21 04:51:50,053 - bot_detector - INFO - Bot detection for XUSDUSDT: Bot Score=38.0%, Pump Score=0.0%
2026-02-21 04:51:50,053 - bot_detector - WARNING - ⚠️ XUSDUSDT: Detected BOT types: market_maker
2026-02-21 04:51:50,054 - binance_client - INFO - DEBUG: Cache MISS for XUSDUSDT 5m limit=200. Calling API...
2026-02-21 04:51:50,279 - binance_client - INFO - DEBUG: API returned 200 klines for XUSDUSDT 5m (requested 200)
/app/advanced_pump_detector.py:323: SettingWithCopyWarning: 
A value is trying to be set on a copy of a slice from a DataFrame.
Try using .loc[row_indexer,col_indexer] = value instead
See the caveats in the documentation: https://pandas.pydata.org/pandas-docs/stable/user_guide/indexing.html#returning-a-view-versus-a-copy
  recent['vwap'] = (recent['volume'] * (recent['high'] + recent['low'] + recent['close']) / 3).cumsum() / recent['volume'].cumsum()
2026-02-21 04:51:51,241 - advanced_pump_detector - INFO - 📊 XUSDUSDT: Signal=NEUTRAL, Confidence=65%, Risk=LOW
2026-02-21 04:51:51,241 - pump_detector_realtime - INFO - 🐋 XUSDUSDT: Institutional accumulation detected
2026-02-21 04:51:51,241 - binance_client - INFO - DEBUG: Cache MISS for YGGUSDT 1h limit=24. Calling API...
2026-02-21 04:51:52,125 - binance_client - INFO - DEBUG: API returned 24 klines for YGGUSDT 1h (requested 24)
2026-02-21 04:51:52,128 - binance_client - INFO - DEBUG: Cache MISS for YGGUSDT 4h limit=24. Calling API...
2026-02-21 04:51:52,802 - binance_client - INFO - DEBUG: API returned 24 klines for YGGUSDT 4h (requested 24)
2026-02-21 04:51:55,247 - binance_client - INFO - DEBUG: Cache MISS for YGGUSDT 5m limit=100. Calling API...
2026-02-21 04:51:55,478 - binance_client - INFO - DEBUG: API returned 100 klines for YGGUSDT 5m (requested 100)
2026-02-21 04:51:55,487 - bot_detector - INFO - Bot detection for YGGUSDT: Bot Score=35.0%, Pump Score=30.0%
2026-02-21 04:51:55,487 - bot_detector - WARNING - ⚠️ YGGUSDT: Detected BOT types: spoofing
2026-02-21 04:51:55,488 - binance_client - INFO - DEBUG: Cache MISS for YGGUSDT 5m limit=200. Calling API...
2026-02-21 04:51:56,160 - binance_client - INFO - DEBUG: API returned 200 klines for YGGUSDT 5m (requested 200)
/app/advanced_pump_detector.py:323: SettingWithCopyWarning: 
A value is trying to be set on a copy of a slice from a DataFrame.
Try using .loc[row_indexer,col_indexer] = value instead
See the caveats in the documentation: https://pandas.pydata.org/pandas-docs/stable/user_guide/indexing.html#returning-a-view-versus-a-copy
  recent['vwap'] = (recent['volume'] * (recent['high'] + recent['low'] + recent['close']) / 3).cumsum() / recent['volume'].cumsum()
2026-02-21 04:51:56,857 - advanced_pump_detector - INFO - 📊 YGGUSDT: Signal=NEUTRAL, Confidence=56%, Risk=LOW
2026-02-21 04:51:56,857 - binance_client - INFO - DEBUG: Cache MISS for MORPHOUSDT 1h limit=24. Calling API...
2026-02-21 04:51:57,088 - binance_client - INFO - DEBUG: API returned 24 klines for MORPHOUSDT 1h (requested 24)
2026-02-21 04:51:57,092 - binance_client - INFO - DEBUG: Cache MISS for MORPHOUSDT 4h limit=24. Calling API...
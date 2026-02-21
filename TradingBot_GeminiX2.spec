# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('vietnamese_messages.py', '.'), ('indicators.py', '.'), ('database.py', '.'), ('binance_client.py', '.'), ('telegram_bot.py', '.'), ('telegram_commands.py', '.'), ('watchlist.py', '.'), ('watchlist_monitor.py', '.'), ('market_scanner.py', '.'), ('bot_detector.py', '.'), ('pump_detector_realtime.py', '.'), ('gemini_analyzer.py', '.'), ('advanced_pump_detector.py', '.'), ('volume_profile.py', '.'), ('fair_value_gaps.py', '.'), ('order_blocks.py', '.'), ('support_resistance.py', '.'), ('smart_money_concepts.py', '.'), ('volume_detector.py', '.'), ('bot_monitor.py', '.'), ('stoch_rsi_analyzer.py', '.')]
binaries = []
hiddenimports = ['pandas', 'numpy', 'requests', 'telebot', 'binance', 'ta', 'babel.numbers']
tmp_ret = collect_all('certifi')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TradingBot_GeminiX2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TradingBot_GeminiX2',
)

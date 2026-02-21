"""Quick BIOUSDT real data check"""
import os
from dotenv import load_dotenv
load_dotenv()
from binance_client import BinanceClient

bc = BinanceClient(os.getenv('BINANCE_API_KEY'), os.getenv('BINANCE_API_SECRET'))

# 1. Ticker
t = bc.client.get_ticker(symbol='BIOUSDT')
print('=== BIOUSDT REAL CHECK ===')
print(f'Price: ${float(t["lastPrice"]):.4f}')
print(f'24h Change: {float(t["priceChangePercent"]):.2f}%')
print(f'24h High: ${float(t["highPrice"]):.4f}')
print(f'24h Low: ${float(t["lowPrice"]):.4f}')
print(f'Volume: {float(t["quoteVolume"])/1e6:.1f}M USDT')

# 2. Last 6 candles
klines = bc.get_klines('BIOUSDT', '1h', limit=8)
print('\nLast 6h candles:')
for i in range(-6, 0):
    r = klines.iloc[i]
    o, c = float(r['open']), float(r['close'])
    color = 'GREEN' if c >= o else 'RED'
    chg = ((c - o) / o) * 100
    print(f'  {color}: {o:.4f} -> {c:.4f} ({chg:+.2f}%) Vol:{float(r["volume"]):,.0f}')

# 3. Order Book
ob = bc.get_order_book('BIOUSDT', limit=20)
bids = sum(float(b[1]) for b in ob['bids'][:10])
asks = sum(float(a[1]) for a in ob['asks'][:10])
ratio = bids / asks if asks > 0 else 0
print(f'\nOrder Book Top 10:')
print(f'  Bids: {bids:,.0f} BIO')
print(f'  Asks: {asks:,.0f} BIO')
print(f'  Ratio: {ratio:.2f}x ({"MUA > BAN" if ratio > 1 else "BAN > MUA"})')

# 4. Verdict
print(f'\n=== KET LUAN ===')
pct = float(t['priceChangePercent'])
if pct < -5: print('RED FLAG: Gia GIAM MANH 24h')
elif pct < -2: print('CAUTION: Gia giam trung binh 24h')
elif pct < 0: print('NOTE: Gia giam nhe 24h - co the la giai doan gom')
else: print('OK: Gia tang 24h')

if ratio < 0.7: print('RED FLAG: Phe Ban ap dao manh')
elif ratio < 1.0: print('CAUTION: Phe Ban nhieu hon Mua')
else: print('OK: Phe Mua ap dao')

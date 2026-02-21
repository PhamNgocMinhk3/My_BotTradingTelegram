"""
Quick MEUSDT Pump Analysis - Direct Technical Analysis
No heavy dependencies, just Binance data + basic TA
"""
import logging
import config
import numpy as np
import pandas as pd
from binance_client import BinanceClient

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("PumpAnalysis")

def analyze_pump(symbol="MEUSDT"):
    print(f"\n{'='*60}")
    print(f"  🔍 PHÂN TÍCH PUMP: {symbol}")
    print(f"{'='*60}\n")
    
    client = BinanceClient(config.BINANCE_API_KEY, config.BINANCE_API_SECRET)
    
    # ============ 1. PRICE ACTION ============
    print("📈 1. PRICE ACTION (Biến động giá)")
    print("-" * 40)
    
    # Get 5m data for short-term
    df_5m = client.get_klines(symbol, '5m', limit=100)
    # Get 1h data for trend
    df_1h = client.get_klines(symbol, '1h', limit=100)
    # Get 1d data for daily context
    df_1d = client.get_klines(symbol, '1d', limit=30)
    
    if df_5m is None or len(df_5m) < 20:
        print(f"❌ Không tìm thấy dữ liệu cho {symbol}. Kiểm tra lại tên coin.")
        return
    
    current_price = float(df_5m['close'].iloc[-1])
    
    # Short-term changes
    price_5m_ago = float(df_5m['close'].iloc[-2])
    price_30m_ago = float(df_5m['close'].iloc[-7]) if len(df_5m) >= 7 else price_5m_ago
    price_1h_ago = float(df_5m['close'].iloc[-13]) if len(df_5m) >= 13 else price_5m_ago
    price_4h_ago = float(df_5m['close'].iloc[-49]) if len(df_5m) >= 49 else price_5m_ago
    
    chg_5m = ((current_price - price_5m_ago) / price_5m_ago) * 100
    chg_30m = ((current_price - price_30m_ago) / price_30m_ago) * 100
    chg_1h = ((current_price - price_1h_ago) / price_1h_ago) * 100
    chg_4h = ((current_price - price_4h_ago) / price_4h_ago) * 100
    
    print(f"  💰 Giá hiện tại: ${current_price:,.6f}")
    print(f"  📊 Thay đổi 5 phút:  {chg_5m:+.2f}%")
    print(f"  📊 Thay đổi 30 phút: {chg_30m:+.2f}%")
    print(f"  📊 Thay đổi 1 giờ:   {chg_1h:+.2f}%")
    print(f"  � Thay đổi 4 giờ:   {chg_4h:+.2f}%")
    
    if df_1d is not None and len(df_1d) >= 2:
        price_24h_ago = float(df_1d['close'].iloc[-2])
        chg_24h = ((current_price - price_24h_ago) / price_24h_ago) * 100
        print(f"  📊 Thay đổi 24 giờ:  {chg_24h:+.2f}%")
        
        # Weekly
        if len(df_1d) >= 7:
            price_7d_ago = float(df_1d['close'].iloc[-7])
            chg_7d = ((current_price - price_7d_ago) / price_7d_ago) * 100
            print(f"  📊 Thay đổi 7 ngày:  {chg_7d:+.2f}%")
    
    # ============ 2. VOLUME ANALYSIS ============
    print(f"\n📊 2. VOLUME ANALYSIS (Phân tích khối lượng)")
    print("-" * 40)
    
    vol_current = float(df_5m['volume'].iloc[-1])
    vol_avg_20 = float(df_5m['volume'].rolling(20).mean().iloc[-1])
    vol_avg_50 = float(df_5m['volume'].rolling(50).mean().iloc[-1]) if len(df_5m) >= 50 else vol_avg_20
    vol_spike = vol_current / vol_avg_20 if vol_avg_20 > 0 else 0
    
    print(f"  � Volume hiện tại (5m): {vol_current:,.0f}")
    print(f"  📦 Volume TB 20 nến:     {vol_avg_20:,.0f}")
    print(f"  📦 Volume TB 50 nến:     {vol_avg_50:,.0f}")
    print(f"  🔥 Tỷ lệ Spike:         {vol_spike:.2f}x")
    
    if vol_spike > 5:
        print("  🚨 CẢNH BÁO: Volume SPIKE CỰC MẠNH (>5x) - Dấu hiệu pump rõ ràng!")
    elif vol_spike > 3:
        print("  ⚠️  Volume tăng mạnh (>3x) - Có dấu hiệu tích lũy/pump")
    elif vol_spike > 2:
        print("  📈 Volume tăng khá (>2x) - Đang có quan tâm")
    else:
        print("  ℹ️  Volume bình thường")
    
    # Volume trend (last 10 candles)
    vol_last_10 = df_5m['volume'].iloc[-10:].values
    vol_increasing = sum(1 for i in range(1, len(vol_last_10)) if vol_last_10[i] > vol_last_10[i-1])
    print(f"  📈 Xu hướng Volume: {vol_increasing}/9 nến tăng liên tiếp")
    
    # 1h volume
    if df_1h is not None and len(df_1h) >= 20:
        vol_1h_current = float(df_1h['volume'].iloc[-1])
        vol_1h_avg = float(df_1h['volume'].rolling(20).mean().iloc[-1])
        vol_1h_spike = vol_1h_current / vol_1h_avg if vol_1h_avg > 0 else 0
        print(f"\n  📦 Volume 1H hiện tại: {vol_1h_current:,.0f}")
        print(f"  📦 Volume 1H TB 20:    {vol_1h_avg:,.0f}")
        print(f"  🔥 Spike 1H:           {vol_1h_spike:.2f}x")
    
    # ============ 3. RSI ANALYSIS ============
    print(f"\n🎯 3. RSI ANALYSIS (Chỉ số sức mạnh)")
    print("-" * 40)
    
    def calc_rsi(series, period=14):
        delta = series.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    rsi_5m = calc_rsi(df_5m['close'], 14)
    rsi_current = float(rsi_5m.iloc[-1])
    rsi_prev = float(rsi_5m.iloc[-2])
    rsi_change = rsi_current - rsi_prev
    
    print(f"  RSI (5m, 14): {rsi_current:.1f}")
    print(f"  RSI thay đổi: {rsi_change:+.1f}")
    
    if rsi_current > 80:
        print("  🔴 QUÁ MUA (Overbought) - Có thể điều chỉnh sớm!")
    elif rsi_current > 70:
        print("  🟡 Gần vùng quá mua - Cẩn thận!")
    elif rsi_current < 30:
        print("  🟢 QUÁ BÁN (Oversold) - Cơ hội mua?")
    else:
        print("  ⚪ Vùng trung tính")
    
    if df_1h is not None and len(df_1h) >= 20:
        rsi_1h = calc_rsi(df_1h['close'], 14)
        print(f"  RSI (1H, 14): {float(rsi_1h.iloc[-1]):.1f}")
    
    # ============ 4. OBV (On-Balance Volume) ============
    print(f"\n� 4. OBV ANALYSIS (Dòng tiền tích lũy)")
    print("-" * 40)
    
    obv = [0]
    for i in range(1, len(df_5m)):
        if float(df_5m['close'].iloc[i]) > float(df_5m['close'].iloc[i-1]):
            obv.append(obv[-1] + float(df_5m['volume'].iloc[i]))
        elif float(df_5m['close'].iloc[i]) < float(df_5m['close'].iloc[i-1]):
            obv.append(obv[-1] - float(df_5m['volume'].iloc[i]))
        else:
            obv.append(obv[-1])
    
    obv_current = obv[-1]
    obv_10_ago = obv[-10] if len(obv) >= 10 else obv[0]
    obv_trend = "TĂNG 📈" if obv_current > obv_10_ago else "GIẢM 📉"
    obv_change = obv_current - obv_10_ago
    
    print(f"  OBV hiện tại:  {obv_current:,.0f}")
    print(f"  OBV 10 nến trước: {obv_10_ago:,.0f}")
    print(f"  Xu hướng OBV: {obv_trend} ({obv_change:+,.0f})")
    
    if obv_current > obv_10_ago and chg_5m < 1:
        print("  💎 STEALTH ACCUMULATION! OBV tăng trong khi giá đi ngang -> Tích lũy âm thầm!")
    elif obv_current > obv_10_ago:
        print("  ✅ Dòng tiền đang chảy VÀO - Bullish signal")
    else:
        print("  ⚠️ Dòng tiền đang chảy RA - Bearish signal")
    
    # ============ 5. BUY/SELL PRESSURE ============
    print(f"\n🏋️ 5. BUY/SELL PRESSURE (Áp lực mua/bán)")
    print("-" * 40)
    
    # Approximate buy/sell pressure from candle bodies
    buy_candles = sum(1 for i in range(len(df_5m)-20, len(df_5m)) 
                      if float(df_5m['close'].iloc[i]) > float(df_5m['open'].iloc[i]))
    sell_candles = 20 - buy_candles
    buy_ratio = buy_candles / 20
    
    print(f"  🟢 Nến tăng (20 nến): {buy_candles}/20 ({buy_ratio*100:.0f}%)")
    print(f"  🔴 Nến giảm (20 nến): {sell_candles}/20 ({(1-buy_ratio)*100:.0f}%)")
    
    if buy_ratio > 0.7:
        print("  💪 Áp lực MUA rất mạnh!")
    elif buy_ratio > 0.6:
        print("  📈 Áp lực mua chiếm ưu thế")
    elif buy_ratio < 0.3:
        print("  📉 Áp lực BÁN rất mạnh!")
    
    # ============ 6. ORDER BOOK ============
    print(f"\n🧱 6. ORDER BOOK (Sổ lệnh)")
    print("-" * 40)
    
    try:
        depth = client.get_order_book(symbol)
        if depth:
            bids = depth['bids'][:20]
            asks = depth['asks'][:20]
            
            bid_vol = sum(float(b[1]) for b in bids)
            ask_vol = sum(float(a[1]) for a in asks)
            ratio = bid_vol / ask_vol if ask_vol > 0 else 0
            
            print(f"  🟢 Buy Wall (20 levels):  {bid_vol:,.0f}")
            print(f"  🔴 Sell Wall (20 levels): {ask_vol:,.0f}")
            print(f"  📊 Tỷ lệ Buy/Sell:       {ratio:.2f}x")
            
            if ratio > 3:
                print("  🚀 CẠN CUNG CỰC MẠNH! Sell wall rất mỏng -> Dễ pump!")
            elif ratio > 2:
                print("  💪 Buy wall mạnh hơn nhiều -> Hỗ trợ tốt")
            elif ratio > 1.2:
                print("  📈 Buy wall nhỉnh hơn")
            elif ratio < 0.5:
                print("  ⚠️ Sell wall áp đảo -> Cẩn thận dump!")
            
            # Check for thin sell walls
            # Calculate cost to move price up 5%
            target_price = current_price * 1.05
            cost_5pct = 0
            for ask in depth['asks']:
                if float(ask[0]) <= target_price:
                    cost_5pct += float(ask[0]) * float(ask[1])
                else:
                    break
            print(f"\n  💰 Chi phí để đẩy giá +5%: ${cost_5pct:,.2f}")
            if cost_5pct < 50000:
                print("  🚨 CHI PHÍ RẤT THẤP -> Dễ bị pump/dump bởi cá voi!")
            elif cost_5pct < 200000:
                print("  ⚠️ Chi phí trung bình -> Có thể bị thao túng")
                
    except Exception as e:
        print(f"  ❌ Lỗi đọc Order Book: {e}")
    
    # ============ 7. PUMP VERDICT ============
    print(f"\n{'='*60}")
    print(f"  🎯 KẾT LUẬN: TẠI SAO {symbol} PUMP?")
    print(f"{'='*60}")
    
    reasons = []
    
    if vol_spike > 3:
        reasons.append(f"📊 Volume tăng đột biến {vol_spike:.1f}x so với trung bình")
    if chg_1h > 5:
        reasons.append(f"📈 Giá tăng mạnh {chg_1h:+.2f}% trong 1 giờ")
    if chg_30m > 3:
        reasons.append(f"🚀 Giá tăng {chg_30m:+.2f}% trong 30 phút")    
    if rsi_current > 70:
        reasons.append(f"🔥 RSI cao ({rsi_current:.0f}) - Momentum mạnh")
    if buy_ratio > 0.65:
        reasons.append(f"💪 Áp lực mua mạnh ({buy_ratio*100:.0f}% nến tăng)")
    if obv_current > obv_10_ago:
        reasons.append(f"💰 Dòng tiền đổ vào mạnh (OBV +{obv_change:,.0f})")
    
    try:
        if ratio > 2:
            reasons.append(f"🧱 Cạn cung: Buy/Sell ratio = {ratio:.1f}x")
        if cost_5pct < 100000:
            reasons.append(f"🐋 Thanh khoản mỏng: Chỉ cần ${cost_5pct:,.0f} để pump 5%")
    except:
        pass
    
    if reasons:
        print(f"\n  � CÁC NGUYÊN NHÂN PUMP:")
        for i, r in enumerate(reasons, 1):
            print(f"    {i}. {r}")
    else:
        print("\n  ℹ️ Chưa phát hiện dấu hiệu pump rõ ràng trên khung 5 phút.")
        print("     Có thể pump đã xảy ra trước đó hoặc trên khung thời gian lớn hơn.")
    
    # Risk assessment
    print(f"\n  ⚠️ ĐÁNH GIÁ RỦI RO:")
    if rsi_current > 80:
        print("    🔴 RSI QUÁ CAO -> Rủi ro điều chỉnh rất lớn, KHÔNG NÊN FOMO!")
    elif rsi_current > 70:
        print("    🟡 RSI cao -> Cẩn thận, có thể điều chỉnh ngắn hạn")
    
    if vol_spike > 5:
        print("    🔴 Volume quá cao -> Có thể là PUMP & DUMP, cực kỳ rủi ro!")
    
    print(f"\n{'='*60}\n")

if __name__ == "__main__":
    analyze_pump("MEUSDT")

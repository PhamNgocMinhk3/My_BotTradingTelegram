"""Test tier classification with real-world cases"""
from vietnamese_messages import get_stealth_accumulation_alert

def test_case(name, evidence, supply_shock, funding_rate, vol_ratio, price_change=0, red_candles=0, update_count=0, changes=None, entry_zone=None):
    # Dummy TP/SL info for testing
    tp_sl_info = {
        'sl': 0.095, 
        'tp1': 0.105, 
        'tp2': 0.115, 
        'is_strong': (vol_ratio > 3.0),
        'recommendation': 'GỒNG LÃI (Hold)' if vol_ratio > 3.0 else 'TP NGẮN HẠN'
    }

    msg = get_stealth_accumulation_alert(
        name, '0.10', None, evidence,
        supply_shock_data=supply_shock,
        funding_rate=funding_rate,
        vol_ratio=vol_ratio,
        vol_24h=50000000,
        vol_24h_usdt=3500000,
        price_change_24h=price_change,
        red_candles_6=red_candles,
        update_count=update_count,
        changes=changes,
        entry_zone=entry_zone,
        tp_sl_info=tp_sl_info
    )
    
    print(f"\n{'='*50}")
    print(f"COIN: {name} (Update #{update_count})")
    print(f"{'-'*20}")
    # Print first 15 lines
    for line in msg.split('\n')[:20]:
        print(line)

# Case 1: Initial Alert
print("\n" + "="*60)
print("CASE 1: Initial Alert (Normal)")
test_case('TESTUSDT', [
    '⏳ Dự Kiến Pump: 5-15 phút',
    'Gom Hàng Ẩn (Stealth): Điểm 72/100',
    '• Dòng Vol Vào: 19.5/25 (Tỷ Lệ: 1.78x)',
], {'detected': True, 'cost_to_push_5pct': 35000, 'ratio': 1.8},
    funding_rate=-0.009579, vol_ratio=1.78)

# Case 2: Update #1 (Price +3%, Vol +0.06%, Score +0, Ratio +0, Funding 0)
print("\n" + "="*60)
print("CASE 2: Update #1 (Price UP, Vol UP, Others Flat)")
changes = {
    'price_pct': 3.2, 
    'vol_pct': 0.08,
    'vol_coin_abs': 150000,
    'vol_usdt_pct': 0.08, 
    'vol_usdt_abs': 50000,
    'score': 0,
    'vol_ratio': 0.0,
    'funding_diff': 0.0
}
test_case('TESTUSDT', [
    '⏳ Dự Kiến Pump: 5-15 phút',
    'Gom Hàng Ẩn (Stealth): Điểm 72/100',
    '• Dòng Vol Vào: 19.5/25 (Tỷ Lệ: 1.78x)',
], {'detected': True, 'cost_to_push_5pct': 35000, 'ratio': 1.8},
    funding_rate=-0.009579, vol_ratio=1.78, update_count=1, changes=changes, entry_zone=(0.095, 0.098))

# Case 3: Update #2 (Score +5, Vol Ratio +0.5, Funding changed)
print("\n" + "="*60)
print("CASE 3: Update #2 (Score +5, Ratio +0.5, Funding Change)")
changes = {
    'price_pct': 0.5,
    'vol_pct': 0.01,
    'score': 5,
    'vol_ratio': 0.50,
    'funding_diff': -0.0005
}
test_case('TESTUSDT', [
    '⏳ Dự Kiến Pump: 5-15 phút',
    'Gom Hàng Ẩn (Stealth): Điểm 77/100',
    '• Dòng Vol Vào: 19.5/25 (Tỷ Lệ: 1.78x)',
], {'detected': True, 'cost_to_push_5pct': 35000, 'ratio': 1.8},
    funding_rate=-0.010079, vol_ratio=2.28, update_count=2, changes=changes, entry_zone=(0.096, 0.099))

print("\n" + "="*60)
print("DONE!")

# 🤖 RSI + MFI Trading Bot — Binance × Telegram × Gemini AI

> **Bot giao dịch thông minh** quét toàn bộ thị trường Binance theo thời gian thực, phát hiện sớm **coin sắp pump 10-20 phút**, phân tích chuyên sâu bằng **Google Gemini AI**, và gửi tín hiệu trực tiếp qua **Telegram**.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![Binance](https://img.shields.io/badge/Binance-API-yellow?logo=binance&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?logo=telegram&logoColor=white)
![Gemini](https://img.shields.io/badge/Google_Gemini-AI-4285F4?logo=google&logoColor=white)
![Railway](https://img.shields.io/badge/Deploy-Railway-000?logo=railway&logoColor=white)

---

## 📑 Mục Lục

- [Tổng Quan](#-tổng-quan)
- [Tính Năng Chính](#-tính-năng-chính)
- [Kiến Trúc Hệ Thống](#-kiến-trúc-hệ-thống)
- [Hệ Thống Phát Hiện Pump Coin](#-hệ-thống-phát-hiện-pump-coin-chi-tiết)
- [Phân Tích AI Bằng Gemini](#-phân-tích-ai-bằng-gemini)
- [Phát Hiện Bot Giao Dịch](#-phát-hiện-bot-giao-dịch)
- [Lệnh Telegram](#-lệnh-telegram)
- [Live Chart WebApp](#-live-chart-webapp)
- [Cài Đặt & Chạy Bot](#-cài-đặt--chạy-bot)
- [Deploy Lên Railway](#-deploy-lên-railway)
- [Cấu Trúc Thư Mục](#-cấu-trúc-thư-mục)
- [Công Nghệ Sử Dụng](#-công-nghệ-sử-dụng)

---

## 🌟 Tổng Quan

Bot này là một hệ thống phân tích thị trường crypto **hoàn toàn tự động**, kết hợp:

| Thành phần | Vai trò |
|------------|---------|
| **Binance API** | Lấy dữ liệu giá, volume, order book, trades theo thời gian thực |
| **15+ Technical Indicators** | RSI, MFI, Stochastic RSI, EMA, Bollinger Bands, VWAP, OBV, ATR, ... |
| **Google Gemini AI** | Phân tích tổng hợp tất cả dữ liệu → đưa ra khuyến nghị BUY/SELL/HOLD |
| **Pump/Dump Detector** | Hệ thống 4 lớp phát hiện sớm coin sắp tăng mạnh |
| **Bot Detector** | Phát hiện 5 loại bot thao túng thị trường |
| **Telegram Bot** | Giao diện điều khiển & nhận alert qua Telegram |
| **WebApp** | Biểu đồ trực quan với đầy đủ indicators |

---

## ✨ Tính Năng Chính

### 📊 Phân Tích Kỹ Thuật Đa Khung Thời Gian
- Quét đồng thời **4 timeframe**: 5m, 1h, 4h, 1d
- **RSI** (Relative Strength Index) — phát hiện quá mua/quá bán
- **MFI** (Money Flow Index) — theo dõi dòng tiền thực
- **Stochastic RSI** — momentum crossover signals
- **EMA 7/25/99** — xu hướng ngắn/trung/dài hạn
- **Bollinger Bands** — phát hiện breakout và squeeze
- **VWAP** — giá trung bình theo volume (giá "fair value")
- **OBV** (On-Balance Volume) — xác nhận dòng tiền

### 🚀 Phát Hiện Pump Sớm 10-20 Phút
- Hệ thống **4 lớp** xác nhận chéo (Layer 0 → Layer 3)
- **Stealth Accumulation** — phát hiện "cá mập" tích lũy ngầm
- **Early Momentum** — bắt tín hiệu ngay khi pump bắt đầu
- **Supply Shock** — cạn cung, giá buộc phải tăng
- Quét **50-100 coin** mỗi 30 giây

### 🤖 Phát Hiện Bot Thao Túng
- **Wash Trading** — giao dịch giả tạo volume
- **Spoofing** — đặt lệnh lớn rồi hủy
- **Iceberg Orders** — lệnh lớn ẩn sau nhiều lệnh nhỏ
- **Market Maker Bot** — thao túng 2 chiều
- **Dump Bot** — bán tháo có tổ chức

### 🧠 AI Phân Tích Bằng Google Gemini
- Tổng hợp **15+ nguồn dữ liệu** thành prompt chi tiết
- So sánh với lịch sử tuần trước (week-over-week)
- Phân loại loại coin (BTC, ETH, Large Cap, Micro Cap)
- Điểm Signal **0-100** với Entry/TP/SL cụ thể
- Đánh giá rủi ro và khuyến nghị chi tiết

### 📈 Watchlist & Giám Sát Tự Động
- Theo dõi danh sách coin yêu thích
- Tự động thêm coin khi phát hiện tín hiệu mạnh
- Smart cleanup — tự xóa coin yếu khỏi watchlist
- Cảnh báo volume bất thường cho coin trong watchlist

### 🌐 Live Chart WebApp
- Biểu đồ nến tương tác trên trình duyệt
- Hiển thị đầy đủ indicators overlay
- Tab phân tích AI tích hợp
- Lịch sử phân tích chi tiết

---

## 🏗 Kiến Trúc Hệ Thống

```
┌──────────────────────────────────────────────────────────────────┐
│                        TELEGRAM BOT                              │
│  (telegram_bot.py + telegram_commands.py)                        │
│  Nhận lệnh → Điều phối → Trả kết quả                           │
└──────────┬──────────────────────────────────────┬────────────────┘
           │                                      │
           ▼                                      ▼
┌─────────────────────┐              ┌──────────────────────────┐
│   MARKET SCANNER    │              │    PUMP DETECTOR         │
│  (market_scanner.py)│              │  (pump_detector_         │
│                     │              │   realtime.py)           │
│ Quét toàn bộ market │              │                          │
│ tìm RSI/MFI signals │              │ 4-Layer Detection System │
└────────┬────────────┘              └──────────┬───────────────┘
         │                                      │
         ▼                                      ▼
┌──────────────────────────────────────────────────────────────────┐
│                     CORE ANALYSIS ENGINES                        │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │ indicators.py│  │bot_detector  │  │ advanced_pump_detector │  │
│  │ RSI, MFI,    │  │ .py          │  │ .py                    │  │
│  │ Stoch RSI,   │  │ 5 Bot Types  │  │ 15+ Indicators         │  │
│  │ EMA, BB      │  │ Detection    │  │ Stealth Accumulation   │  │
│  └──────────────┘  └──────────────┘  │ Early Momentum         │  │
│                                      │ Supply Shock           │  │
│  ┌──────────────┐  ┌──────────────┐  └────────────────────────┘  │
│  │volume_       │  │ chart_       │                              │
│  │detector.py   │  │ generator.py │  ┌────────────────────────┐  │
│  │Volume Spikes │  │ Matplotlib   │  │ gemini_analyzer.py     │  │
│  │Multi-TF      │  │ Charts       │  │ Google Gemini AI       │  │
│  └──────────────┘  └──────────────┘  │ Full Analysis + Score  │  │
│                                      └────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                        BINANCE API                               │
│  (binance_client.py)                                             │
│  Klines • Order Book • Trades • Tickers • 24h Stats              │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🔍 Hệ Thống Phát Hiện Pump Coin (Chi Tiết)

> Đây là tính năng **cốt lõi** của bot — phát hiện coin sắp pump **sớm 10-20 phút** trước khi giá bùng nổ.

### 4 Lớp Xác Nhận (Layer System)

```
Layer 0 (Pre-Pump)  ──→  Layer 1 (Fast)  ──→  Layer 2 (Confirm)  ──→  Layer 3 (Trend)
    1h timeframe          5m timeframe         1h/4h timeframe         1d timeframe
    Mỗi 5 phút           Mỗi 30 giây         Khi L1 trigger          Khi L2 confirm
```

#### 🔮 Layer 0 — Pre-Pump (Phát Hiện Sớm Nhất)

Quét **top 100 coin** theo volume 24h, tìm 2 pattern đặc biệt:

**Stealth Accumulation ("Tín Hiệu Gemini")**
Phát hiện "cá mập" đang tích lũy ngầm trước khi pump:

| Tiêu chí | Trọng số | Giải thích |
|-----------|----------|------------|
| Price Compression | 20% | Bollinger Band thu hẹp → giá bị nén, sắp breakout |
| Volume Divergence | 25% | Volume tăng + giá đi ngang → ai đó mua số lượng lớn |
| OBV Trend | 20% | On-Balance Volume tăng liên tục → dòng tiền thực sự vào |
| EMA Alignment | 15% | EMA7 > EMA25 > EMA99 → xu hướng tăng đang hình thành |
| 24h Volume Growth | 20% | Volume 24h so với trung bình tăng → sự quan tâm thị trường |

**Early Momentum Breakout**
Bắt pump ngay thời điểm bắt đầu, cần ≥ 2/4 điều kiện:
1. Volume Spike > 3x trung bình 6 giờ
2. Giá vượt Bollinger Band trên
3. RSI cross 50 từ dưới lên
4. ≥ 3 nến xanh liên tiếp

**Công thức điểm Pre-Pump:**
```
Pre-Pump Score = Stealth Score × 0.6 + Momentum Score × 0.4
Alert khi Score ≥ 65/100
```

#### ⚡ Layer 1 — Fast Detection (5 phút)

Quét **top 50 coin** theo volume mỗi 30 giây:

| Chỉ số | Trọng số | Ngưỡng trigger |
|--------|----------|---------------|
| Volume Spike | 30% | Volume > 3x trung bình 20 nến |
| Buy Pressure | 25% | Tỷ lệ mua/bán > 60% |
| Price Momentum | 20% | Giá tăng > 1% trong 5m |
| Trade Frequency | 15% | Số giao dịch > 2x trung bình |
| Taker Buy Ratio | 10% | Taker buy > 55% tổng volume |

**Ngưỡng:** `pump_score ≥ 60` → chuyển sang Layer 2

#### ✅ Layer 2 — Confirmation (1h/4h)

- RSI 1h trong vùng momentum (40-70, không quá mua)
- MFI xác nhận dòng tiền vào (> 50)
- Volume 1h sustained (> 1.5x trung bình)
- Kiểm tra bot wash trading
- Gọi `AdvancedPumpDumpDetector.analyze_comprehensive()` — phân tích sâu 15+ indicators

#### 📈 Layer 3 — Long-term Trend (1D)

- EMA 7/25/99 alignment (uptrend confirmation)
- Daily RSI hợp lệ (30 < RSI < 75)
- Volume trend tăng trên daily
- Không có dump pattern

#### Điểm Cuối Cùng & Hành Động

```
Final Score = Layer1 × 30% + Layer2 × 40% + Layer3 × 30%
```

| Score | Mức độ | Hành động |
|-------|--------|-----------|
| ≥ 80 | 🔴 **STRONG PUMP** | Alert ngay + Tự động thêm watchlist |
| ≥ 65 | 🟡 **MODERATE PUMP** | Alert + Gợi ý thêm watchlist |
| < 65 | ⚪ Bình thường | Không alert |

### Tính Năng Thông Minh Bổ Trợ

- **Dynamic TP/SL**: Tính Take Profit & Stop Loss dựa trên ATR + mức độ pump
- **Supply Shock**: Phân tích order book, phát hiện cạn cung → giá sẽ phải tăng
- **Priority Rescan**: Quét lại coin đã theo dõi mỗi 2 phút (chỉ 5-15 coin → siêu nhanh)
- **Smart Cleanup**: Tự động xóa coin yếu khỏi watchlist mỗi 1 giờ
- **Cooldown System**: Chống spam alert — không gửi lặp cùng 1 coin

---

## 🧠 Phân Tích AI Bằng Gemini

Bot sử dụng **Google Gemini 1.5 Pro** để phân tích:

1. **Thu thập dữ liệu** từ 15+ nguồn (RSI, MFI, Volume Profile, Order Blocks, FVG, SMC, ...)
2. **So sánh lịch sử** — tuần này vs tuần trước
3. **Phân loại coin** — BTC, ETH, Large Cap Alt, Mid Cap, Small Cap, Micro Cap
4. **Tạo prompt chi tiết** gửi đến Gemini AI
5. **AI trả về**: Signal Score (0-100), Entry Price, TP1/TP2/TP3, Stop Loss, Timeframe, Phân tích chi tiết

### Institutional Indicators (Smart Money)

Tích hợp phân tích thể chế:
- **Volume Profile** — vùng giá giao dịch nhiều nhất
- **Order Blocks** — vùng mà "cá lớn" đặt lệnh
- **Fair Value Gaps** — khoảng trống giá chưa được fill
- **Smart Money Concepts** — Break of Structure, Change of Character

---

## 🤖 Phát Hiện Bot Giao Dịch

Module `bot_detector.py` phát hiện **5 loại bot** thao túng thị trường:

| Loại Bot | Cách phát hiện | Rủi ro cho trader |
|----------|----------------|-------------------|
| **Wash Trading** | Giao dịch lặp cùng size & giá, tần suất cao | Volume giả → pump giả |
| **Spoofing** | Đặt lệnh lớn rồi cancel trước khi khớp | Tạo ảo giác cung/cầu |
| **Iceberg** | Nhiều lệnh nhỏ ẩn lệnh lớn, timing đều đặn | Tích lũy/phân phối ngầm |
| **Market Maker** | Bid + Ask cả 2 phía, spread rất nhỏ | Thao túng giá 2 chiều |
| **Dump Bot** | Volume bán đột biến, sell pressure > 70% | Bán tháo có tổ chức |

**Bot Score**: 0-100 điểm, mức **≥ 75** = cảnh báo thao túng nặng.

---

## 💬 Lệnh Telegram

### 📊 Phân Tích Coin

| Lệnh | Mô tả |
|-------|--------|
| `/BTC` hoặc `/btc` | Phân tích toàn diện BTC (PUMP + RSI/MFI + Stoch RSI + nút AI) |
| `/ETH`, `/SOL`, ... | Phân tích bất kỳ coin nào (gõ tên coin) |
| `/stochrsi <coin>` | Phân tích Stochastic RSI đa khung thời gian |

### 📡 Quét Thị Trường

| Lệnh | Mô tả |
|-------|--------|
| `/scan` | Quét toàn bộ market tìm tín hiệu RSI/MFI (fast mode) |
| `/top` | Xem top coin theo volume 24h |
| `/startmarketscan` | Bật auto-scan thị trường |
| `/stopmarketscan` | Tắt auto-scan |
| `/marketstatus` | Xem trạng thái market scanner |

### 🚀 Pump Detection

| Lệnh | Mô tả |
|-------|--------|
| `/startpumpwatch` | **Bật** giám sát pump coin real-time |
| `/stoppumpwatch` | Tắt giám sát pump |
| `/pumpscan <coin>` | Scan pump cho 1 coin cụ thể |
| `/pumpstatus` | Xem trạng thái pump detector |

### 📋 Watchlist

| Lệnh | Mô tả |
|-------|--------|
| `/watch <coin>` | Thêm coin vào watchlist |
| `/unwatch <coin>` | Xóa coin khỏi watchlist |
| `/watchlist` | Xem danh sách watchlist |
| `/scanwatch` | Quét tất cả coin trong watchlist |
| `/clearwatch` | Xóa toàn bộ watchlist |
| `/startmonitor` | Bật auto-monitor watchlist |
| `/stopmonitor` | Tắt auto-monitor |
| `/monitorstatus` | Xem trạng thái monitor |

### 🤖 Bot Detector

| Lệnh | Mô tả |
|-------|--------|
| `/botscan <coin>` | Phân tích bot activity cho 1 coin |
| `/startbotmonitor` | Bật giám sát bot tự động |
| `/stopbotmonitor` | Tắt giám sát bot |
| `/botmonitorstatus` | Xem trạng thái bot monitor |
| `/botthreshold` | Cài ngưỡng phát hiện bot |

### 📊 Volume

| Lệnh | Mô tả |
|-------|--------|
| `/volumescan` | Quét volume spikes cho watchlist |
| `/volumesensitivity` | Điều chỉnh độ nhạy phát hiện volume |

### ⚙️ Hệ Thống

| Lệnh | Mô tả |
|-------|--------|
| `/start` | Khởi động bot |
| `/help` | Xem hướng dẫn sử dụng |
| `/menu` | Menu tương tác với nút bấm |
| `/status` | Xem trạng thái bot |
| `/settings` | Xem cài đặt hiện tại |
| `/performance` | Xem hiệu suất quét |

---

## 🌐 Live Chart WebApp

Bot tích hợp **web app hiển thị biểu đồ** trực quan:

- **Biểu đồ nến** với RSI, MFI, Volume overlay
- **Tab Indicators** — xem chi tiết từng indicator
- **Tab AI Analysis** — kết quả phân tích Gemini AI
- **Lịch sử phân tích** với analytics dashboard
- Truy cập trực tiếp từ nút trong Telegram message

**URL**: Tự động deploy cùng bot trên Railway tại route `/webapp/chart.html`

---

## ⚙ Cài Đặt & Chạy Bot

### Yêu Cầu

- **Python** 3.10+
- Tài khoản **Binance** (API Key)
- **Telegram Bot** (Token từ @BotFather)
- **Google Gemini** API Key

### Bước 1: Clone & Cài đặt

```bash
git clone https://github.com/PhamNgocMinhk3/My_BotTradingTelegram.git
cd My_BotTradingTelegram
pip install -r requirements.txt
```

### Bước 2: Cấu hình API Keys

Copy file `.env.example` thành `.env` và điền API keys:

```bash
cp .env.example .env
```

Mở file `.env` và điền:

```env
# Gemini AI
GEMINI_API_KEY=your_gemini_api_key_here

# Binance
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_API_SECRET=your_binance_api_secret_here

# Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
```

> ⚠️ **QUAN TRỌNG**: KHÔNG BAO GIỜ commit file `.env` lên GitHub! File này đã được thêm vào `.gitignore`.

### Bước 3: Chạy Bot

```bash
python main.py
```

Hoặc dùng script batch (Windows):
```bash
run_bot.bat
```

---

## 🚀 Deploy Lên Railway

Bot được tối ưu để deploy trên [Railway](https://railway.app):

1. Push code lên GitHub
2. Tạo project mới trên Railway → Connect GitHub repo
3. Thêm **Environment Variables** (giống file `.env`)
4. Railway tự động build & deploy

**Các file deploy:**
- `Procfile` — start command cho Railway
- `runtime.txt` — phiên bản Python
- `nixpacks.toml` — cấu hình Nixpacks build
- `requirements.txt` — dependencies

---

## 📁 Cấu Trúc Thư Mục

```
rsi-mfi-trading-bot/
│
├── 🚀 Core Bot
│   ├── main.py                    # Entry point — khởi tạo & chạy bot
│   ├── config.py                  # Cấu hình (API keys, trading params)
│   ├── binance_client.py          # Wrapper Binance API
│   ├── telegram_bot.py            # Telegram bot connection
│   └── telegram_commands.py       # Xử lý 30+ lệnh Telegram
│
├── 📊 Analysis Engines
│   ├── indicators.py              # RSI, MFI, Stochastic RSI, EMA, BB
│   ├── market_scanner.py          # Quét toàn bộ thị trường
│   ├── gemini_analyzer.py         # Google Gemini AI integration
│   ├── stoch_rsi_analyzer.py      # Stochastic RSI đa khung thời gian
│   └── chart_generator.py         # Tạo biểu đồ bằng Matplotlib
│
├── 🚀 Pump/Dump Detection
│   ├── pump_detector_realtime.py  # ⭐ Hệ thống 4 lớp phát hiện pump
│   ├── advanced_pump_detector.py  # ⭐ 15+ indicators, Stealth Accumulation
│   ├── bot_detector.py            # Phát hiện 5 loại bot thao túng
│   ├── volume_detector.py         # Volume spike detection
│   └── bot_monitor.py             # Giám sát bot tự động
│
├── 📈 Institutional Analysis (Smart Money)
│   ├── volume_profile.py          # Volume Profile analysis
│   ├── order_blocks.py            # Order Blocks detection
│   ├── fair_value_gaps.py         # Fair Value Gaps (FVG)
│   ├── smart_money_concepts.py    # SMC (BOS, CHoCH)
│   └── support_resistance.py      # Support & Resistance levels
│
├── 📋 Watchlist & Monitoring
│   ├── watchlist.py               # Quản lý watchlist
│   ├── watchlist_monitor.py       # Giám sát watchlist tự động
│   ├── price_tracker.py           # Theo dõi giá real-time
│   └── coin_monitor.py            # Monitor coin đơn lẻ
│
├── 🌐 WebApp (Live Charts)
│   ├── webapp/
│   │   ├── chart.html             # Trang biểu đồ chính
│   │   ├── css/                   # Styles (variables, base, components)
│   │   └── js/                    # Scripts (navigation, indicators, AI tab)
│   └── server.py                  # Flask server phục vụ WebApp + API
│
├── 🗄️ Data & Storage
│   ├── database.py                # Database operations (PostgreSQL)
│   └── vietnamese_messages.py     # Template tin nhắn tiếng Việt
│
├── 📐 TradingView Pine Scripts
│   ├── RSI+MFI.pine               # RSI + MFI indicator
│   ├── Stoch+RSI Multitimeframe.pine
│   ├── Smartmoneyconcept.pine
│   ├── Order Blocks & Fair Value Gaps.pine
│   ├── Support and Resistance (High Volume Boxes).pine
│   └── Volume Profile, Pivot Anchored.pine
│
├── ⚙️ Config & Deploy
│   ├── .env.example               # Template API keys
│   ├── requirements.txt           # Python dependencies
│   ├── Procfile                   # Railway start command
│   ├── runtime.txt                # Python version
│   ├── nixpacks.toml              # Nixpacks build config
│   ├── run_bot.bat                # Windows startup script
│   └── start.sh                   # Linux startup script
│
└── 🧪 Tests & Verification
    ├── test_pump_analysis.py      # Test pump detection
    ├── test_gemini.py             # Test Gemini AI
    ├── test_data_integration.py   # Test data pipeline
    ├── verify_all_fixes.py        # Verification suite
    └── ... (nhiều test files khác)
```

---

## 🛠 Công Nghệ Sử Dụng

| Công nghệ | Phiên bản | Vai trò |
|------------|-----------|---------|
| Python | 3.10+ | Ngôn ngữ chính |
| python-binance | 1.0.19 | Binance API client |
| pyTelegramBotAPI | 4.18.0 | Telegram Bot framework |
| google-genai | ≥1.0.0 | Google Gemini AI SDK |
| pandas | ≥1.3.0 | Xử lý dữ liệu, DataFrame |
| numpy | ≥1.21.0 | Tính toán indicators |
| matplotlib | ≥3.4.0 | Tạo biểu đồ |
| Flask | ≥2.3.0 | Web server cho WebApp |
| flask-cors | ≥4.0.0 | CORS cho API |
| psycopg2-binary | ≥2.9.0 | PostgreSQL driver |
| websockets | ≥12.0 | Real-time data |
| python-dotenv | 1.0.0 | Load .env |

---

## 📊 Thống Kê Dự Án

| Metric | Giá trị |
|--------|---------|
| Tổng dòng code Python | **~15,000+ lines** |
| Số module chính | **20+ files** |
| Lệnh Telegram | **30+ commands** |
| Technical indicators | **15+** |
| Bot detection types | **5 loại** |
| Pump detection layers | **4 lớp** |
| Timeframes phân tích | **4** (5m, 1h, 4h, 1d) |
| Tốc độ quét nhanh nhất | **30 giây / vòng** |
| Số coin quét mỗi vòng | **50-100** |

---

## 👨‍💻 Tác Giả

**Phạm Ngọc Minh** — [@PhamNgocMinhk3](https://github.com/PhamNgocMinhk3)

---

## 📄 License

Dự án này được phát triển cho mục đích **học tập và nghiên cứu**.

> ⚠️ **Disclaimer**: Bot này chỉ cung cấp phân tích kỹ thuật và tín hiệu tham khảo. Mọi quyết định giao dịch đều mang rủi ro. Hãy tự nghiên cứu (DYOR) trước khi đầu tư.

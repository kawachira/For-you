import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime, timedelta

# --- Import ใหม่สำหรับกราฟ Interactive ---
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- Import สำหรับ Google Sheets ---
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. ตั้งค่าหน้าเว็บ (The Master Version) ---
st.set_page_config(page_title="AI Stock Master (God Mode V.2)", page_icon="💎", layout="wide")

# --- Initialize Session State ---
if 'history_log' not in st.session_state:
    st.session_state['history_log'] = []

if 'search_triggered' not in st.session_state:
    st.session_state['search_triggered'] = False

if 'last_symbol' not in st.session_state:
    st.session_state['last_symbol'] = ""

# --- 2. CSS ปรับแต่ง (Clean & Professional) ---
st.markdown("""
    <style>
    body { overflow-x: hidden; }
    .block-container { padding-top: 1rem !important; padding-bottom: 5rem !important; }
    h1 { text-align: center; font-size: 2.8rem !important; margin-bottom: 0px !important; margin-top: 5px !important; }
    div[data-testid="stForm"] {
        border: none; padding: 30px; border-radius: 20px;
        background-color: var(--secondary-background-color);
        box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        max-width: 800px; margin: 0 auto;
    }
    div[data-testid="stFormSubmitButton"] button {
        width: 100%; border-radius: 12px; font-size: 1.2rem; font-weight: bold; padding: 15px 0;
    }
    .disclaimer-box {
        margin-top: 20px; margin-bottom: 20px; padding: 20px;
        background-color: #fff8e1; border: 2px solid #ffc107;
        border-radius: 12px; font-size: 1rem; color: #5d4037;
        text-align: center; font-weight: 500;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    /* X-Ray Box Style */
    .xray-box {
        background-color: #f0f9ff;
        border: 1px solid #bae6fd;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 20px;
    }
    .xray-title {
        font-weight: bold;
        color: #0369a1;
        font-size: 1.1rem;
        margin-bottom: 10px;
        border-bottom: 1px solid #e0f2fe;
        padding-bottom: 5px;
    }
    .xray-item {
        display: flex;
        justify-content: space-between;
        margin-bottom: 8px;
        font-size: 0.95rem;
    }
    /* Fundamental Box */
    .fund-box {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 10px;
        text-align: center;
    }
    .fund-label { font-size: 0.8rem; color: #64748b; }
    .fund-val { font-size: 1.1rem; font-weight: bold; color: #0f172a; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ส่วนหัวข้อ ---
st.markdown("<h1>💎 Ai<br><span style='font-size: 1.5rem; opacity: 0.7;'>Ultimate Sniper (God Mode V.2)🚀</span></h1>", unsafe_allow_html=True)

# --- Form ค้นหา ---
col_space1, col_form, col_space2 = st.columns([1, 2, 1])
with col_form:
    with st.form(key='search_form'):
        st.markdown("### 🔍 ค้นหาหุ้น")
        c1, c2 = st.columns([3, 1])
        with c1:
            symbol_input_raw = st.text_input("ชื่อหุ้น (เช่น AMZN,EOSE,RKLB,TSLA)🪐", value="").upper().strip()
        with c2:
            timeframe = st.selectbox("Timeframe:", ["1h (รายชั่วโมง)", "1d (รายวัน)", "1wk (รายสัปดาห์)"], index=1)
            if "1wk" in timeframe: tf_code = "1wk"; mtf_code = "1mo"
            elif "1h" in timeframe: tf_code = "1h"; mtf_code = "1d"
            else: tf_code = "1d"; mtf_code = "1wk"
        
        st.markdown("---")
        submit_btn = st.form_submit_button("🚀 วิเคราะห์ทันที")

# --- 4. Helper Functions (Visuals & Data) ---

def plot_interactive_chart(df, symbol, ema20, ema50, ema200, zones):
    """
    สร้างกราฟ Interactive ด้วย Plotly
    """
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, subplot_titles=(f'{symbol} Price Action', 'Volume'), 
                        row_width=[0.2, 0.7])

    # Candlestick
    fig.add_trace(go.Candlestick(x=df.index,
                    open=df['Open'], high=df['High'],
                    low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)

    # EMAs
    if 'EMA20' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA20'], opacity=0.7, line=dict(color='#f59e0b', width=1), name='EMA 20'), row=1, col=1)
    if 'EMA50' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA50'], opacity=0.7, line=dict(color='#3b82f6', width=1.5), name='EMA 50'), row=1, col=1)
    if 'EMA200' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA200'], opacity=0.7, line=dict(color='#ef4444', width=2), name='EMA 200'), row=1, col=1)

    # Zones (Demand/Supply) - Optional Visualization
    # (Plotly makes rectangles tricky with datetime x-axis, simplifying to lines for now)
    
    # Volume
    colors = ['#dc2626' if row['Open'] - row['Close'] >= 0 else '#16a34a' for index, row in df.iterrows()]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name='Volume'), row=2, col=1)

    # Layout Updates
    fig.update_layout(
        height=500,
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis_rangeslider_visible=False,
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(gridcolor='#e5e7eb'),
        xaxis=dict(gridcolor='#e5e7eb')
    )
    return fig

def analyze_candlestick(df_window):
    # (ฟังก์ชันเดิม ไม่เปลี่ยนแปลง logic)
    if len(df_window) < 4: 
        return "Normal Candle", "gray", "ข้อมูลไม่เพียงพอ", False

    c1 = df_window.iloc[0]; c2 = df_window.iloc[1]; c3 = df_window.iloc[2]; c4 = df_window.iloc[3]
    open_p = c4['Open']; close_p = c4['Close']; high_p = c4['High']; low_p = c4['Low']
    body = abs(close_p - open_p); range_len = high_p - low_p
    is_bull = close_p >= open_p; color = "🟢 เขียว (Buying)" if is_bull else "🔴 แดง (Selling)"
    prev_open = c3['Open']; prev_close = c3['Close']; is_prev_bull = prev_close >= prev_open

    pattern_name = "Normal Candle (ปกติ)"; detail = "แรงซื้อขายสมดุล"; is_big = False

    if (c2['Close'] < c2['Open']) and (c3['Close'] < c3['Open']) and (c4['Close'] < c4['Open']):
        if (c4['Close'] < c3['Close']) and (c3['Close'] < c2['Close']):
            return "🦅 Three Black Crows (อีกา 3 ตัว)", "🔴 แดง (Selling)", "แรงขายทุบต่อเนื่อง 3 วัน (ระวังลงลึก)", True

    if (c2['Close'] > c2['Open']) and (c3['Close'] > c3['Open']) and (c4['Close'] > c4['Open']):
        if (c4['Close'] > c3['Close']) and (c3['Close'] > c2['Close']):
            return "💂 Three White Soldiers (3 ทหารเสือ)", "🟢 เขียว (Buying)", "แรงซื้อดันต่อเนื่อง 3 วัน (แข็งแกร่ง)", True

    c2_body = abs(c2['Close'] - c2['Open']); c2_range = c2['High'] - c2['Low']
    if (c2['Close'] < c2['Open']) and (c2_body > c2_range * 0.5):
        if abs(c3['Close'] - c3['Open']) < c2_body * 0.4:
            midpoint = (c2['Open'] + c2['Close']) / 2
            if (c4['Close'] > c4['Open']) and (c4['Close'] > midpoint):
                return "🌅 Morning Star (รุ่งอรุณ)", "🟢 เขียว (Buying)", "กลับตัวขึ้นสวยงาม (Confirm Reversal)", True

    if (c2['Close'] > c2['Open']) and (c2_body > c2_range * 0.5):
        if abs(c3['Close'] - c3['Open']) < c2_body * 0.4:
            midpoint = (c2['Open'] + c2['Close']) / 2
            if (c4['Close'] < c4['Open']) and (c4['Close'] < midpoint):
                return "🌆 Evening Star (พลบค่ำ)", "🔴 แดง (Selling)", "กลับตัวลงชัดเจน (Confirm Reversal)", True

    if is_prev_bull and not is_bull:
        if (open_p >= prev_close) and (close_p <= prev_open):
            return "🐻 Bearish Engulfing (กลืนกินขาลง)", "🔴 แดง (Selling)", "แท่งแดงกลบแท่งเขียวเมื่อวาน", True

    if not is_prev_bull and is_bull:
        if (open_p <= prev_close) and (close_p >= prev_open):
            return "🐂 Bullish Engulfing (กลืนกินขาขึ้น)", "🟢 เขียว (Buying)", "แท่งเขียวกลบแท่งแดงเมื่อวาน", True
    
    wick_up = high_p - max(close_p, open_p); wick_low = min(close_p, open_p) - low_p
    
    if wick_low > (body * 2) and wick_up < body: pattern_name = "🔨 Hammer/Pinbar (ค้อน)"; detail = "ปฏิเสธราคาต่ำ (แรงซื้อสวน)"
    elif wick_up > (body * 2) and wick_low < body: pattern_name = "☄️ Shooting Star (ดาวตก)"; detail = "ปฏิเสธราคาสูง (แรงขายตบ)"
    elif body > (range_len * 0.6): 
        is_big = True
        pattern_name = "Big Bullish (แท่งเขียวตัน)" if is_bull else "Big Bearish (แท่งแดงตัน)"
        detail = "แรงซื้อ/ขาย คุมตลาดเบ็ดเสร็จ"
    elif body < (range_len * 0.1): pattern_name = "Doji (โดจิ)"; detail = "ตลาดลังเล (Indecision)"
        
    return pattern_name, color, detail, is_big

def arrow_html(change):
    if change is None: return ""
    return "<span style='color:#16a34a;font-weight:600'>▲</span>" if change > 0 else "<span style='color:#dc2626;font-weight:600'>▼</span>"

def format_volume(vol):
    if vol >= 1_000_000_000: return f"{vol/1_000_000_000:.2f}B"
    if vol >= 1_000_000: return f"{vol/1_000_000:.2f}M"
    if vol >= 1_000: return f"{vol/1_000:.2f}K"
    return f"{vol:,.0f}"

def custom_metric_html(label, value, status_text, color_status, icon_svg):
    color_code = "#16a34a" if color_status == "green" else "#dc2626" if color_status == "red" else "#a3a3a3"
    html = f"""
    <div style="margin-bottom: 15px;">
        <div style="display: flex; align-items: baseline; gap: 10px; margin-bottom: 5px;">
            <div style="font-size: 18px; font-weight: 700; opacity: 0.9; color: var(--text-color); white-space: nowrap;">{label}</div>
            <div style="font-size: 24px; font-weight: 700; color: var(--text-color);">{value}</div>
        </div>
        <div style="display: flex; align-items: start; gap: 6px; font-size: 15px; font-weight: 600; color: {color_code}; line-height: 1.4;">
            <div style="margin-top: 3px; min-width: 24px;">{icon_svg}</div>
            <div>{status_text}</div>
        </div>
    </div>
    """
    return html

def get_rsi_interpretation(rsi, is_trending_mode):
    if np.isnan(rsi): return "N/A"
    if is_trending_mode:
        if rsi >= 75: return "Super Bullish (แรงสุดๆ)"
        elif rsi <= 45: return "Dip Opportunity (ย่อซื้อ)"
        else: return "Trending"
    else: 
        if rsi >= 65: return "Overbought (ระวังแรงขาย)"
        elif rsi <= 35: return "Oversold (ระวังเด้งสวน)"
        else: return "Neutral"

def get_adx_interpretation(adx, is_uptrend):
    if np.isnan(adx): return "N/A"
    trend_str = "ขาขึ้น" if is_uptrend else "ขาลง"
    if adx >= 50: return f"Super Strong {trend_str} (แรงมาก)"
    if adx >= 25: return f"Strong {trend_str} (แข็งแกร่ง)"
    return "Weak/Sideway (ตลาดไร้ทิศทาง)"

def save_to_gsheet(data_dict):
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)
            sheet = client.open("Stock_Analysis_Log").sheet1
            row = [
                datetime.now().strftime("%Y-%m-%d"), 
                data_dict.get("เวลา", ""), data_dict.get("หุ้น", ""), data_dict.get("TF", ""),
                data_dict.get("ราคา", ""), data_dict.get("Change%", ""), data_dict.get("สถานะ", ""),
                data_dict.get("Action", ""), data_dict.get("SL", ""), data_dict.get("TP", "")
            ]
            sheet.append_row(row)
            return True
        return False
    except Exception as e:
        return False

# --- SMC: Find Zones ---
def find_demand_zones(df, atr_multiplier=0.25):
    zones = []
    if len(df) < 20: return zones
    lows = df['Low']
    is_swing_low = (lows < lows.shift(1)) & (lows < lows.shift(2)) & (lows < lows.shift(-1)) & (lows < lows.shift(-2))
    swing_indices = is_swing_low[is_swing_low].index
    current_price = df['Close'].iloc[-1]
    for date in swing_indices:
        if date == df.index[-1] or date == df.index[-2]: continue
        swing_low_val = df.loc[date, 'Low']
        atr_val = df.loc[date, 'ATR'] if 'ATR' in df.columns else (swing_low_val * 0.02)
        if np.isnan(atr_val): atr_val = swing_low_val * 0.02
        zone_bottom = swing_low_val
        zone_top = swing_low_val + (atr_val * atr_multiplier)
        if (current_price - zone_top) / current_price > 0.20: continue
        future_data = df.loc[date:][1:]
        if future_data.empty: continue
        if not (future_data['Close'] < zone_bottom).any():
            zones.append({'bottom': zone_bottom, 'top': zone_top})
    return zones

def find_supply_zones(df, atr_multiplier=0.25):
    zones = []
    if len(df) < 20: return zones
    highs = df['High']
    is_swing_high = (highs > highs.shift(1)) & (highs > highs.shift(2)) & (highs > highs.shift(-1)) & (highs > highs.shift(-2))
    swing_indices = is_swing_high[is_swing_high].index
    current_price = df['Close'].iloc[-1]
    for date in swing_indices:
        if date == df.index[-1] or date == df.index[-2]: continue
        swing_high_val = df.loc[date, 'High']
        atr_val = df.loc[date, 'ATR'] if 'ATR' in df.columns else (swing_high_val * 0.02)
        if np.isnan(atr_val): atr_val = swing_high_val * 0.02
        zone_top = swing_high_val
        zone_bottom = swing_high_val - (atr_val * atr_multiplier)
        if (zone_bottom - current_price) / current_price > 0.20: continue
        future_data = df.loc[date:][1:]
        if future_data.empty: continue
        if not (future_data['Close'] > zone_top).any():
            zones.append({'bottom': zone_bottom, 'top': zone_top})
    return zones

# --- 5. Data Fetching ---
@st.cache_data(ttl=60, show_spinner=False)
def get_data_hybrid(symbol, interval, mtf_interval):
    try:
        ticker = yf.Ticker(symbol)
        period_val = "10y" if interval == "1wk" else "5y" if interval == "1d" else "730d"
        df = ticker.history(period=period_val, interval=interval)
        df_mtf = ticker.history(period="10y", interval=mtf_interval)
        if not df_mtf.empty: df_mtf['EMA200'] = ta.ema(df_mtf['Close'], length=200)
        
        try: raw_info = ticker.info 
        except: raw_info = {} 

        df_daily = ticker.history(period="5d", interval="1d")
        if not df_daily.empty:
            price = df_daily['Close'].iloc[-1]
            chg = price - df_daily['Close'].iloc[-2] if len(df_daily) >=2 else 0
            pct = (chg / df_daily['Close'].iloc[-2]) if len(df_daily) >=2 else 0
            d_h, d_l, d_o = df_daily['High'].iloc[-1], df_daily['Low'].iloc[-1], df_daily['Open'].iloc[-1]
        else:
            price = df['Close'].iloc[-1]; chg = 0; pct = 0; d_h=0; d_l=0; d_o=0

        info_dict = {
            'longName': raw_info.get('longName', symbol), 
            'marketState': raw_info.get('marketState', 'REGULAR'), 
            'regularMarketPrice': price, 'regularMarketChange': chg,
            'regularMarketChangePercent': pct, 'dayHigh': d_h, 'dayLow': d_l, 'regularMarketOpen': d_o,
            'preMarketPrice': raw_info.get('preMarketPrice'), 'preMarketChange': raw_info.get('preMarketChange'),
            'postMarketPrice': raw_info.get('postMarketPrice'), 'postMarketChange': raw_info.get('postMarketChange'),
            'marketCap': raw_info.get('marketCap'), 'trailingPE': raw_info.get('trailingPE'), 
            'trailingEps': raw_info.get('trailingEps'), 'sector': raw_info.get('sector'),
            'website': raw_info.get('website'), 'shortName': raw_info.get('shortName')
        }
        return df, info_dict, df_mtf
    except: return None, None, None

def analyze_volume(row, vol_ma):
    vol = row['Volume']
    if np.isnan(vol_ma) or vol_ma == 0: return "☁️ ปกติ", "gray"
    pct = (vol / vol_ma) * 100
    if pct >= 250: return f"💣 สูงมาก/ระเบิด ({pct:.0f}%)", "#7f1d1d"
    elif pct >= 120: return f"🔥 สูง/คึกคัก ({pct:.0f}%)", "#16a34a"
    elif pct <= 70: return f"🌵 ต่ำ/เบาบาง ({pct:.0f}%)", "#f59e0b"
    else: return f"☁️ ปกติ ({pct:.0f}%)", "gray"

# --- 7. AI Decision Engine (THE UPGRADED BRAIN - GOD MODE) ---
def ai_hybrid_analysis(price, ema20, ema50, ema200, rsi, macd_val, macd_sig, adx, bb_up, bb_low, 
                       vol_status, mtf_trend, atr_val, mtf_ema200_val,
                       open_price, high, low, close, obv_val, obv_avg,
                       obv_slope, prev_open, prev_close, vol_now, vol_avg, demand_zones,
                       is_squeeze, df_candles): 

    def safe(x): return float(x) if not np.isnan(float(x)) else np.nan
    price = safe(price); ema20 = safe(ema20); ema50 = safe(ema50); ema200 = safe(ema200)
    atr_val = safe(atr_val); obv_slope = safe(obv_slope); vol_now = safe(vol_now); vol_avg = safe(vol_avg)

    candle_pattern, candle_color, candle_detail, is_big_candle = analyze_candlestick(df_candles)
    
    is_shooting_star = "Shooting Star" in candle_pattern

    is_vol_dry = vol_now < (vol_avg * 0.8) 
    is_vol_climax = vol_now > (vol_avg * 2.0) 
    vol_txt, vol_col = analyze_volume({'Volume': vol_now}, vol_avg)

    in_demand_zone = False; active_zone = None; confluence_msg = ""
    if demand_zones:
        for zone in demand_zones:
            if (low <= zone['top'] * 1.015) and (high >= zone['bottom']):
                in_demand_zone = True; active_zone = zone; break
    
    is_confluence = False
    if in_demand_zone:
        if not np.isnan(ema200) and abs(active_zone['bottom'] - ema200) / price < 0.02: is_confluence = True; confluence_msg = "Zone + EMA 200"
        elif not np.isnan(ema50) and abs(active_zone['bottom'] - ema50) / price < 0.02: is_confluence = True; confluence_msg = "Zone + EMA 50"

    is_strong_trend = adx > 25 if not np.isnan(adx) else False
    is_major_uptrend = price > ema200 if not np.isnan(ema200) else True

    # --- SCORING ---
    score = 0; bullish = []; bearish = []; ctx = ""

    if not np.isnan(ema200):
        if price > ema200: score += 3; bullish.append("Structure: ยืนเหนือ EMA 200 (ขาขึ้นระยะยาว)")
        else: score -= 3; bearish.append("Structure: หลุด EMA 200 (ขาลงระยะยาว)")

    if not np.isnan(ema50):
        if price > ema50: score += 2; bullish.append("Structure: ยืนเหนือ EMA 50 (แกร่งระยะกลาง)")
        else: score -= 1; bearish.append("Structure: หลุด EMA 50 (เสียทรงระยะกลาง)")

    if "Three Black Crows" in candle_pattern:
        score -= 3; bearish.append("🦅 Three Black Crows: แรงขายทุบ 3 วันติด"); ctx = "🩸 Panic Dump: หนีตาย"
    elif "Evening Star" in candle_pattern:
        score -= 2; bearish.append("🌆 Evening Star: กลับตัวลง")
        if score < 2: ctx = "📉 Reversal: สัญญาณกลับตัวลง"
    elif "Bearish Engulfing" in candle_pattern:
        if is_vol_climax: score -= 3; bearish.append("🐻 Bearish Engulfing + Vol Peak"); ctx = "🩸 Panic Sell"
        elif is_major_uptrend and is_vol_dry: score += 1; bullish.append("🐂 Bullish Pullback: ย่อวอลุ่มแห้ง")
        else: score -= 2; bearish.append("⚠️ Bearish Engulfing")
    elif is_shooting_star:
        score -= 1; bearish.append("☄️ Shooting Star: แรงขายกดดัน")

    if "Three White Soldiers" in candle_pattern: score += 3; bullish.append("💂 Three White Soldiers")
    elif "Morning Star" in candle_pattern:
        if in_demand_zone: score += 3; bullish.append("🌅 Morning Star (in Zone): กลับตัวต้นน้ำ")
        else: score += 2; bullish.append("🌅 Morning Star")
    elif "Bullish Engulfing" in candle_pattern:
        if rsi > 70: score -= 1; bearish.append("⚠️ Bullish Trap: เขียวดอย")
        elif is_vol_climax: score += 3; bullish.append("🚀 Power Buy: เขียวกลืนกิน + วอลุ่ม")
        else: score += 2; bullish.append("🐂 Bullish Engulfing")

    obv_strength_pct = 0
    if vol_avg > 0 and not np.isnan(obv_slope): obv_strength_pct = (obv_slope / vol_avg) * 100
    obv_insight = f"Flow ปกติ ({obv_strength_pct:.1f}%)"

    if obv_strength_pct > 5: 
        if obv_strength_pct > 60: obv_insight = f"🚀 กวาดซื้อ ({obv_strength_pct:.1f}%)"
        else: obv_insight = f"💎 เก็บของ ({obv_strength_pct:.1f}%)"
        if price < ema20: score += 2; bullish.append(f"Bullish Div: ราคาลงแต่เงินเข้า")
        else: score += 1; bullish.append(f"Fund Flow: เงินไหลเข้าต่อเนื่อง")
    elif obv_strength_pct < -5:
        if obv_strength_pct < -60: obv_insight = f"🩸 ทิ้งของ ({obv_strength_pct:.1f}%)"
        else: obv_insight = f"💧 รินขาย ({obv_strength_pct:.1f}%)"
        if price > ema20: score -= 2; bearish.append(f"Bearish Div: ราคาขึ้นแต่เงินออก")
        else: score -= 1; bearish.append(f"Fund Flow: เงินไหลออกต่อเนื่อง")

    if not np.isnan(macd_val) and macd_val > macd_sig: score += 1; bullish.append("MACD ตัดขึ้น")
    elif not np.isnan(macd_val): score -= 1

    if not np.isnan(rsi):
        if is_strong_trend and is_major_uptrend:
            if rsi > 75 and not is_vol_climax: score += 1; bullish.append(f"RSI {rsi:.0f}: Super Bullish Trend") 
            elif rsi < 45: score += 2; bullish.append(f"RSI {rsi:.0f}: Dip Opportunity")
        else: 
            if rsi > 65: score -= 2; bearish.append(f"RSI {rsi:.0f}: Overbought")
            elif rsi < 30: score += 2; bullish.append(f"RSI {rsi:.0f}: Oversold")

    if in_demand_zone:
        score += 3; bullish.append("🟢 In Demand Zone (ต้นทุนดี)")
        if is_confluence: score += 1; bullish.append(f"⭐ {confluence_msg}")
        if not ctx: ctx = "💎 Sniper Mode (เข้าโซนสวย)"

    if ctx == "":
        if score >= 5: ctx = "🚀 Bullish Breakout: โมเมนตัมกระทิงดุ"
        elif score >= 2: ctx = "📈 Uptrend Structure: ย่อตัวเพื่อขึ้นต่อ"
        elif score <= -4: ctx = "🩸 Bearish Crash: แรงขายรุนแรง"
        elif score <= -1: ctx = "📉 Downtrend Pressure: เด้งเพื่อลง"
        else: ctx = "⚖️ Sideway/Neutral: รอเลือกทาง"

    if score >= 6:
        color = "green"; title = "🚀 Sniper Entry: จุดซื้อคมกริบ"; strat = "Aggressive Buy"
        adv = f"โมเมนตัมแรงจัด Pattern สวย ถือรันเทรนด์ SL: {low-(atr_val*1.0):.2f}"
    elif score >= 4:
        if "Pullback" in ctx or "Dip" in str(bullish):
            color = "green"; title = "🐂 Bullish Pullback: ย่อเพื่อไปต่อ"; strat = "Buy on Dip"
            adv = "ราคาย่อตัวในขาขึ้น วอลุ่มแห้ง/RSI ต่ำ เป็นจังหวะเก็บของที่ดีที่สุด"
        else:
            color = "green"; title = "🐂 Strong Buy: ขาขึ้นแข็งแกร่ง"; strat = "Accumulate"
            adv = "เทรนด์หลักเป็นขาขึ้น ย่อตัวน่าสนใจ"
    elif score >= 1:
        if "Sideway Up" in ctx:
            color = "yellow"; title = "⚖️ Sideway Up: สะสมพลัง"; strat = "Accumulate"
            adv = "ราคาออกข้างแต่เงินไหลเข้า ดักเก็บที่แนวรับ ลุ้นเบรค"
        else:
            color = "yellow"; title = "⚖️ Neutral: รอความชัดเจน"; strat = "Wait & Watch"
            adv = "ปัจจัยขัดแย้งกัน นั่งทับมือไปก่อน"
    elif score <= -4:
        if "Panic" in ctx:
            color = "red"; title = "💀 Panic Sell: หนีตาย"; strat = "Exit Immediately"
            adv = "วงแตก! แรงขายระดับวิกฤต ห้ามรับเด็ดขาด"
        else:
            color = "red"; title = "🩸 Falling Knife: มีดหล่น"; strat = "Avoid / Cut Loss"
            adv = "ราคาดิ่งแรง หลุดแนวรับสำคัญ รอให้หยุดลงและสร้างฐานก่อน"
    else: 
        color = "orange"; title = "🐻 Bearish Pressure: แรงกดดันสูง"; strat = "Reduce Port"
        adv = "แรงขายมากกว่าแรงซื้อ ระวังหลุดแนวรับ ไม่ควรรีบรับ"

    if in_demand_zone: sl = active_zone['bottom'] - (atr_val*0.5)
    else: sl = price - (2*atr_val) if not np.isnan(atr_val) else price*0.95
    tp = price + (3*atr_val) if not np.isnan(atr_val) else price*1.05

    return {
        "status_color": color, "banner_title": title, "strategy": strat, "context": ctx,
        "bullish_factors": bullish, "bearish_factors": bearish, "sl": sl, "tp": tp, "holder_advice": adv,
        "candle_pattern": candle_pattern, "candle_color": candle_color, "candle_detail": candle_detail,
        "vol_quality_msg": vol_txt, "vol_quality_color": vol_col,
        "in_demand_zone": in_demand_zone, "confluence_msg": confluence_msg,
        "is_squeeze": is_squeeze, "obv_insight": obv_insight
    }

# --- 8. Main Execution & Display ---

if submit_btn:
    st.session_state['search_triggered'] = True
    st.session_state['last_symbol'] = symbol_input_raw

if st.session_state['search_triggered']:
    symbol_input = st.session_state['last_symbol']
    
    st.divider()
    
    # CSS บังคับ Expander
    st.markdown("""
    <style>
    body { overflow: auto !important; }
    div[data-testid="stExpander"] details summary p {
        font-size: 18px !important; font-weight: 700 !important; color: #333333 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    with st.spinner(f"AI God Mode V.2 กำลังประมวลผล {symbol_input}..."):
        df, info, df_mtf = get_data_hybrid(symbol_input, tf_code, mtf_code)
        try:
            ticker_stats = yf.Ticker(symbol_input)
            df_stats_day = ticker_stats.history(period="2y", interval="1d")
            df_stats_week = ticker_stats.history(period="5y", interval="1wk")
        except:
            df_stats_day = pd.DataFrame(); df_stats_week = pd.DataFrame()

    if df is not None and not df.empty and len(df) > 20: 
        # --- Indicators ---
        df['EMA20'] = ta.ema(df['Close'], length=20)
        df['EMA50'] = ta.ema(df['Close'], length=50)
        ema200_series = ta.ema(df['Close'], length=200)
        df['EMA200'] = ema200_series if ema200_series is not None else np.nan
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        macd = ta.macd(df['Close'])
        if macd is not None: df = pd.concat([df, macd], axis=1)
        bbands = ta.bbands(df['Close'], length=20, std=2)
        if bbands is not None and len(bbands.columns) >= 3:
            bbl_col_name, bbu_col_name = bbands.columns[0], bbands.columns[2]
            df = pd.concat([df, bbands], axis=1)
        else: bbl_col_name, bbu_col_name = None, None
        adx = ta.adx(df['High'], df['Low'], df['Close'], length=14)
        if adx is not None: df = pd.concat([df, adx], axis=1)
        df['Vol_SMA20'] = ta.sma(df['Volume'], length=20)
        df['OBV'] = ta.obv(df['Close'], df['Volume'])
        df['OBV_SMA20'] = ta.sma(df['OBV'], length=20)
        df['OBV_Slope'] = ta.slope(df['OBV'], length=5) 
        if bbu_col_name and bbl_col_name and 'EMA20' in df.columns:
            df['BB_Width'] = (df[bbu_col_name] - df[bbl_col_name]) / df['EMA20'] * 100
            df['BB_Width_Min20'] = df['BB_Width'].rolling(window=20).min()
            is_squeeze = df['BB_Width'].iloc[-1] <= (df['BB_Width_Min20'].iloc[-1] * 1.1) 
        else: is_squeeze = False

        demand_zones = find_demand_zones(df, atr_multiplier=0.25)
        supply_zones = find_supply_zones(df, atr_multiplier=0.25)
        
        last = df.iloc[-1]
        price = info.get('regularMarketPrice') if info.get('regularMarketPrice') else last['Close']
        ema20 = last['EMA20'] if 'EMA20' in last else np.nan
        ema50 = last['EMA50'] if 'EMA50' in last else np.nan
        ema200 = last['EMA200'] if 'EMA200' in last else np.nan
        
        if tf_code == "1wk":
            if ema200 is None or (isinstance(ema200, float) and np.isnan(ema200)):
                st.error(f"⚠️ **ข้อมูลไม่เพียงพอสำหรับ TF Week** (ต้องการ 200 สัปดาห์)")
                st.stop() 

        rsi = last['RSI'] if 'RSI' in last else np.nan
        atr = last['ATR'] if 'ATR' in last else np.nan
        vol_now = last['Volume']
        open_p = last['Open']; high_p = last['High']; low_p = last['Low']; close_p = last['Close']
        try: macd_val, macd_signal = last['MACD_12_26_9'], last['MACDs_12_26_9']
        except: macd_val, macd_signal = np.nan, np.nan
        try: adx_val = last['ADX_14']
        except: adx_val = np.nan
        if bbu_col_name and bbl_col_name: bb_upper, bb_lower = last[bbu_col_name], last[bbl_col_name]
        else: bb_upper, bb_lower = price * 1.05, price * 0.95
        vol_status, vol_color = analyze_volume(last, last['Vol_SMA20'])
        try: obv_val = last['OBV']; obv_avg = last['OBV_SMA20']
        except: obv_val = np.nan; obv_avg = np.nan
        obv_slope_val = last.get('OBV_Slope', np.nan)
        mtf_trend = "Sideway"; mtf_ema200_val = 0
        if df_mtf is not None and not df_mtf.empty:
            if 'EMA200' not in df_mtf.columns: df_mtf['EMA200'] = ta.ema(df_mtf['Close'], length=200)
            if len(df_mtf) > 200 and not pd.isna(df_mtf['EMA200'].iloc[-1]):
                mtf_ema200_val = df_mtf['EMA200'].iloc[-1]
                if df_mtf['Close'].iloc[-1] > mtf_ema200_val: mtf_trend = "Bullish"
                else: mtf_trend = "Bearish"
        
        try: prev_open = df['Open'].iloc[-2]; prev_close = df['Close'].iloc[-2]; vol_avg = last['Vol_SMA20']
        except: prev_open = 0; prev_close = 0; vol_avg = 1

        df_candles_4 = df.iloc[-4:] 

        # 🧠 CALL GOD MODE BRAIN
        ai_report = ai_hybrid_analysis(price, ema20, ema50, ema200, rsi, macd_val, macd_signal, adx_val, bb_upper, bb_lower, 
                                       vol_status, mtf_trend, atr, mtf_ema200_val,
                                       open_p, high_p, low_p, close_p, obv_val, obv_avg, obv_slope_val, 
                                       prev_open, prev_close, vol_now, vol_avg, demand_zones, is_squeeze, df_candles_4)

        # --- LOGGING ---
        current_time = datetime.now().strftime("%H:%M:%S")
        pct_change = info.get('regularMarketChangePercent', 0)
        pct_str = f"{pct_change * 100:+.2f}%" if pct_change is not None else "0.00%"

        raw_strat = ai_report['strategy']
        if "Aggressive Buy" in raw_strat: th_action = "ลุยซื้อ (Aggressive)"
        elif "Buy on Dip" in raw_strat: th_action = "ย่อซื้อ (Dip)"
        elif "Accumulate" in raw_strat: th_action = "ทยอยสะสม"
        elif "Wait" in raw_strat: th_action = "รอจังหวะ"
        elif "No Trade" in raw_strat: th_action = "ทับมือ (ห้ามเล่น)"
        elif "Exit" in raw_strat: th_action = "หนีตาย (Exit)"
        elif "Reduce" in raw_strat: th_action = "ลดพอร์ต"
        elif "Sell" in raw_strat: th_action = "เด้งขาย"
        else: th_action = raw_strat 

        raw_color = ai_report['status_color']
        th_score = "🟢 ขาขึ้น" if raw_color == "green" else "🔴 ขาลง" if raw_color == "red" else "🟠 เสี่ยง" if raw_color == "orange" else "🟡 พักตัว"

        log_entry = { 
            "เวลา": current_time, "หุ้น": symbol_input, "TF": timeframe, 
            "ราคา": f"{price:.2f}", "Change%": pct_str, "สถานะ": th_score,
            "Action": th_action, "SL": f"{ai_report['sl']:.2f}", "TP": f"{ai_report['tp']:.2f}"
        }
        
        if submit_btn: 
            st.session_state['history_log'].insert(0, log_entry)
            if len(st.session_state['history_log']) > 10: st.session_state['history_log'] = st.session_state['history_log'][:10]

        # --- DISPLAY UI ---
        logo_url = f"https://financialmodelingprep.com/image-stock/{symbol_input}.png"
        fallback_url = "https://cdn-icons-png.flaticon.com/512/720/720453.png"
        icon_html = f"""<img src="{logo_url}" onerror="this.onerror=null; this.src='{fallback_url}';" style="height: 50px; width: 50px; border-radius: 50%; vertical-align: middle; margin-right: 10px; object-fit: contain; background-color: white; border: 1px solid #e0e0e0; padding: 2px;">"""
        st.markdown(f"<h2 style='text-align: center; margin-top: -15px; margin-bottom: 25px;'>{icon_html} {info['longName']} ({symbol_input})</h2>", unsafe_allow_html=True)

        # Price Info
        c1, c2 = st.columns(2)
        with c1:
            reg_price, reg_chg = info.get('regularMarketPrice'), info.get('regularMarketChange')
            if reg_price and reg_chg: prev_c = reg_price - reg_chg; reg_pct = (reg_chg / prev_c) * 100 if prev_c != 0 else 0.0
            else: reg_pct = 0.0
            color_text = "#16a34a" if reg_chg and reg_chg > 0 else "#dc2626"; bg_color = "#e8f5ec" if reg_chg and reg_chg > 0 else "#fee2e2"
            st.markdown(f"""<div style="margin-bottom:5px; display: flex; align-items: center; gap: 15px; flex-wrap: wrap;"><div style="font-size:40px; font-weight:600; line-height: 1;">{reg_price:,.2f} <span style="font-size: 20px; color: #6b7280; font-weight: 400;">USD</span></div><div style="display:inline-flex; align-items:center; gap:6px; background:{bg_color}; color:{color_text}; padding:4px 12px; border-radius:999px; font-size:18px; font-weight:500;">{arrow_html(reg_chg)} {reg_chg:+.2f} ({reg_pct:.2f}%)</div></div>""", unsafe_allow_html=True)
            
            # --- New Fundamental Bar ---
            f_col1, f_col2, f_col3 = st.columns(3)
            with f_col1:
                mk_cap = info.get('marketCap')
                mk_cap_str = f"{mk_cap/1_000_000_000:.2f}B" if mk_cap else "N/A"
                st.markdown(f"<div class='fund-box'><div class='fund-label'>Market Cap</div><div class='fund-val'>{mk_cap_str}</div></div>", unsafe_allow_html=True)
            with f_col2:
                pe = info.get('trailingPE')
                pe_str = f"{pe:.2f}" if pe else "N/A"
                st.markdown(f"<div class='fund-box'><div class='fund-label'>P/E Ratio</div><div class='fund-val'>{pe_str}</div></div>", unsafe_allow_html=True)
            with f_col3:
                eps = info.get('trailingEps')
                eps_str = f"{eps:.2f}" if eps else "N/A"
                st.markdown(f"<div class='fund-box'><div class='fund-label'>EPS</div><div class='fund-val'>{eps_str}</div></div>", unsafe_allow_html=True)
            
        with c2:
            st_color = ai_report["status_color"]
            main_status = ai_report["banner_title"]
            if st_color == "green": st.success(f"📈 {main_status}\n\n**TF: {tf_code.upper()}**")
            elif st_color == "red": st.error(f"📉 {main_status}\n\n**TF: {tf_code.upper()}**")
            elif st_color == "orange": st.warning(f"⚠️ {main_status}\n\n**TF: {tf_code.upper()}**")
            else: st.warning(f"⚖️ {main_status}\n\n**TF: {tf_code.upper()}**")

        st.markdown("---")
        
        # --- 📊 INTERACTIVE CHART SECTION (New) ---
        st.subheader("📊 Interactive Chart & Analysis")
        chart_fig = plot_interactive_chart(df, symbol_input, ema20, ema50, ema200, demand_zones)
        st.plotly_chart(chart_fig, use_container_width=True)

        # --- METRICS ROW ---
        c3, c4 = st.columns(2)
        icon_flat_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="#a3a3a3"><circle cx="12" cy="12" r="10"/></svg>"""
        with c3:
            rsi_str = f"{rsi:.2f}" if not np.isnan(rsi) else "N/A"; rsi_text = get_rsi_interpretation(rsi, adx_val > 25)
            st.markdown(custom_metric_html("⚡ RSI (14)", rsi_str, rsi_text, "gray", icon_flat_svg), unsafe_allow_html=True)
        with c4:
            adx_disp = float(adx_val) if not np.isnan(adx_val) else np.nan
            is_uptrend = price >= ema200 if not np.isnan(ema200) else True
            adx_text = get_adx_interpretation(adx_disp, is_uptrend)
            adx_str = f"{adx_disp:.2f}" if not np.isnan(adx_disp) else "N/A"
            st.markdown(custom_metric_html("💪 ADX Strength", adx_str, adx_text, "gray", icon_flat_svg), unsafe_allow_html=True)

        st.write("") 
        c_ema, c_ai = st.columns([1.5, 2])
        
        with c_ema:
            st.subheader("📉 Technical Data")
            vol_str = format_volume(vol_now)
            e20_s = f"{ema20:.2f}" if not np.isnan(ema20) else "N/A"
            e50_s = f"{ema50:.2f}" if not np.isnan(ema50) else "N/A"
            e200_s = f"{ema200:.2f}" if (ema200 is not None and not np.isnan(ema200)) else "N/A"
            atr_pct = (atr / price) * 100 if not np.isnan(atr) and price > 0 else 0; atr_s = f"{atr:.2f} ({atr_pct:.1f}%)" if not np.isnan(atr) else "N/A"
            bb_s = f"{bb_upper:.2f} / {bb_lower:.2f}" if not np.isnan(bb_upper) else "N/A"

            st.markdown(f"""<div style='background-color: var(--secondary-background-color); padding: 15px; border-radius: 10px; font-size: 0.95rem;'><div style='display:flex; justify-content:space-between; margin-bottom:5px; border-bottom:1px solid #ddd; font-weight:bold;'><span>Indicator</span> <span>Value</span></div><div style='display:flex; justify-content:space-between;'><span>EMA 20</span> <span>{e20_s}</span></div><div style='display:flex; justify-content:space-between;'><span>EMA 50</span> <span>{e50_s}</span></div><div style='display:flex; justify-content:space-between;'><span>EMA 200</span> <span>{e200_s}</span></div><div style='display:flex; justify-content:space-between;'><span>Volume ({vol_str})</span> <span style='color:{ai_report['vol_quality_color']}'>{ai_report['vol_quality_msg']}</span></div><div style='display:flex; justify-content:space-between;'><span>ATR</span> <span>{atr_s}</span></div><div style='display:flex; justify-content:space-between;'><span>BB (Up/Low)</span> <span>{bb_s}</span></div></div>""", unsafe_allow_html=True)
            
            # --- Key Levels Logic (Compact) ---
            if tf_code == "1h": min_dist = atr * 1.0 
            else: min_dist = atr * 1.5 
            
            candidates_supp = []
            if not np.isnan(ema20) and ema20 < price: candidates_supp.append({'val': ema20, 'label': f"EMA 20"})
            if not np.isnan(ema50) and ema50 < price: candidates_supp.append({'val': ema50, 'label': f"EMA 50"})
            if not np.isnan(ema200) and ema200 < price: candidates_supp.append({'val': ema200, 'label': f"EMA 200"})
            if demand_zones:
                for z in demand_zones: candidates_supp.append({'val': z['bottom'], 'label': f"Demand Zone"})
            candidates_supp.sort(key=lambda x: x['val'], reverse=True)

            candidates_res = []
            if not np.isnan(ema20) and ema20 > price: candidates_res.append({'val': ema20, 'label': f"EMA 20"})
            if not np.isnan(ema50) and ema50 > price: candidates_res.append({'val': ema50, 'label': f"EMA 50"})
            if not np.isnan(ema200) and ema200 > price: candidates_res.append({'val': ema200, 'label': f"EMA 200"})
            if supply_zones:
                for z in supply_zones: candidates_res.append({'val': z['top'], 'label': f"Supply Zone"})
            candidates_res.sort(key=lambda x: x['val'])

            st.markdown("#### 🚧 Key Levels")
            if candidates_supp:
                st.markdown("**🟢 แนวรับ (Supports):**")
                for s in candidates_supp[:3]: st.write(f"- {s['val']:.2f} ({s['label']})")
            else: st.write("🚨 All Time Low / หลุดแนวรับ")
            
            if candidates_res:
                st.markdown("**🔴 แนวต้าน (Resistances):**")
                for r in candidates_res[:3]: st.write(f"- {r['val']:.2f} ({r['label']})")
            else: st.write("🚀 All Time High / ไร้ต้าน")

        with c_ai:
            st.subheader("🔬 Price Action X-Ray")
            sq_col = "#f97316" if ai_report['is_squeeze'] else "#0369a1"
            sq_txt = "⚠️ Squeeze (อัดอั้นรอระเบิด)" if ai_report['is_squeeze'] else "Normal (ปกติ)"
            vol_q_col = ai_report['vol_quality_color']
            obv_col = "#22c55e" if "Bullish" in ai_report['obv_insight'] or "ซื้อ" in ai_report['obv_insight'] else ("#ef4444" if "Bearish" in ai_report['obv_insight'] or "ขาย" in ai_report['obv_insight'] else "#6b7280")
            dz_status = "✅ อยู่ในโซน (In Zone)" if ai_report['in_demand_zone'] else "❌ นอกโซน"
            
            st.markdown(f"""
            <div class='xray-box'>
                <div class='xray-title'>🕯️ God Mode Insight</div>
                <div class='xray-item'><span>ทรงกราฟ:</span> <span style='font-weight:bold;'>{ai_report['candle_pattern']}</span></div>
                <div class='xray-item'><span>สถานะ:</span> <span>{ai_report['candle_color']}</span></div>
                <hr style='margin: 8px 0; opacity: 0.3;'>
                <div class='xray-item'><span>🔥 Volatility:</span> <span style='color:{sq_col}; font-weight:bold;'>{sq_txt}</span></div>
                <div class='xray-item'><span>🌊 Smart Flow (OBV):</span> <span style='color:{obv_col}; font-weight:bold;'>{ai_report['obv_insight']}</span></div>
                <div class='xray-item'><span>🎯 Demand Zone:</span> <span style='font-weight:bold;'>{dz_status}</span></div>
            </div>
            """, unsafe_allow_html=True)
            
            color_map = {
                "green": {"bg": "#dcfce7", "border": "#22c55e", "text": "#14532d"}, 
                "red": {"bg": "#fee2e2", "border": "#ef4444", "text": "#7f1d1d"}, 
                "orange": {"bg": "#ffedd5", "border": "#f97316", "text": "#7c2d12"}, 
                "yellow": {"bg": "#fef9c3", "border": "#eab308", "text": "#713f12"}
            }
            c_theme = color_map.get(ai_report['status_color'], color_map["yellow"])
            sl_val = ai_report['sl']; tp_val = ai_report['tp']

            html_strategy = f"""
            <div style="background-color: {c_theme['bg']}; border-left: 6px solid {c_theme['border']}; padding: 15px; border-radius: 8px; margin-bottom: 10px;">
                <h3 style="color: {c_theme['text']}; margin:0 0 5px 0;">{ai_report['banner_title']}</h3>
                <div style="font-weight: 500; color: {c_theme['text']}; opacity:0.9;">Strategy: {ai_report['strategy']}</div>
                <div style="margin-top: 10px; font-weight: bold; color: {c_theme['text']};">
                    SL: {sl_val:.2f} | TP: {tp_val:.2f}
                </div>
            </div>
            """
            st.markdown(html_strategy, unsafe_allow_html=True)

            with st.chat_message("assistant"):
                st.markdown("**🤖 AI Rationale:**")
                for r in ai_report['bullish_factors']: st.write(f"- 🟢 {r}")
                for w in ai_report['bearish_factors']: st.write(f"- 🔴 {w}")

        # --- News Feed Section (New) ---
        st.markdown("---")
        st.subheader(f"📰 News Feed for {symbol_input}")
        
        try:
            news = yf.Ticker(symbol_input).news
            if news:
                news_cols = st.columns(3)
                for i, n in enumerate(news[:3]):
                    with news_cols[i]:
                        with st.container(border=True):
                            st.markdown(f"**{n['title']}**")
                            pub_time = datetime.fromtimestamp(n['providerPublishTime']).strftime('%Y-%m-%d %H:%M')
                            st.caption(f"{n['publisher']} • {pub_time}")
                            if 'link' in n:
                                st.markdown(f"[Read more]({n['link']})")
            else:
                st.info("No recent news found.")
        except:
            st.info("Could not fetch news.")

        # --- Footer & Logs ---
        st.markdown("---")
        col_btn, col_info = st.columns([2, 4])
        with col_btn:
            if st.session_state['history_log']:
                latest_data = st.session_state['history_log'][0]
                save_key = f"save_{latest_data['หุ้น']}_{latest_data['เวลา']}"
                if st.button(f"💾 บันทึก {latest_data['หุ้น']} ลง Sheet", type="primary", use_container_width=True, key=save_key):
                    with st.spinner("Saving..."):
                        if save_to_gsheet(latest_data): st.toast("Saved!", icon="✅")
                        else: st.error("Save Failed")
        
        st.divider()
        st.subheader("📜 History Log")
        if st.session_state['history_log']: 
            df_hist = pd.DataFrame(st.session_state['history_log'])
            cols_to_show = ["เวลา", "หุ้น", "TF", "ราคา", "Change%", "สถานะ", "Action", "SL", "TP"]
            st.dataframe(df_hist[cols_to_show], use_container_width=True, hide_index=True)
    else: 
        st.error("ไม่พบข้อมูลหุ้น หรือข้อมูลไม่เพียงพอสำหรับคำนวณ (ต้องมีมากกว่า 20 แท่ง)")

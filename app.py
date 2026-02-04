import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime, timedelta

# --- Import สำหรับ Google Sheets ---
# (ถ้ายังไม่มี JSON Key ให้ข้ามส่วนนี้ไป หรือ Comment ออก)
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. ตั้งค่าหน้าเว็บ (The Master Version) ---
st.set_page_config(page_title="AI Stock Master (Pro Hybrid)", page_icon="💎", layout="wide")

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
    .xray-box {
        background-color: #f0f9ff; border: 1px solid #bae6fd;
        border-radius: 10px; padding: 15px; margin-bottom: 20px;
    }
    .xray-title {
        font-weight: bold; color: #0369a1; font-size: 1.1rem;
        margin-bottom: 10px; border-bottom: 1px solid #e0f2fe; padding-bottom: 5px;
    }
    .xray-item {
        display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 0.95rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ส่วนหัวข้อ ---
st.markdown("<h1>💎 Ai<br><span style='font-size: 1.5rem; opacity: 0.7;'>Ultimate Sniper (Pro Logic + Context)🚀</span></h1>", unsafe_allow_html=True)

# --- Form ค้นหา ---
col_space1, col_form, col_space2 = st.columns([1, 2, 1])
with col_form:
    with st.form(key='search_form'):
        st.markdown("### 🔍 ค้นหาหุ้น")
        c1, c2 = st.columns([3, 1])
        with c1:
            symbol_input_raw = st.text_input("ชื่อหุ้น (เช่น AMZN,TSLA,BTC-USD)🪐", value="").upper().strip()
        with c2:
            timeframe = st.selectbox("Timeframe:", ["1h (รายชั่วโมง)", "1d (รายวัน)", "1wk (รายสัปดาห์)"], index=1)
            if "1wk" in timeframe: tf_code = "1wk"; mtf_code = "1mo"
            elif "1h" in timeframe: tf_code = "1h"; mtf_code = "1d"
            else: tf_code = "1d"; mtf_code = "1wk"
        st.markdown("---")
        submit_btn = st.form_submit_button("🚀 วิเคราะห์ทันที")

# --- 4. Helper Functions ---

def analyze_candlestick(open_price, high, low, close):
    body = abs(close - open_price)
    wick_upper = high - max(close, open_price)
    wick_lower = min(close, open_price) - low
    total_range = high - low
    
    color = "🟢 เขียว (Buying)" if close >= open_price else "🔴 แดง (Selling)"
    if total_range == 0: return "Doji (N/A)", color, "N/A", False

    pattern_name = "Normal Candle (ปกติ)"
    detail = "แรงซื้อขายสมดุล"
    is_big = False

    if wick_lower > (body * 2) and wick_upper < body:
        pattern_name = "Hammer/Pinbar (ค้อน)"
        detail = "ปฏิเสธราคาต่ำ (แรงซื้อสวนกลับ)"
    elif wick_upper > (body * 2) and wick_lower < body:
        pattern_name = "Shooting Star (ดาวตก)"
        detail = "ปฏิเสธราคาสูง (โดนตบหัวทิ่ม)"
    elif body > (total_range * 0.6): 
        is_big = True
        if close > open_price: 
            pattern_name = "Big Bullish (แท่งเขียวตัน)"
            detail = "แรงซื้อคุมตลาดเบ็ดเสร็จ"
        else: 
            pattern_name = "Big Bearish (แท่งแดงตัน)"
            detail = "แรงขายคุมตลาดเบ็ดเสร็จ"
    elif body < (total_range * 0.1):
        pattern_name = "Doji (โดจิ)"
        detail = "ตลาดลังเล (Indecision)"
        
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

def get_rsi_interpretation(rsi, is_strong_trend):
    if np.isnan(rsi): return "N/A"
    if is_strong_trend:
        if rsi >= 75: return "Extreme Bullish (แรงสุดๆ)"
        if rsi <= 40: return "Dip Opportunity (ย่อซื้อ)"
        return "Trending Up"
    else:
        if rsi >= 70: return "Overbought (ระวังแรงขาย)"
        if rsi <= 30: return "Oversold (ระวังเด้งสวน)"
        return "Neutral"

def get_adx_interpretation(adx):
    if np.isnan(adx): return "N/A"
    if adx >= 50: return "Super Strong Trend"
    if adx >= 25: return "Strong Trend (มีเทรนด์)"
    return "Weak/Sideway (ไซด์เวย์)"

# --- Google Sheets Function (Code 1 Feature) ---
def save_to_gsheet(data_dict):
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        # ⚠️ ต้องมี secrets.toml ถึงจะใช้ได้
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)
            sheet = client.open("Stock_Analysis_Log").sheet1
            row = [
                datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%H:%M:%S"),
                data_dict.get("หุ้น", ""), data_dict.get("ราคา", ""),
                data_dict.get("Score", ""), data_dict.get("คำแนะนำ", ""), data_dict.get("Action", ""),
            ]
            sheet.append_row(row)
            return True
        else:
            return False # ไม่มี Secret
    except Exception as e:
        return False

# --- SMC: Find Zones (Logic เดิมที่ถูกต้อง) ---

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
        
        # Distance Filter 20%
        if (current_price - zone_top) / current_price > 0.20: continue
        
        future_data = df.loc[date:][1:]
        if future_data.empty: continue
        # Broken check
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
        else:
            price = df['Close'].iloc[-1]; chg = 0; pct = 0

        info_dict = {
            'longName': raw_info.get('longName', symbol), 
            'marketState': raw_info.get('marketState', 'REGULAR'), 
            'regularMarketPrice': price, 'regularMarketChange': chg,
            'regularMarketChangePercent': pct,
            'preMarketPrice': raw_info.get('preMarketPrice'), 'preMarketChange': raw_info.get('preMarketChange'),
            'postMarketPrice': raw_info.get('postMarketPrice'), 'postMarketChange': raw_info.get('postMarketChange'),
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

# --- 7. AI Decision Engine (PRO LOGIC: Context Aware) ---

def ai_hybrid_analysis(price, ema20, ema50, ema200, rsi, macd_val, macd_sig, adx, bb_up, bb_low, 
                       vol_status, mtf_trend, atr_val, mtf_ema200_val,
                       open_price, high, low, close, obv_val, obv_avg,
                       obv_slope, prev_open, prev_close, vol_now, vol_avg, demand_zones,
                       is_squeeze):

    def safe(x): return float(x) if not np.isnan(float(x)) else np.nan
    price = safe(price); ema20 = safe(ema20); ema50 = safe(ema50); ema200 = safe(ema200)
    atr_val = safe(atr_val); obv_slope = safe(obv_slope)

    # 1. Pattern & Regime
    candle_pattern, candle_color, candle_detail, is_big_candle = analyze_candlestick(open_price, high, low, close)
    is_reversal = "Hammer" in candle_pattern or "Doji" in candle_pattern
    vol_txt, vol_col = analyze_volume({'Volume': vol_now}, vol_avg)
    
    # ADX Regime: >25 Trending, <25 Sideway
    is_strong_trend = adx > 25 if not np.isnan(adx) else False
    
    # Zone Check
    in_demand_zone = False; active_zone = None
    if demand_zones:
        for zone in demand_zones:
            if (low <= zone['top'] * 1.01) and (high >= zone['bottom']): # Buffer 1%
                in_demand_zone = True; active_zone = zone; break

    # --- SCORING (Weighted) ---
    score = 0
    bullish, bearish = [], []

    # A. Trend (EMA200 King)
    if not np.isnan(ema200):
        if price > ema200: score += 3; bullish.append("ยืนเหนือ EMA 200 (เทรนด์หลักขาขึ้น)")
        else: score -= 3; bearish.append("หลุด EMA 200 (เทรนด์หลักขาลง)")

    if not np.isnan(ema50):
        if price > ema50: score += 2; bullish.append("ยืนเหนือ EMA 50 (ระยะกลางแกร่ง)")
        else: score -= 1; bearish.append("หลุด EMA 50 (ระยะกลางเสียทรง)")

    # B. Momentum (Context Aware)
    if not np.isnan(macd_val) and macd_val > macd_sig: score += 1; bullish.append("MACD ตัดขึ้น")
    
    if not np.isnan(rsi):
        if is_strong_trend and price > ema200: # Trending Up
            if rsi > 70: score += 1; bullish.append(f"RSI {rsi:.0f} (Super Momentum)")
            elif rsi < 40: score += 2; bullish.append(f"RSI {rsi:.0f} (Dip ในขาขึ้น)")
        elif is_strong_trend and price < ema200: # Trending Down
            if rsi < 30: score -= 1; bearish.append(f"RSI {rsi:.0f} (Super Bearish)")
            elif rsi > 60: score -= 2; bearish.append(f"RSI {rsi:.0f} (Rebound เพื่อลง)")
        else: # Sideway
            if rsi > 70: score -= 2; bearish.append(f"RSI {rsi:.0f} (Overbought ในไซด์เวย์)")
            elif rsi < 30: score += 2; bullish.append(f"RSI {rsi:.0f} (Oversold ในไซด์เวย์)")

    # C. Smart OBV (Intensity Levels)
    has_bearish_div = False
    obv_insight = "Volume Flow ปกติ"
    if not np.isnan(obv_slope):
        # Bullish Div
        if price < ema20 and obv_slope > 0:
            score += 2
            lvl = "กวาดซื้อด่วน" if obv_slope > 100000 else "แอบเก็บของ" # Mock threshold
            bullish.append(f"💎 Smart OBV: Bullish Div ({lvl})")
            obv_insight = f"Bullish Div ({lvl})"
        # Bearish Div
        elif price > ema20 and obv_slope < 0:
            has_bearish_div = True
            score -= 4 # Veto Penalty
            lvl = "เทกระจาด" if obv_slope < -100000 else "รินขาย"
            bearish.append(f"⚠️ Smart OBV: Bearish Div ({lvl})")
            obv_insight = f"Bearish Div ({lvl})"

    # D. Situation Logic
    context_status = ""
    
    if is_squeeze: context_status = "💣 BB Squeeze (รอระเบิด)"
    
    if in_demand_zone:
        if has_bearish_div:
            score -= 2; bearish.append("🚫 Demand Zone เสี่ยง (เจ้าออกของ)")
            context_status = "⚠️ Trap Risk (ราคาลงแนวรับแต่เงินออก)"
        else:
            score += 3; bullish.append("🟢 In Demand Zone")
            if is_reversal: score += 1; bullish.append("🕯️ แท่งเทียนกลับตัวในโซน")
            context_status = "💎 Sniper Mode (เข้าโซนสวย)"

    # --- SAFETY VETO ---
    if has_bearish_div and score > 0: score = 0 # Veto Buy
    if "ระเบิด" in vol_txt and close < open_price: score = -10; context_status = "🩸 Panic Sell (หนีตาย)"

    # --- FINAL CONTEXTUAL MAPPING (เพิ่มสถานะ เด้งเพื่อลง / ย่อเพื่อขึ้น) ---
    banner_title = ""; strategy = ""; advice = ""; color = ""
    
    # 1. เช็ค Rebound to Drop (ขาลง เด้งมาชนต้าน)
    is_downtrend = price < ema200 if not np.isnan(ema200) else False
    is_rebound = rsi > 50 if not np.isnan(rsi) else False
    hit_resistance = (high >= ema50) or (high >= ema20)
    
    # 2. เช็ค Bullish Pullback (ขาขึ้น ย่อมาชนรับ)
    is_uptrend = price > ema200 if not np.isnan(ema200) else False
    is_dip = rsi < 50 if not np.isnan(rsi) else False
    
    if score <= -2 and is_downtrend and is_rebound and hit_resistance:
        color = "orange"; banner_title = "📉 Rebound to Drop: เด้งเพื่อลงต่อ"; strategy = "Short / Sell on Rally"
        advice = "ราคาดีดตัวในขาลง ชนแนวต้านแล้วหมดแรง เป็นจังหวะออกของ"
        context_status = "Bearish Pullback Pattern"
        
    elif score >= 3 and is_uptrend and is_dip:
        color = "green"; banner_title = "🐂 Bullish Pullback: ย่อเพื่อไปต่อ"; strategy = "Buy on Dip"
        advice = "ราคาย่อตัวในเทรนด์ขาขึ้น เป็นโอกาสสะสมที่ดีที่สุด"
        context_status = "Healthy Correction Pattern"
        
    elif score >= 5:
        color = "green"; banner_title = "🚀 Sniper Entry: จุดซื้อคมกริบ"; strategy = "Aggressive Buy"
        advice = f"เทรนด์แกร่ง ถือรันเทรนด์ SL: {low-(atr_val*1.0):.2f}"
        
    elif score >= 1:
        color = "yellow"; banner_title = "⚖️ Neutral: ไซด์เวย์"; strategy = "Wait & See"
        advice = "ตลาดเลือกทาง หรือพักตัว เฝ้าดูโซนรับ"
        
    elif score <= -3:
        color = "red"; banner_title = "🩸 Falling Knife: มีดหล่น"; strategy = "Cut Loss"
        advice = "ห้ามรับ! แรงขายรุนแรง รอสร้างฐานใหม่"
        
    else:
        color = "orange"; banner_title = "🐻 Bearish: แรงกดดันสูง"; strategy = "Avoid"
        advice = "เทรนด์อ่อนแอ เด้งขาย หรือชะลอการลงทุน"

    if in_demand_zone: sl = active_zone['bottom'] - (atr_val*0.5)
    else: sl = price - (2*atr_val) if not np.isnan(atr_val) else price*0.95
    tp = price + (3*atr_val) if not np.isnan(atr_val) else price*1.05

    return {
        "color": color, "title": banner_title, "strat": strategy, "ctx": context_status,
        "bull": bullish, "bear": bearish, "sl": sl, "tp": tp, "adv": advice,
        "c_pat": candle_pattern, "c_col": candle_color, "c_det": candle_detail,
        "v_txt": vol_txt, "v_col": vol_col, "in_zone": in_demand_zone,
        "sq": is_squeeze, "obv": obv_insight
    }

# --- 8. Main Execution ---

if submit_btn:
    st.session_state['search_triggered'] = True
    st.session_state['last_symbol'] = symbol_input_raw

if st.session_state['search_triggered']:
    symbol = st.session_state['last_symbol']
    st.divider()
    
    with st.spinner(f"AI Hybrid Pro กำลังวิเคราะห์ {symbol} ..."):
        df, info, df_mtf = get_data_hybrid(symbol, tf_code, mtf_code)
        
    if df is not None and not df.empty and len(df) > 20:
        # Indicators
        df['EMA20'] = ta.ema(df['Close'], length=20)
        df['EMA50'] = ta.ema(df['Close'], length=50)
        ema200_s = ta.ema(df['Close'], length=200)
        df['EMA200'] = ema200_s if ema200_s is not None else np.nan
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        macd = ta.macd(df['Close']); df = pd.concat([df, macd], axis=1)
        bb = ta.bbands(df['Close'], length=20, std=2)
        if bb is not None: df = pd.concat([df, bb], axis=1)
        adx = ta.adx(df['High'], df['Low'], df['Close'], length=14); df = pd.concat([df, adx], axis=1)
        df['Vol_MA'] = ta.sma(df['Volume'], length=20)
        
        # OBV
        df['OBV'] = ta.obv(df['Close'], df['Volume'])
        df['OBV_Slope'] = ta.slope(df['OBV'], length=5)
        
        # Squeeze
        if 'BBU_20_2.0' in df.columns:
            df['Width'] = (df['BBU_20_2.0'] - df['BBL_20_2.0']) / df['EMA20']
            is_sq = df['Width'].iloc[-1] < df['Width'].rolling(20).min().iloc[-1] * 1.1
        else: is_sq = False
        
        # Zones
        d_zones = find_demand_zones(df)
        s_zones = find_supply_zones(df)
        
        # Last Values
        last = df.iloc[-1]
        price = info['regularMarketPrice']
        
        # 🛑 Week Check
        if tf_code == "1wk" and np.isnan(last['EMA200']):
            st.error("⚠️ ข้อมูล Week ไม่พอคำนวณ EMA200 (ต้องการ 4-5 ปี)"); st.stop()

        # AI RUN
        rpt = ai_hybrid_analysis(
            price, last['EMA20'], last['EMA50'], last['EMA200'], last['RSI'],
            last.get('MACD_12_26_9'), last.get('MACDs_12_26_9'), last.get('ADX_14'),
            last.get('BBU_20_2.0'), last.get('BBL_20_2.0'), "", "", last['ATR'], 0,
            last['Open'], last['High'], last['Low'], last['Close'], 0, 0,
            last.get('OBV_Slope'), 0, 0, last['Volume'], last['Vol_MA'], d_zones, is_sq
        )
        
        # LOG
        log_entry = {"หุ้น": symbol, "ราคา": f"{price:.2f}", "Score": rpt['color'].upper(), "คำแนะนำ": rpt['title'], "Action": rpt['strat']}
        if submit_btn: st.session_state['history_log'].insert(0, log_entry)

        # --- DISPLAY ---
        st.markdown(f"<h2 style='text-align:center;'>{symbol} : {info['longName']}</h2>", unsafe_allow_html=True)
        
        # Status Box
        c_theme = {"green": "#dcfce7", "red": "#fee2e2", "orange": "#ffedd5", "yellow": "#fef9c3"}.get(rpt['color'], "#fef9c3")
        st.markdown(f"""
        <div style="background:{c_theme}; padding:20px; border-radius:10px; border-left:6px solid {rpt['color']}; margin-bottom:20px;">
            <h2 style="margin:0; color:#333;">{rpt['title']}</h2>
            <h3 style="margin:5px 0 0 0; color:#555;">{rpt['strat']}</h3>
            <p style="margin:5px 0 0 0;"><b>💡 Context:</b> {rpt['ctx']}</p>
        </div>
        """, unsafe_allow_html=True)

        # Columns
        c1, c2 = st.columns([1, 1.5])
        with c1:
            st.subheader("📊 Key Indicators")
            rsi_txt = get_rsi_interpretation(last['RSI'], last.get('ADX_14',0)>25)
            st.markdown(custom_metric_html("Price", f"{price:.2f}", f"{info['regularMarketChangePercent']:.2f}%", "green" if info['regularMarketChangePercent']>0 else "red", ""), unsafe_allow_html=True)
            st.markdown(custom_metric_html("RSI", f"{last['RSI']:.2f}", rsi_txt, "gray", ""), unsafe_allow_html=True)
            st.markdown(custom_metric_html("OBV Insight", rpt['obv'], "", "gray", ""), unsafe_allow_html=True)
            
            # X-Ray
            st.markdown(f"""
            <div class='xray-box'>
                <div class='xray-title'>🕯️ X-Ray Insight</div>
                <div class='xray-item'><span>Pattern:</span> <b>{rpt['c_pat']}</b></div>
                <div class='xray-item'><span>Volume:</span> <span style='color:{rpt['v_col']}'>{rpt['v_txt']}</span></div>
                <div class='xray-item'><span>Zone:</span> <b>{'✅ In Zone' if rpt['in_zone'] else '❌ Out Zone'}</b></div>
            </div>
            """, unsafe_allow_html=True)

        with c2:
            st.subheader("🚧 Smart Levels (Code 2 Logic)")
            
            # --- SUPPORTS (VIP Logic Restoration) ---
            supps = []
            if not np.isnan(last['EMA20']) and last['EMA20'] < price: supps.append({'v': last['EMA20'], 'l': f"EMA 20 ({tf_code})"})
            if not np.isnan(last['EMA50']) and last['EMA50'] < price: supps.append({'v': last['EMA50'], 'l': f"EMA 50 ({tf_code})"})
            if not np.isnan(last['EMA200']) and last['EMA200'] < price: supps.append({'v': last['EMA200'], 'l': f"🛡️ EMA 200 (Trend Wall)"})
            for z in d_zones: supps.append({'v': z['bottom'], 'l': f"Demand Zone [{z['bottom']:.2f}-{z['top']:.2f}]"})
            
            # Sort & Filter (Simple Dist + VIP)
            supps.sort(key=lambda x: x['v'], reverse=True)
            final_supp = []
            for s in supps:
                if not final_supp: final_supp.append(s)
                else:
                    if abs(final_supp[-1]['v'] - s['v']) > last['ATR']*0.5 or "EMA 200" in s['l']: # VIP Rule
                        final_supp.append(s)

            st.markdown("#### 🟢 แนวรับ")
            for s in final_supp[:4]: st.write(f"- **{s['v']:.2f}**: {s['l']}")

            # --- RESISTANCE ---
            res = []
            if not np.isnan(last['EMA20']) and last['EMA20'] > price: res.append({'v': last['EMA20'], 'l': f"EMA 20 ({tf_code})"})
            if not np.isnan(last['EMA50']) and last['EMA50'] > price: res.append({'v': last['EMA50'], 'l': f"EMA 50 ({tf_code})"})
            if not np.isnan(last['EMA200']) and last['EMA200'] > price: res.append({'v': last['EMA200'], 'l': f"EMA 200 (Major Res)"})
            for z in s_zones: res.append({'v': z['top'], 'l': f"Supply Zone [{z['bottom']:.2f}-{z['top']:.2f}]"})
            
            res.sort(key=lambda x: x['v'])
            final_res = []
            for r in res:
                if not final_res: final_res.append(r)
                else:
                    if abs(final_res[-1]['v'] - r['v']) > last['ATR']*0.5 or "EMA 200" in r['l']:
                        final_res.append(r)
                        
            st.markdown("#### 🔴 แนวต้าน")
            for r in final_res[:4]: st.write(f"- **{r['v']:.2f}**: {r['l']}")

        # --- Assistant Chat ---
        st.markdown("---")
        with st.chat_message("assistant"):
            st.write("#### 🤖 AI Analysis Report")
            if rpt['bull']: 
                st.markdown("**ปัจจัยบวก:**")
                for b in rpt['bull']: st.markdown(f"- 🟢 {b}")
            if rpt['bear']: 
                st.markdown("**ปัจจัยลบ/ความเสี่ยง:**")
                for b in rpt['bear']: st.markdown(f"- 🔴 {b}")
            
            st.info(f"**คำแนะนำ (Advice):** {rpt['adv']}\n\n🛑 Stop Loss: {rpt['sl']:.2f} | ✅ Take Profit: {rpt['tp']:.2f}")

        # --- GSheet Button (Optional) ---
        if st.button("💾 Save to Google Sheet"):
            if save_to_gsheet(log_entry): st.success("Saved!")
            else: st.error("บันทึกไม่ได้ (ตรวจสอบ secrets.toml)")

        # History
        if st.session_state['history_log']:
            st.markdown("---")
            st.subheader("📜 History")
            st.dataframe(pd.DataFrame(st.session_state['history_log']))

    else: st.error("Data Not Found")

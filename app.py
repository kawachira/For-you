import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime, timedelta

# --- 1. ตั้งค่าหน้าเว็บ (The Master Version) ---
st.set_page_config(page_title="AI Stock Master (SMC)", page_icon="💎", layout="wide")

# --- Initialize Session State for History ---
if 'history_log' not in st.session_state:
    st.session_state['history_log'] = []

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
    /* Fundamental Box Style */
    .fund-box {
        padding: 10px;
        border-radius: 8px;
        margin-bottom: 5px;
        font-size: 0.9rem;
    }
    .fund-good { background-color: #dcfce7; color: #14532d; border: 1px solid #22c55e; }
    .fund-mid { background-color: #fef9c3; color: #713f12; border: 1px solid #eab308; }
    .fund-bad { background-color: #fee2e2; color: #7f1d1d; border: 1px solid #ef4444; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ส่วนหัวข้อ ---
st.markdown("<h1>💎 Ai<br><span style='font-size: 1.5rem; opacity: 0.7;'>Ultimate Sniper (SMC + OBV Hybrid)🚀</span></h1>", unsafe_allow_html=True)

# --- Form ค้นหา ---
col_space1, col_form, col_space2 = st.columns([1, 2, 1])
with col_form:
    with st.form(key='search_form'):
        st.markdown("### 🔍 ค้นหาหุ้น")
        c1, c2 = st.columns([3, 1])
        with c1:
            symbol_input = st.text_input("ชื่อหุ้น (เช่น AMZN,EOSE,RKLB,TSLA)🪐", value="").upper().strip()
        with c2:
            timeframe = st.selectbox("Timeframe:", ["1h (รายชั่วโมง)", "1d (รายวัน)", "1wk (รายสัปดาห์)"], index=1)
            if "1wk" in timeframe: tf_code = "1wk"; mtf_code = "1mo"
            elif "1h" in timeframe: tf_code = "1h"; mtf_code = "1d"
            else: tf_code = "1d"; mtf_code = "1wk"
        
        st.markdown("---")
        submit_btn = st.form_submit_button("🚀 วิเคราะห์ทันที")

# --- 4. Helper Functions ---

def analyze_candlestick(open_price, high, low, close):
    """ฟังก์ชันอ่านแท่งเทียน (Tuned Sensitivity 0.6)"""
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
        detail = "มีการปฏิเสธราคาต่ำ (แรงซื้อสวนกลับดันราคาขึ้น)"
    elif wick_upper > (body * 2) and wick_lower < body:
        pattern_name = "Shooting Star (ดาวตก)"
        detail = "มีการปฏิเสธราคาสูง (โดนตบหัวทิ่ม/แรงขายกดดัน)"
    elif body > (total_range * 0.6): 
        is_big = True
        if close > open_price: 
            pattern_name = "Big Bullish Candle (แท่งเขียวตัน)"
            detail = "แรงซื้อคุมตลาดเบ็ดเสร็จ (Strong Momentum)"
        else: 
            pattern_name = "Big Bearish Candle (แท่งแดงตัน)"
            detail = "แรงขายคุมตลาดเบ็ดเสร็จ (Panic Sell)"
    elif body < (total_range * 0.1):
        pattern_name = "Doji (โดจิ)"
        detail = "ตลาดเกิดความลังเล (Indecision) รอเลือกทาง"
        
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
    if color_status == "green": color_code = "#16a34a"
    elif color_status == "red": color_code = "#dc2626"
    else: color_code = "#a3a3a3"
    
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

def get_rsi_interpretation(rsi):
    if np.isnan(rsi): return "N/A"
    if rsi >= 70: return "Overbought (ระวังแรงขาย)"
    elif rsi >= 55: return "Bullish (กระทิงแข็งแกร่ง)"
    elif rsi >= 45: return "Sideway/Neutral (รอเลือกทาง)"
    elif rsi >= 30: return "Bearish (หมีครองตลาด)"
    else: return "Oversold (ระวังเด้งสวน)"

def get_adx_interpretation(adx, is_uptrend):
    if np.isnan(adx): return "N/A"
    trend_str = "ขาขึ้น" if is_uptrend else "ขาลง"
    if adx >= 50: return f"Super Strong {trend_str} (แรงมาก)"
    if adx >= 25: return f"Strong {trend_str} (แข็งแกร่ง)"
    if adx >= 20: return "Developing Trend (เริ่มก่อตัว)"
    return "Weak/Sideway (ตลาดไร้ทิศทาง)"

def filter_levels(levels, threshold_pct=0.025):
    selected = []
    for val, label in levels:
        if np.isnan(val): continue
        label = label.replace("BB Lower (Volatility)", "BB Lower (กรอบล่าง)").replace("Low 60 Days (Price Action)", "Low 60 วัน (ฐานราคา)").replace("EMA 200 (Trend Wall)", "EMA 200 (เทรนด์หลัก)").replace("EMA 50 (Short Trend)", "EMA 50 (ระยะกลาง)").replace("EMA 20 (Momentum)", "EMA 20 (โมเมนตัม)").replace("BB Upper (Ceiling)", "BB Upper (ต้านใหญ่)").replace("High 60 Days (Peak)", "High 60 วัน (ยอดดอย)")
        if "MTF" in label or "1wk" in label.lower() or "1mo" in label.lower(): label = "EMA 200 (TF ใหญ่)"
        if not selected: selected.append((val, label))
        else:
            last_val = selected[-1][0]; diff = abs(val - last_val) / last_val
            if diff > threshold_pct: selected.append((val, label))
    return selected

# --- NEW: Fundamental Analysis Function ---
def analyze_fundamental(info):
    pe = info.get('trailingPE', None)
    eps_growth = info.get('earningsQuarterlyGrowth', None)
    rev_growth = info.get('revenueGrowth', None)
    
    score = 0
    status = "Neutral"
    color_class = "fund-mid"
    summary_text = "ข้อมูลพื้นฐานกลางๆ"
    advice = "เล่นตามรอบ (Swing Trade)"

    if pe:
        if pe < 0: score -= 2
        elif pe < 20: score += 1
        elif pe > 50: score -= 1
    
    if eps_growth:
        growth_pct = eps_growth * 100
        if growth_pct > 15: score += 2
        elif growth_pct > 0: score += 1
        else: score -= 2
    
    if score >= 2:
        status = "Strong Fundamental (งบดี)"
        color_class = "fund-good"
        summary_text = "✅ **งบแกร่ง:** กำไรเติบโตดี/ราคาไม่แพงเวอร์"
        advice = "💎 **ถือยาวได้ / ใส่เงินเยอะได้ (Investable)**"
    elif score <= -2:
        status = "Weak Fundamental (งบเน่า)"
        color_class = "fund-bad"
        summary_text = "🔴 **งบแย่:** ขาดทุนหรือกำไรถดถอย"
        advice = "⚠️ **เก็งกำไรสั้นๆ เท่านั้น / ห้ามถือยาว (Speculative)**"
    else:
        status = "Moderate (งบกลางๆ)"
        color_class = "fund-mid"
        summary_text = "⚖️ **งบกลางๆ:** พอไปวัดไปวาได้"
        advice = "🔄 **เล่นตามรอบเทคนิค (Swing Trade)**"

    return {"status": status, "color_class": color_class, "summary": summary_text, "advice": advice, "pe": f"{pe:.2f}" if pe else "N/A", "growth": f"{eps_growth*100:.2f}%" if eps_growth else "N/A"}

# --- SMC: Find Zones ---
def find_demand_zones(df, atr_multiplier=0.25):
    """ ค้นหา Demand Zones (Swing Low) """
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
            test_count = ((future_data['Low'] <= zone_top) & (future_data['Low'] >= zone_bottom)).sum()
            zones.append({'bottom': zone_bottom, 'top': zone_top, 'type': 'Fresh' if test_count == 0 else 'Tested'})
    return zones

def find_supply_zones(df, atr_multiplier=0.25):
    """ ค้นหา Supply Zones (Swing High) - สำหรับแนวต้าน """
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
        
        # Filter: ถ้าโซนอยู่สูงเกิน 20% ของราคาปัจจุบัน ให้ข้าม (ลด Noise)
        if (zone_bottom - current_price) / current_price > 0.20: continue

        future_data = df.loc[date:][1:]
        if future_data.empty: continue
        # Fresh Check: ราคายังไม่เคยปิดทะลุ High ขึ้นไป
        if not (future_data['Close'] > zone_top).any():
            zones.append({'bottom': zone_bottom, 'top': zone_top, 'type': 'Fresh'})
            
    return zones

# --- 5. Data Fetching ---
@st.cache_data(ttl=60, show_spinner=False)
def get_data_hybrid(symbol, interval, mtf_interval):
    try:
        ticker = yf.Ticker(symbol)
        if interval == "1wk": period_val = "10y"
        elif interval == "1d": period_val = "5y"
        else: period_val = "730d"
        df = ticker.history(period=period_val, interval=interval)
        df_mtf = ticker.history(period="10y", interval=mtf_interval)
        if not df_mtf.empty: df_mtf['EMA200'] = ta.ema(df_mtf['Close'], length=200)
        
        try: raw_info = ticker.info 
        except: raw_info = {} 

        df_daily_header = ticker.history(period="5d", interval="1d")
        if not df_daily_header.empty:
            header_price = df_daily_header['Close'].iloc[-1]
            header_change = header_price - df_daily_header['Close'].iloc[-2] if len(df_daily_header) >=2 else 0
            header_pct = (header_change / df_daily_header['Close'].iloc[-2]) if len(df_daily_header) >=2 else 0
            d_h, d_l, d_o = df_daily_header['High'].iloc[-1], df_daily_header['Low'].iloc[-1], df_daily_header['Open'].iloc[-1]
        else:
            header_price = df['Close'].iloc[-1]
            header_change, header_pct = 0, 0
            d_h, d_l, d_o = df['High'].iloc[-1], df['Low'].iloc[-1], df['Open'].iloc[-1]

        stock_info = {
            'longName': raw_info.get('longName', symbol), 
            'marketState': raw_info.get('marketState', 'REGULAR'), 
            'trailingPE': raw_info.get('trailingPE', None), 
            'earningsQuarterlyGrowth': raw_info.get('earningsQuarterlyGrowth', None),
            'revenueGrowth': raw_info.get('revenueGrowth', None),
            'regularMarketPrice': header_price, 'regularMarketChange': header_change,
            'regularMarketChangePercent': header_pct, 'dayHigh': d_h, 'dayLow': d_l, 'regularMarketOpen': d_o,
            'preMarketPrice': raw_info.get('preMarketPrice'), 'preMarketChange': raw_info.get('preMarketChange'),
            'postMarketPrice': raw_info.get('postMarketPrice'), 'postMarketChange': raw_info.get('postMarketChange'),
        }
        
        try:
            cal = ticker.calendar
            if cal is not None and not cal.empty:
                if isinstance(cal, pd.DataFrame): stock_info['nextEarnings'] = cal.iloc[0, 0].strftime("%Y-%m-%d")
                elif isinstance(cal, dict): stock_info['nextEarnings'] = cal.get('Earnings Date', ['N/A'])[0]
            else: stock_info['nextEarnings'] = "N/A"
        except: stock_info['nextEarnings'] = "N/A"

        return df, stock_info, df_mtf
    except: return None, None, None

# --- 6. Analysis Logic (Thai Volume Grading) ---
def analyze_volume(row, vol_ma):
    vol = row['Volume']
    
    # กัน Error กรณีหุ้นใหม่ หรือไม่มีค่าเฉลี่ย
    if np.isnan(vol_ma) or vol_ma == 0: 
        return "☁️ ปกติ", "gray"
    
    # คำนวณ % เทียบค่าเฉลี่ย
    pct = (vol / vol_ma) * 100
    
    # --- แบ่งเกรด 4 ระดับ (ภาษาไทย) ---
    if pct >= 250: # ระดับ 4: ระเบิดลง
        return f"💣 สูงมาก/ระเบิด ({pct:.0f}%)", "#7f1d1d" # สีแดงเข้ม (Extreme)
    elif pct >= 120: # ระดับ 3: คึกคัก
        return f"🔥 สูง/คึกคัก ({pct:.0f}%)", "#16a34a" # สีเขียว (Strong)
    elif pct <= 70: # ระดับ 1: แห้ง
        return f"🌵 ต่ำ/เบาบาง ({pct:.0f}%)", "#f59e0b" # สีส้ม (Quiet)
    else: # ระดับ 2: ปกติ
        return f"☁️ ปกติ ({pct:.0f}%)", "gray" # สีเทา

# --- 7. AI Brain (Precision EMA + Dynamic Volume Tier) ---
def ai_hybrid_analysis(price, ema20, ema50, ema200, rsi, macd_val, macd_sig, adx, bb_up, bb_low, vol_status, mtf_trend, atr_val, mtf_ema200_val, open_price, high, low, close, obv_val, obv_avg, obv_slope, rolling_min, rolling_max, prev_open, prev_close, vol_now, vol_avg, demand_zones, is_squeeze):
    
    def sf(x): return float(x) if not np.isnan(float(x)) else np.nan
    price = sf(price); ema20 = sf(ema20); ema50 = sf(ema50); ema200 = sf(ema200); atr_val = sf(atr_val)
    
    candle_pattern, candle_color, candle_detail, is_big_candle = analyze_candlestick(open_price, high, low, close)
    is_reversal = "Hammer" in candle_pattern or "Doji" in candle_pattern
    vol_txt, vol_col = analyze_volume({'Volume': vol_now}, vol_avg)
    
    in_zone = False; active_zone = None
    if demand_zones:
        for z in demand_zones:
            if (low <= z['top'] * 1.005) and (high >= z['bottom']): in_zone = True; active_zone = z; break
            
    is_conf = False; conf_msg = ""
    if in_zone:
        if abs(active_zone['bottom'] - ema200) / price < 0.02: is_conf = True; conf_msg = "Zone + EMA 200"
        elif abs(active_zone['bottom'] - ema50) / price < 0.02: is_conf = True; conf_msg = "Zone + EMA 50"

    score = 0; bullish = []; bearish = []
    
    # 1. Structure (Precision Logic for Week)
    is_above_200 = False
    if not np.isnan(ema200):
        if price > ema200: score += 2; is_above_200 = True; bullish.append("ยืนเหนือ EMA 200 (เทรนด์หลักแกร่ง)")
        else: score -= 2; bearish.append("หลุด EMA 200 (เทรนด์หลักขาลง/อ่อนแอ)")
    if not np.isnan(ema50):
        if price > ema50: score += 1; bullish.append("ยืนเหนือ EMA 50 (ระยะกลางดี)")
        else: score -= 1; bearish.append("หลุด EMA 50 (เสียทรงระยะกลาง)")
    if not np.isnan(ema20):
        if price < ema20: score -= 2; bearish.append("หลุด EMA 20 (โมเมนตัมระยะสั้นหาย)") # Penalty -2

    # Bonus: Alignment
    if not np.isnan(ema20) and not np.isnan(ema50) and not np.isnan(ema200):
        if ema20 > ema50 and ema50 > ema200 and price > ema20: score += 1; bullish.append("🚀 Perfect Alignment (20>50>200)")

    # 2. Momentum
    if not np.isnan(macd_val) and not np.isnan(macd_sig):
        if macd_val > macd_sig: bullish.append("MACD ตัดขึ้น (Momentum บวก)")
        else: score -= 1; bearish.append("MACD ตัดลง (Momentum ลบ)")
    if rsi < 30: score += 1; bullish.append(f"RSI Oversold ({rsi:.0f})")
    elif rsi > 70: score -= 1; bearish.append(f"RSI Overbought ({rsi:.0f})")
    if mtf_trend == "Bullish": score += 1; bullish.append("TF ใหญ่เป็นขาขึ้น")
    else: bearish.append("TF ใหญ่เป็นขาลง")

    situation_insight = ""
    
    # 3. Smart OBV & Squeeze
    has_bull_div = False; has_bear_div = False; obv_insight = "Volume Flow ปกติ"
    if not np.isnan(obv_slope):
        if price < ema20 and obv_slope > 0: has_bull_div = True; score += 2; bullish.append("💎 Smart OBV: Bullish Divergence"); obv_insight = "Bullish Divergence (สะสม)"
        elif price > ema20 and obv_slope < 0: has_bear_div = True; score -= 2; bearish.append("⚠️ Smart OBV: Bearish Divergence"); obv_insight = "Bearish Divergence (ระวังทุบ)"
    
    if is_squeeze:
        situation_insight = "💣 **BB Squeeze:** กราฟบีบอัดรุนแรง รอระเบิด!"
        if has_bull_div: score += 1; situation_insight += " (ลุ้นระเบิดขึ้น 🚀)"
        elif has_bear_div: score -= 1; situation_insight += " (ระวังระเบิดลง 🩸)"

    # 4. SMC
    if in_zone:
        if "ต่ำ" in vol_txt or "ปกติ" in vol_txt:
            score += 3; bullish.append(f"🟢 Demand Zone + Volume ปลอดภัย")
            if not is_squeeze: situation_insight = "💎 **Sniper Mode:** เข้าโซนซื้อสวย รอเด้ง"
            if is_reversal: score += 1; bullish.append("🕯️ เจอแท่งเทียนกลับตัวในโซน")
        if is_conf: score += 2; bullish.append(f"⭐ Confluence: {conf_msg}")

    # 5. SAFETY NET (Smart Dynamic Penalty - 4 Tiers)
    if "ระเบิด" in vol_txt and close < open_price: # Tier 4: Crash > 250%
        score -= 10; bearish.append("💀 **Panic Sell:** Volume ระเบิด (หนีตาย!)"); situation_insight = "🩸 **Market Crash:** แรงขายถล่มทลาย ห้ามรับ!"
        bullish = [f for f in bullish if "EMA" not in f] # Wipe EMA score
    elif "คึกคัก" in vol_txt and is_big_candle and close < open_price: # Tier 1-3
        vol_pct = (vol_now / vol_avg) * 100
        # --- The Smart Penalty Logic ---
        if vol_pct >= 200: penalty = 5; sev = "รุนแรงมาก (Severe)" # Tier 3
        elif vol_pct >= 150: penalty = 4; sev = "รุนแรง (Heavy)"   # Tier 2
        else: penalty = 3; sev = "เริ่มผิดปกติ (Moderate)"         # Tier 1
        
        score -= penalty
        bearish.append(f"⚠️ **Selling Pressure:** แรงขาย{sev} (Vol {vol_pct:.0f}%) หัก {penalty} แต้ม")
        
        if score <= -3: situation_insight = "🩸 **Falling Knife:** เสียทรงขาลงชัดเจน (ห้ามรับ)"
        elif score <= -1: situation_insight = "🟠 **Correction:** ย่อตัวแรง (ระวังหลุดแนวรับ)"
        else: situation_insight = "⚠️ **Profit Taking:** แรงขายทำกำไรกดดัน"

    # 6. Status Generation
    if situation_insight == "":
        if score >= 5: situation_insight = "🚀 **Skyrocket:** เทรนด์ขาขึ้นแข็งแกร่ง (Strong Uptrend)"
        elif score >= 3: situation_insight = "🐂 **Uptrend:** เทรนด์ยังดี ย่อตัวน่าสนใจ"
        elif score >= 1: situation_insight = "⚖️ **Sideway:** รอเลือกทาง / พักตัว"
        elif score >= -2: situation_insight = "🐻 **Bearish:** แรงกดดันสูง / ติดแนวต้าน"
        else: situation_insight = "📉 **Downtrend:** ขาลงสมบูรณ์แบบ"

    # GATEKEEPER: EMA 200 Rule
    if not is_above_200 and score >= 5:
        score = 4; situation_insight = "🐂 **Rebound Play:** เล่นเด้งในขาลงใหญ่ (ระวัง EMA 200 กดทับ)"

    if score >= 5: status_col = "green"; title = "🚀 Sniper Entry: จุดซื้อคมกริบ"; st_text = "Aggressive Buy"; adv = f"เทรนด์แข็งแกร่งมาก! รันเทรนด์ได้ยาวๆ SL: {low-(atr_val*0.5):.2f}"
    elif score >= 3: status_col = "green"; title = "🐂 Buy on Dip: ย่อซื้อ"; st_text = "Accumulate"; adv = "ย่อตัวลงมาในจุดที่ได้เปรียบ ทยอยสะสมได้"
    elif score >= 1: status_col = "yellow"; title = "⚖️ Neutral: ไซด์เวย์"; st_text = "Wait & See"; adv = "ตลาดยังไม่เลือกทางชัดเจน รอสัญญาณยืนยัน"
    elif score <= -3: status_col = "red"; title = "🩸 Falling Knife: มีดหล่น"; st_text = "Wait / Cut Loss"; adv = "อันตราย! อย่าเพิ่งรับมีด รอให้ราคาหยุดลงและสร้างฐานใหม่"
    else: status_col = "orange"; title = "🐻 Bearish Pressure: แรงกดดันสูง"; st_text = "Avoid"; adv = "โมเมนตัมเป็นลบ/ติดแนวต้าน ยังไม่คุ้มเสี่ยง"

    sl_v = (active_zone['bottom'] - atr_val*0.5) if in_zone else (price - 2*atr_val)
    tp_v = price + 3*atr_val

    return {"status_color": status_col, "banner_title": title, "strategy": st_text, "context": situation_insight, "bullish_factors": bullish, "bearish_factors": bearish, "sl": sl_v, "tp": tp_v, "holder_advice": adv, "candle_pattern": candle_pattern, "candle_color": candle_color, "candle_detail": candle_detail, "vol_quality_msg": vol_txt, "vol_quality_color": vol_col, "in_demand_zone": in_zone, "confluence_msg": conf_msg, "is_squeeze": is_squeeze, "obv_insight": obv_insight}

# --- 8. Display ---
if submit_btn:
    st.divider()
    with st.spinner(f"AI กำลังประมวลผล {symbol_input}..."):
        df, info, df_mtf = get_data_hybrid(symbol_input, tf_code, mtf_code)
        try: ts = yf.Ticker(symbol_input); df_d = ts.history(period="2y", interval="1d"); df_w = ts.history(period="5y", interval="1wk")
        except: df_d = pd.DataFrame(); df_w = pd.DataFrame()

    if df is not None and not df.empty and len(df) > 20:
        df['EMA20'] = ta.ema(df['Close'], length=20); df['EMA50'] = ta.ema(df['Close'], length=50); df['EMA200'] = ta.ema(df['Close'], length=200)
        df['RSI'] = ta.rsi(df['Close'], length=14); df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        macd = ta.macd(df['Close']); df = pd.concat([df, macd], axis=1)
        bb = ta.bbands(df['Close'], length=20, std=2); 
        if bb is not None: df = pd.concat([df, bb], axis=1); bbu_col = bb.columns[2]; bbl_col = bb.columns[0]
        else: bbu_col = None; bbl_col = None
        df['ADX'] = ta.adx(df['High'], df['Low'], df['Close'], length=14)['ADX_14']
        df['Vol_SMA20'] = ta.sma(df['Volume'], length=20)
        df['OBV'] = ta.obv(df['Close'], df['Volume']); df['OBV_SMA20'] = ta.sma(df['OBV'], length=20); df['OBV_Slope'] = ta.slope(df['OBV'], length=5)
        df['BB_Width'] = (df[bbu_col] - df[bbl_col]) / df['EMA20'] * 100 if bbu_col else 0
        df['BB_Min'] = df['BB_Width'].rolling(20).min(); is_sq = df['BB_Width'].iloc[-1] <= (df['BB_Min'].iloc[-1] * 1.1)

        dz = find_demand_zones(df); sz = find_supply_zones(df)
        last = df.iloc[-1]; price = info.get('regularMarketPrice') or last['Close']
        vol_avg = last['Vol_SMA20'] if not np.isnan(last['Vol_SMA20']) else 1
        
        # Run AI
        rpt = ai_hybrid_analysis(price, last.get('EMA20'), last.get('EMA50'), last.get('EMA200'), last.get('RSI'), last.get('MACD_12_26_9'), last.get('MACDs_12_26_9'), last.get('ADX'), last.get(bbu_col), last.get(bbl_col), "", "", last.get('ATR'), 0, last['Open'], last['High'], last['Low'], last['Close'], last.get('OBV'), last.get('OBV_SMA20'), last.get('OBV_Slope'), 0, 0, 0, 0, last['Volume'], vol_avg, dz, is_sq)

        # Log
        st.session_state['history_log'].insert(0, { "เวลา": datetime.now().strftime("%H:%M"), "หุ้น": symbol_input, "ราคา": f"{price:.2f}", "Score": rpt['status_color'].upper(), "Action": rpt['strategy'] })
        st.session_state['history_log'] = st.session_state['history_log'][:10]

        # UI
        st.image(f"https://financialmodelingprep.com/image-stock/{symbol_input}.png", width=60)
        st.title(f"{info['longName']} ({symbol_input})")
        
        c1, c2 = st.columns(2)
        c1.metric("Price", f"{price:.2f}", f"{info.get('regularMarketChange'):.2f} ({info.get('regularMarketChangePercent'):.2f}%)")
        if "green" in rpt['status_color']: c2.success(f"📈 {rpt['banner_title']}")
        elif "red" in rpt['status_color']: c2.error(f"📉 {rpt['banner_title']}")
        else: c2.warning(f"⚖️ {rpt['banner_title']}")

        # Action Plan Box
        box_fn = st.success if "green" in rpt['status_color'] else (st.error if "red" in rpt['status_color'] else st.warning)
        box_fn(f"""### 📝 แผนการเทรด (Action Plan)\n\n**1. สถานการณ์:** {rpt['context']}\n\n**2. คำแนะนำ:** 👉 **{rpt['strategy']}** : {rpt['holder_advice']}\n\n**3. Setup:** 🛑 SL: {rpt['sl']:.2f} | ✅ TP: {rpt['tp']:.2f}""")

        # Details
        c3, c4 = st.columns([1.5, 2])
        with c3:
            st.markdown("#### 📉 Indicators")
            st.write(f"EMA 20: {last.get('EMA20',0):.2f} | EMA 50: {last.get('EMA50',0):.2f} | EMA 200: {last.get('EMA200',0):.2f}")
            st.write(f"RSI: {last.get('RSI',0):.2f} | Volume: {rpt['vol_quality_msg']}")
            st.markdown("#### 🟢 แนวรับ/ต้าน")
            
            # --- 🛡️ FIXED CRASH: Add try-except for insufficient data ---
            if not df_stats_week.empty:
                try: w_ema50 = ta.ema(df_stats_week['Close'], length=50).iloc[-1]
                except: w_ema50 = np.nan
                
                try: w_ema200 = ta.ema(df_stats_week['Close'], length=200).iloc[-1]
                except: w_ema200 = np.nan

                if not np.isnan(w_ema50) and w_ema50 < price: candidates_supp.append({'val': w_ema50, 'label': "EMA 50 (TF Week - รับระยะยาว)"})
                if not np.isnan(w_ema200) and w_ema200 < price: candidates_supp.append({'val': w_ema200, 'label': "🛡️ EMA 200 (TF Week - รับระดับกองทุน)"})
            # -------------------------------------------------------------
                
            if supply_zones:
                for z in supply_zones: candidates_res.append({'val': z['top'], 'label': f"Supply Zone [{z['bottom']:.2f}-{z['top']:.2f}]"})

            candidates_res.sort(key=lambda x: x['val'], reverse=True) # High -> Low for Support

            merged_supp = []
            skip_next = False
            for i in range(len(candidates_supp)):
                if skip_next: skip_next = False; continue
                current = candidates_supp[i]
                if i < len(candidates_supp) - 1:
                    next_item = candidates_supp[i+1]
                    if (current['val'] - next_item['val']) / current['val'] < 0.01: 
                        new_label = f"⭐ Confluence Zone ({current['label']} + {next_item['label']})"
                        merged_supp.append({'val': current['val'], 'label': new_label})
                        skip_next = True
                        continue
                merged_supp.append(current)

            final_show_supp = []
            for item in merged_supp:
                if (price - item['val']) / price > 0.30 and "EMA 200 (TF Week" not in item['label']: continue
                
                # Immunity Check: ถ้าเป็น EMA 200 หรือ EMA 50 Week หรือ 52-Week ให้ผ่านตลอด (VIP)
                is_vip = "EMA 200" in item['label'] or "EMA 50 (TF Week" in item['label'] or "52-Week" in item['label']
                
                if not final_show_supp: final_show_supp.append(item)
                else:
                    last_item = final_show_supp[-1]
                    dist = abs(last_item['val'] - item['val'])
                    # ถ้า V.I.P. ให้ Add เลย ไม่สนระยะห่าง / ถ้าไม่ใช่ V.I.P. ต้องผ่านเกณฑ์ระยะห่าง
                    if is_vip or dist >= min_dist:
                        final_show_supp.append(item)

            # --- 🌟 MODIFIED: Sub-header ตัดภาษาอังกฤษออก ---
            st.markdown("#### 🟢 แนวรับ"); 
            if final_show_supp: 
                for item in final_show_supp[:4]: st.write(f"- **{item['val']:.2f} :** {item['label']}")
            else: st.error("🚨 ราคาหลุดทุกแนวรับสำคัญ! (All Time Low?)")

            # === PART 2: RESISTANCES ===
            candidates_res = []
            if not np.isnan(ema20) and ema20 > price: candidates_res.append({'val': ema20, 'label': f"EMA 20 ({tf_label} - ต้านสั้น)"})
            if not np.isnan(ema50) and ema50 > price: candidates_res.append({'val': ema50, 'label': f"EMA 50 ({tf_label})"})
            if not np.isnan(ema200) and ema200 > price: candidates_res.append({'val': ema200, 'label': f"EMA 200 ({tf_label} - ต้านใหญ่)"})
            if not np.isnan(bb_upper) and bb_upper > price: candidates_res.append({'val': bb_upper, 'label': f"BB Upper ({tf_label} - เพดาน)"})
            
            if not df_stats_day.empty:
                d_ema50 = ta.ema(df_stats_day['Close'], length=50).iloc[-1]
                if d_ema50 > price: candidates_res.append({'val': d_ema50, 'label': "EMA 50 (TF Day)"})
                high_60d = df_stats_day['High'].tail(60).max()
                if high_60d > price: candidates_res.append({'val': high_60d, 'label': "🏔️ High 60d (ดอย 3 เดือน)"})

            # --- 🛡️ FIXED CRASH: Add try-except for insufficient data ---
            if not df_stats_week.empty:
                try: w_ema50 = ta.ema(df_stats_week['Close'], length=50).iloc[-1]
                except: w_ema50 = np.nan
                
                try: w_ema200 = ta.ema(df_stats_week['Close'], length=200).iloc[-1]
                except: w_ema200 = np.nan

                if not np.isnan(w_ema50) and w_ema50 > price: candidates_res.append({'val': w_ema50, 'label': "EMA 50 (TF Week - ต้านระยะยาว)"})
                if not np.isnan(w_ema200) and w_ema200 > price: candidates_res.append({'val': w_ema200, 'label': "🛡️ EMA 200 (TF Week - ต้านระดับกองทุน)"})
            # -------------------------------------------------------------
                
            if supply_zones:
                for z in supply_zones: candidates_res.append({'val': z['top'], 'label': f"Supply Zone [{z['bottom']:.2f}-{z['top']:.2f}]"})

            candidates_res.sort(key=lambda x: x['val'])

            merged_res = []
            skip_next = False
            for i in range(len(candidates_res)):
                if skip_next: skip_next = False; continue
                current = candidates_res[i]
                if i < len(candidates_res) - 1:
                    next_item = candidates_res[i+1]
                    if (next_item['val'] - current['val']) / current['val'] < 0.01:
                        new_label = f"⭐ Confluence Zone ({current['label']} + {next_item['label']})"
                        merged_res.append({'val': current['val'], 'label': new_label})
                        skip_next = True
                        continue
                merged_res.append(current)

            final_show_res = []
            for item in merged_res:
                if (item['val'] - price) / price > 0.30 and "EMA 200 (TF Week" not in item['label']: continue
                
                is_vip = "EMA 200" in item['label'] or "EMA 50 (TF Week" in item['label']
                
                if not final_show_res: final_show_res.append(item)
                else:
                    last_item = final_show_res[-1]
                    dist = abs(item['val'] - last_item['val'])
                    if is_vip or dist >= min_dist:
                        final_show_res.append(item)

            # --- 🌟 MODIFIED: Sub-header ตัดภาษาอังกฤษออก ---
            st.markdown("#### 🔴 แนวต้าน"); 
            if final_show_res: 
                for item in final_show_res[:4]: st.write(f"- **{item['val']:.2f} :** {item['label']}")
            else: st.write("- N/A (Blue Sky)")

        with c4:
            st.markdown("#### 🔍 AI Analysis")
            st.markdown(f"**ทรงกราฟ:** {rpt['candle_pattern']} ({rpt['candle_color']})")
            st.markdown(f"**แรงกดดัน (BB):** {'⚠️ Squeeze' if is_sq else 'Normal'}")
            st.markdown(f"**Smart OBV:** {rpt['obv_insight']}")
            if rpt['bullish_factors']: 
                st.markdown("**✅ ปัจจัยบวก:**")
                for f in rpt['bullish_factors']: st.caption(f"- {f}")
            if rpt['bearish_factors']: 
                st.markdown("**⚠️ ความเสี่ยง:**")
                for f in rpt['bearish_factors']: st.caption(f"- {f}")
        
        # --- 🛡️ FIXED: Safe Display for c5 (Prevents TypeError: >= not supported between instances of 'float' and 'NoneType') ---
        with c5:
            # Safe ADX processing
            try:
                adx_val_safe = float(last.get('ADX', np.nan)) # Use .get() to avoid key error if column missing
                if np.isnan(adx_val_safe): adx_disp = np.nan
                else: adx_disp = adx_val_safe
            except: adx_disp = np.nan

            # Safe Trend Check (The main crasher)
            try:
                ema200_val = last.get('EMA200')
                if ema200_val is not None:
                    ema200_safe = float(ema200_val)
                    if not np.isnan(ema200_safe):
                        is_uptrend = price >= ema200_safe
                    else: is_uptrend = True
                else: is_uptrend = True
            except: is_uptrend = True

            adx_text = get_adx_interpretation(adx_disp, is_uptrend)
            adx_str = f"{adx_disp:.2f}" if not np.isnan(adx_disp) else "N/A"
            st.markdown(custom_metric_html("💪 ADX Strength", adx_str, adx_text, "gray", icon_flat_svg), unsafe_allow_html=True)
        # -----------------------------------------------------------------------------------------------------------------

        st.markdown("---")
        st.subheader("📜 History Log")
        st.dataframe(pd.DataFrame(st.session_state['history_log']), hide_index=True, use_container_width=True)

    else: st.error("ไม่พบข้อมูลหุ้น")

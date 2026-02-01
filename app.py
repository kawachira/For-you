import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import plotly.graph_objects as go
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
        border: none; padding: 20px; border-radius: 15px;
        background-color: var(--secondary-background-color);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    .disclaimer-box {
        margin-top: 20px; margin-bottom: 20px; padding: 15px;
        background-color: #fff8e1; border: 1px solid #ffc107;
        border-radius: 10px; font-size: 0.9rem; color: #5d4037;
        text-align: center;
    }

    /* Custom Cards */
    .metric-card {
        background-color: var(--secondary-background-color);
        padding: 15px; border-radius: 10px;
        border-left: 5px solid #ccc;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    
    .fund-good { border-left-color: #22c55e; }
    .fund-mid { border-left-color: #eab308; }
    .fund-bad { border-left-color: #ef4444; }
    
    .xray-box {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ส่วนหัวข้อ ---
st.markdown("<h1>💎 Ai Stock Master<br><span style='font-size: 1.2rem; opacity: 0.7;'>Ultimate Sniper (SMC + OBV Hybrid) 🚀</span></h1>", unsafe_allow_html=True)

# --- Form ค้นหา ---
with st.container():
    col_space1, col_form, col_space2 = st.columns([1, 2, 1])
    with col_form:
        with st.form(key='search_form'):
            c1, c2 = st.columns([3, 1])
            with c1:
                symbol_input = st.text_input("ชื่อหุ้น (เช่น TSLA, AAPL, NVDA)", value="TSLA").upper().strip()
            with c2:
                timeframe = st.selectbox("Timeframe:", ["1h (รายชั่วโมง)", "1d (รายวัน)", "1wk (รายสัปดาห์)"], index=1)
                
                if "1wk" in timeframe: tf_code = "1wk"; mtf_code = "1mo"
                elif "1h" in timeframe: tf_code = "1h"; mtf_code = "1d"
                else: tf_code = "1d"; mtf_code = "1wk"
            
            submit_btn = st.form_submit_button("🚀 วิเคราะห์ทันที", use_container_width=True)

# --- 4. Helper Functions ---

def analyze_candlestick(open_price, high, low, close):
    body = abs(close - open_price)
    wick_upper = high - max(close, open_price)
    wick_lower = min(close, open_price) - low
    total_range = high - low
    
    color = "🟢 เขียว (Buying)" if close >= open_price else "🔴 แดง (Selling)"
    if total_range == 0: return "Doji (N/A)", color, "N/A", False

    pattern_name = "Normal Candle"
    detail = "แรงซื้อขายสมดุล"
    is_big = False

    if wick_lower > (body * 2) and wick_upper < body:
        pattern_name = "🔨 Hammer/Pinbar"
        detail = "ปฏิเสธราคาต่ำ (แรงซื้อสวนกลับ)"
    elif wick_upper > (body * 2) and wick_lower < body:
        pattern_name = "🌠 Shooting Star"
        detail = "ปฏิเสธราคาสูง (แรงขายกดดัน)"
    elif body > (total_range * 0.6): 
        is_big = True
        pattern_name = "Big Candle (แท่งตัน)"
        detail = "Momentum แข็งแกร่ง"
    elif body < (total_range * 0.1):
        pattern_name = "Doji"
        detail = "ตลาดลังเล (Indecision)"
        
    return pattern_name, color, detail, is_big

def analyze_fundamental(info):
    pe = info.get('trailingPE', None)
    eps_growth = info.get('earningsQuarterlyGrowth', None)
    
    score = 0
    if pe:
        if pe < 0: score -= 2
        elif pe < 20: score += 1
        elif pe > 50: score -= 1
    
    if eps_growth:
        if eps_growth > 0.15: score += 2
        elif eps_growth > 0: score += 1
        else: score -= 2
    
    if score >= 2: return {"status": "Strong Fundamental (งบดี)", "class": "fund-good", "advice": "ถือยาวได้ (Investable)"}
    elif score <= -2: return {"status": "Weak Fundamental (งบแย่)", "class": "fund-bad", "advice": "เก็งกำไรสั้นๆ เท่านั้น"}
    else: return {"status": "Moderate (งบกลางๆ)", "class": "fund-mid", "advice": "เล่นตามรอบ (Swing Trade)"}

# --- SMC Logic ---
def find_zones(df, zone_type="Demand", atr_multiplier=0.25):
    zones = []
    if len(df) < 20: return zones
    
    if zone_type == "Demand":
        # Swing Low logic
        check = df['Low']
        is_swing = (check < check.shift(1)) & (check < check.shift(2)) & (check < check.shift(-1)) & (check < check.shift(-2))
    else:
        # Swing High logic
        check = df['High']
        is_swing = (check > check.shift(1)) & (check > check.shift(2)) & (check > check.shift(-1)) & (check > check.shift(-2))
        
    indices = is_swing[is_swing].index
    current_price = df['Close'].iloc[-1]
    
    for date in indices:
        if date >= df.index[-2]: continue # Skip incomplete candles
        
        atr_val = df.loc[date, 'ATR'] if 'ATR' in df.columns else (df.loc[date, 'Close'] * 0.02)
        if np.isnan(atr_val): continue

        if zone_type == "Demand":
            base = df.loc[date, 'Low']
            top = base + (atr_val * atr_multiplier)
            bottom = base
            # Filter distant zones
            if (current_price - top) / current_price > 0.15: continue
            # Check if broken
            future = df.loc[date:][1:]
            if not (future['Close'] < bottom).any():
                zones.append({'bottom': bottom, 'top': top, 'date': date})
        else:
            base = df.loc[date, 'High']
            bottom = base - (atr_val * atr_multiplier)
            top = base
             # Filter distant zones
            if (bottom - current_price) / current_price > 0.15: continue
            # Check if broken
            future = df.loc[date:][1:]
            if not (future['Close'] > top).any():
                zones.append({'bottom': bottom, 'top': top, 'date': date})
                
    return zones

# --- Charting Function ---
def create_chart(df, symbol, demand_zones, supply_zones):
    fig = go.Figure()

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name="Price"
    ))

    # EMAs
    colors = {'EMA20': '#f59e0b', 'EMA50': '#3b82f6', 'EMA200': '#a855f7'}
    for ema, color in colors.items():
        if ema in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df[ema], mode='lines', name=ema, line=dict(color=color, width=1)))

    # Zones (Shapes)
    shapes = []
    # Demand (Green)
    for z in demand_zones:
        shapes.append(dict(type="rect", xref="x", yref="y", x0=z['date'], y0=z['bottom'], x1=df.index[-1], y1=z['top'],
                           fillcolor="green", opacity=0.2, line_width=0))
    # Supply (Red)
    for z in supply_zones:
        shapes.append(dict(type="rect", xref="x", yref="y", x0=z['date'], y0=z['bottom'], x1=df.index[-1], y1=z['top'],
                           fillcolor="red", opacity=0.2, line_width=0))

    fig.update_layout(
        title=f"{symbol} Price Action & SMC Zones",
        yaxis_title="Price",
        template="plotly_white",
        height=500,
        margin=dict(l=20, r=20, t=50, b=20),
        shapes=shapes,
        xaxis_rangeslider_visible=False
    )
    return fig

# --- 5. Data & Logic ---

@st.cache_data(ttl=60, show_spinner=False)
def get_data(symbol, interval):
    try:
        ticker = yf.Ticker(symbol)
        period = "2y" if interval == "1d" else ("5y" if interval == "1wk" else "60d")
        df = ticker.history(period=period, interval=interval)
        return df, ticker.info
    except:
        return None, None

if submit_btn:
    st.divider()
    with st.spinner(f"AI กำลังสแกนหา Demand/Supply Zone และประมวลผล {symbol_input}..."):
        
        df, info = get_data(symbol_input, tf_code)
        
        if df is not None and not df.empty and len(df) > 50:
            # --- Indicators Calculation ---
            df['EMA20'] = ta.ema(df['Close'], length=20)
            df['EMA50'] = ta.ema(df['Close'], length=50)
            df['EMA200'] = ta.ema(df['Close'], length=200)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
            df['OBV'] = ta.obv(df['Close'], df['Volume'])
            
            # BB & Squeeze
            bb = ta.bbands(df['Close'], length=20, std=2)
            if bb is not None:
                df = pd.concat([df, bb], axis=1)
                df['BB_Width'] = (df.iloc[:, -1] - df.iloc[:, -3]) / df['EMA20']
            
            # Extract Last Data
            last = df.iloc[-1]
            prev = df.iloc[-2]
            
            # --- Analysis Logic ---
            demand_zones = find_zones(df, "Demand")
            supply_zones = find_zones(df, "Supply")
            
            # Fundamental Check
            fund_data = analyze_fundamental(info)
            
            # Score Calculation (Simplified for readability)
            score = 0
            reasons = []
            
            # Trend
            if last['Close'] > last['EMA200']: score += 2; reasons.append("Price > EMA200 (Uptrend)")
            else: score -= 2; reasons.append("Price < EMA200 (Downtrend)")
            
            # Momentum
            if last['RSI'] < 30: score += 1; reasons.append("RSI Oversold (Buy Signal)")
            elif last['RSI'] > 70: score -= 1; reasons.append("RSI Overbought (Risk)")
            
            # SMC
            in_demand = False
            for z in demand_zones:
                if (last['Low'] <= z['top']) and (last['High'] >= z['bottom']):
                    in_demand = True
                    break
            
            if in_demand: score += 3; reasons.append("Price in Demand Zone (Sniper Entry)")
            
            # AI Verdict
            if score >= 4: verdict, v_color = "STRONG BUY", "green"
            elif score >= 1: verdict, v_color = "BUY / ACCUMULATE", "teal"
            elif score <= -3: verdict, v_color = "STRONG SELL", "red"
            else: verdict, v_color = "NEUTRAL / WAIT", "orange"
            
            # --- Display UI ---
            
            # Header Info
            st.markdown(f"## {info.get('longName', symbol_input)} ({symbol_input})")
            p_now = last['Close']
            p_chg = p_now - prev['Close']
            p_pct = (p_chg / prev['Close']) * 100
            
            col_h1, col_h2, col_h3 = st.columns([1.5, 1, 1])
            with col_h1:
                st.metric("Current Price", f"{p_now:.2f}", f"{p_chg:.2f} ({p_pct:.2f}%)")
            with col_h2:
                st.markdown(f"**Verdict:** <span style='color:{v_color}; font-weight:bold; font-size:1.2em'>{verdict}</span>", unsafe_allow_html=True)
            with col_h3:
                st.markdown(f"**Fundamental:** <span style='color:blue'>{fund_data['status']}</span>", unsafe_allow_html=True)

            # --- Chart (New!) ---
            st.plotly_chart(create_chart(df, symbol_input, demand_zones, supply_zones), use_container_width=True)
            
            # --- Detailed Panels ---
            c1, c2, c3 = st.columns(3)
            
            with c1:
                st.markdown(f"<div class='metric-card {fund_data['class']}'><b>📊 Technical Data</b><br>"
                            f"RSI: {last['RSI']:.2f}<br>"
                            f"EMA200: {last['EMA200']:.2f}<br>"
                            f"ATR: {last['ATR']:.2f}</div>", unsafe_allow_html=True)
            
            with c2:
                vol_status = "Volume Spike! 💣" if last['Volume'] > df['Volume'].mean() * 2 else "Volume Normal"
                st.markdown(f"<div class='metric-card'><b>🌊 Volume & OBV</b><br>"
                            f"{vol_status}<br>"
                            f"OBV: {last['OBV']:.0f}</div>", unsafe_allow_html=True)
                            
            with c3:
                candle_pat, c_col, c_det, _ = analyze_candlestick(last['Open'], last['High'], last['Low'], last['Close'])
                st.markdown(f"<div class='metric-card'><b>🕯️ Price Action</b><br>"
                            f"{candle_pat}<br>"
                            f"<span style='font-size:0.8em'>{c_det}</span></div>", unsafe_allow_html=True)

            # Strategy Box
            st.markdown("### 🤖 AI Strategy Insight")
            st.info(f"**เหตุผลประกอบ:** {', '.join(reasons)}")
            
            if in_demand:
                sl = last['Low'] - (last['ATR'] * 0.5)
                tp = last['Close'] + (last['ATR'] * 2)
                st.success(f"🎯 **Sniper Setup Identified!**\n\nBuy Limit @ Market | SL: {sl:.2f} | TP: {tp:.2f}")

        else:
            st.error("ไม่พบข้อมูลหุ้น หรือข้อมูลไม่เพียงพอ")

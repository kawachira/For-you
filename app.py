import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="AI Stock Master", page_icon="💎", layout="wide")

# --- 2. CSS ปรับแต่ง (TradingView Style Theme) ---
st.markdown("""
    <style>
    .block-container { padding-top: 0.5rem !important; padding-bottom: 0rem !important; }
    h1 { text-align: center; font-size: 2rem !important; margin-bottom: 10px; color: #d1d4dc; }
    /* ปรับแต่ง Form ให้มืดและเข้ม */
    div[data-testid="stForm"] {
        border: 1px solid #2a2e39; padding: 20px; border-radius: 8px;
        background-color: #1e222d; /* สีพื้นหลัง Form แบบ TV */
        max-width: 900px; margin: 0 auto; color: #d1d4dc;
    }
    .stTextInput label, .stSelectbox label { color: #d1d4dc !important; }
    div[data-testid="stFormSubmitButton"] button {
        width: 100%; border-radius: 4px; font-weight: 600; padding: 10px 0;
        background-color: #2962ff; color: white; border: none;
    }
    div[data-testid="stFormSubmitButton"] button:hover { background-color: #1e54e4; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ส่วนหัวข้อ ---
st.markdown("<h1>💎 AI Stock Analysis (TV Style)</h1>", unsafe_allow_html=True)

# --- Form ค้นหา ---
with st.form(key='search_form'):
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        symbol_input = st.text_input("Symbol (e.g., AMZN, TSLA)", value="EOSE").upper().strip()
    with c2:
        timeframe = st.selectbox("Timeframe", ["1h", "1d", "1wk"], index=1)
        tf_code = "1wk" if "1wk" in timeframe else ("1h" if "1h" in timeframe else "1d")
    with c3:
        st.write("") # Spacer
        st.write("") # Spacer
        submit_btn = st.form_submit_button("🚀 Load Chart")

# --- Helper Functions ---
def get_rsi_int(rsi):
    if rsi>=70: return "🔴 Overbought"
    elif rsi<=30: return "🟢 Oversold"
    return "⚪ Neutral"

# --- 5. Get Data ---
@st.cache_data(ttl=60, show_spinner=False)
def get_data(symbol, interval):
    try:
        ticker = yf.Ticker(symbol)
        period_val = "730d" if interval == "1h" else "max"
        df = ticker.history(period=period_val, interval=interval)
        if df.empty: return None, None
        
        info = ticker.info
        reg_price = info.get('regularMarketPrice')
        if reg_price is None: reg_price = df['Close'].iloc[-1]

        stock_info = {
            'price': reg_price,
            'pe': info.get('trailingPE', 'N/A')
        }
        return df, stock_info
    except: return None, None

# --- AI Logic (Simplified) ---
def get_ai_signal(price, ema50, ema200):
    if price > ema200 and price > ema50: return "🟢 BULLISH: Strong Uptrend", "green"
    if price < ema200 and price < ema50: return "🔴 BEARISH: Strong Downtrend", "red"
    return "⚪ NEUTRAL: Sideway / Consolidation", "orange"

# --- 7. Display ---
if submit_btn:
    st.divider()
    with st.spinner(f"Loading {symbol_input} chart..."):
        df, info = get_data(symbol_input, tf_code)

        if df is not None and not df.empty and len(df) > 100:
            # Indicators
            df['EMA50'] = ta.ema(df['Close'], length=50)
            df['EMA200'] = ta.ema(df['Close'], length=200)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            
            last = df.iloc[-1]
            price = info['price']
            ai_txt, ai_col = get_ai_signal(price, last['EMA50'], last['EMA200'])

            # Price Header
            st.markdown(f"""
            <div style="text-align:center; margin-bottom: 15px;">
              <span style="font-size:36px; font-weight:bold; color:#d1d4dc;">{symbol_input}</span>
              <br>
              <span style="font-size:28px; color:white;">{price:,.2f}</span>
            </div>
            """, unsafe_allow_html=True)

            # ==================================================
            # 🔥🔥 กราฟ TradingView Style (แก้ไขการซูม) 🔥🔥
            # ==================================================
            
            # 1. Create Subplots (Price & Volume)
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                vertical_spacing=0.02, row_width=[0.2, 0.8])

            # 2. Candlestick (TV Colors)
            fig.add_trace(go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                name='Price',
                increasing_line_color='#089981', increasing_fillcolor='#089981', # TV Green
                decreasing_line_color='#f23645', decreasing_fillcolor='#f23645'  # TV Red
            ), row=1, col=1)

            # 3. EMAs
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA50'], mode='lines', name='EMA 50', line=dict(color='#2962ff', width=1.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA200'], mode='lines', name='EMA 200', line=dict(color='#fbbf24', width=2)), row=1, col=1)

            # 4. Volume
            vol_colors = ['#089981' if c >= o else '#f23645' for c, o in zip(df['Close'], df['Open'])]
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='Volume', marker_color=vol_colors), row=2, col=1)

            # 5. Layout Setup (หัวใจสำคัญของการซูม)
            fig.update_layout(
                height=550,
                margin=dict(l=0, r=0, t=10, b=0), # ลดขอบให้สุด
                paper_bgcolor='#131722', # พื้นหลัง TV
                plot_bgcolor='#131722',
                font=dict(color='#d1d4dc'),
                showlegend=False,
                dragmode='pan', # โหมดจับลาก
                hovermode='x unified',
                
                # --- ส่วนสำคัญที่เพิ่มมา: ล็อกแกน Y เพื่อให้ซูมได้

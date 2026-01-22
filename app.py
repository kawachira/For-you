import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="AI Stock Master", page_icon="💎", layout="wide")

# --- 2. CSS ปรับแต่งความสวยงาม (รองรับ Dark Mode) ---
st.markdown("""
    <style>
    h1 {
        text-align: center;
        font-size: 2.8rem !important;
        margin-bottom: 10px;
    }
    div[data-testid="stForm"] {
        border: none;
        padding: 30px;
        border-radius: 20px;
        background-color: var(--secondary-background-color);
        box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        max-width: 800px;
        margin: 0 auto;
    }
    div[data-testid="stFormSubmitButton"] button {
        width: 100%;
        border-radius: 12px;
        font-size: 1.2rem;
        font-weight: bold;
        padding: 15px 0;
    }
    div[data-testid="metric-container"] label { font-size: 1.1rem; }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] { font-size: 1.8rem; }
    </style>
""", unsafe_allow_html=True)

# --- 3. ส่วนหัวข้อและค้นหา ---
st.markdown("<h1>💎 Ai<br><span style='font-size: 1.5rem; opacity: 0.7;'>ระบบวิเคราะห์หุ้นอัจฉริยะ</span></h1>", unsafe_allow_html=True)
st.write("")

col_space1, col_form, col_space2 = st.columns([1, 2, 1])
with col_form:
    with st.form(key='search_form'):
        st.markdown("### 🔍 ค้นหาหุ้นที่ต้องการ")
        c1, c2 = st.columns([3, 1])
        with c1:
            symbol_input = st.text_input("ชื่อหุ้น (เช่น PTT.BK, TSLA):", value="EOSE").upper().strip()
        with c2:
            timeframe = st.selectbox("Timeframe:", ["1d (รายวัน)", "1wk (รายสัปดาห์)"], index=0)
            tf_code = "1wk" if "1wk" in timeframe else "1d"
        submit_btn = st.form_submit_button("🚀 วิเคราะห์ทันที")

# --- 4. Interpretation Functions ---
def get_rsi_interpretation(rsi):
    if rsi >= 80: return "🔴 Extreme Overbought"
    elif rsi >= 70: return "🟠 Overbought"
    elif rsi >= 60: return "🟢 Strong Bullish"
    elif rsi > 40: return "⚪ Neutral"
    elif rsi > 30: return "🟠 Bearish"
    elif rsi > 20: return "🟢 Oversold"
    else: return "🟢 Extreme Oversold"

def get_pe_interpretation(pe):
    if isinstance(pe, str): return "N/A"
    if pe < 0: return "ขาดทุน"
    if pe < 15: return "หุ้นถูก"
    if pe < 30: return "ปกติ"
    return "หุ้นแพง"

# --- 5. ดึงข้อมูล ---
@st.cache_data(ttl=1800, show_spinner=False)
def get_data(symbol, interval):
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="2y", interval=interval)
    info = ticker.info

    stock_info = {
        'longName': info.get('longName', symbol),
        'trailingPE': info.get('trailingPE', 'N/A'),

        # >>> ADD <<<
        'regularMarketPrice': info.get('regularMarketPrice'),
        'regularMarketChange': info.get('regularMarketChange'),
        'regularMarketChangePercent': info.get('regularMarketChangePercent'),
        'preMarketPrice': info.get('preMarketPrice'),
        'preMarketChange': info.get('preMarketChange'),
        'preMarketChangePercent': info.get('preMarketChangePercent'),
        'postMarketPrice': info.get('postMarketPrice'),
        'postMarketChange': info.get('postMarketChange'),
        'postMarketChangePercent': info.get('postMarketChangePercent'),
    }
    return df, stock_info

# >>> ADD <<< ลูกศรขึ้นลง สีเขียว/แดง
def arrow(v):
    if v is None: return ""
    return "🟢 ▲" if v > 0 else "🔴 ▼" if v < 0 else "➖"

# --- 6. แสดงผล ---
if submit_btn:
    st.divider()
    df, info = get_data(symbol_input, tf_code)

    if df is not None and not df.empty and len(df) > 200:
        df['EMA20'] = ta.ema(df['Close'], 20)
        df['EMA50'] = ta.ema(df['Close'], 50)
        df['EMA200'] = ta.ema(df['Close'], 200)
        df['RSI'] = ta.rsi(df['Close'], 14)

        last, prev = df.iloc[-1], df.iloc[-2]
        price = last['Close']
        change = price - prev['Close']
        change_pct = (change / prev['Close']) * 100

        st.markdown(f"<h2 style='text-align:center;'>🏢 {info['longName']} ({symbol_input})</h2>", unsafe_allow_html=True)

        c1, c2 = st.columns(2)

        # --- ราคาหลัก (ของเดิม) ---
        c1.metric("💰 ราคาล่าสุด", f"{price:.2f}", f"{change:.2f} ({change_pct:.2f}%)")

        # >>> ADD <<< เพิ่มตรงหลังราคา
        with c1:
            st.markdown(f"""
            <div style="margin-top:10px;font-size:15px;">
            <b>⏱️ ระหว่างตลาด</b><br>
            {arrow(info['regularMarketChange'])} {info['regularMarketChangePercent']}%<br><br>

            <b>🌅 ก่อนเปิดตลาด</b><br>
            {arrow(info['preMarketChange'])} {info['preMarketChangePercent']}%<br><br>

            <b>🌙 หลังปิดตลาด</b><br>
            {arrow(info['postMarketChange'])} {info['postMarketChangePercent']}%<br>

            <span style="font-size:12px;opacity:0.6;">
            *Market = near real-time / Pre & Post = last available*
            </span>
            </div>
            """, unsafe_allow_html=True)

        c2.success("📈 วิเคราะห์แนวโน้ม")

        st.subheader("📈 กราฟราคา")
        st.line_chart(df.tail(150)['Close'])

    else:
        st.error("ไม่พบข้อมูลหุ้น")

import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="AI Stock Master", page_icon="💎", layout="wide")

# --- 2. CSS ---
st.markdown("""
<style>
h1 { text-align:center; font-size:2.8rem !important; }
</style>
""", unsafe_allow_html=True)

# --- 3. Header ---
st.markdown("<h1>💎 AI<br><span style='font-size:1.4rem;opacity:0.7'>ระบบวิเคราะห์หุ้นอัจฉริยะ</span></h1>", unsafe_allow_html=True)
st.write("")

# --- Search ---
col1, col2, col3 = st.columns([1,2,1])
with col2:
    with st.form("search"):
        symbol_input = st.text_input("ชื่อหุ้น", value="EOSE").upper()
        timeframe = st.selectbox("Timeframe", ["1d", "1wk"])
        tf_code = "1wk" if timeframe == "1wk" else "1d"
        submit = st.form_submit_button("วิเคราะห์")

# --- Helper ---
def arrow_html(change):
    if change is None:
        return ""
    if change > 0:
        return "<span style='color:#16a34a;font-weight:600'>▲</span>"
    elif change < 0:
        return "<span style='color:#dc2626;font-weight:600'>▼</span>"
    return "—"

# --- Data ---
@st.cache_data(ttl=1800)
def get_data(symbol, interval):
    t = yf.Ticker(symbol)
    df = t.history(period="2y", interval=interval)
    info = t.info
    stock_info = {
        "longName": info.get("longName", symbol),
        "regularMarketPrice": info.get("regularMarketPrice"),
        "regularMarketChange": info.get("regularMarketChange"),
        "regularMarketChangePercent": info.get("regularMarketChangePercent"),
        "preMarketPrice": info.get("preMarketPrice"),
        "preMarketChange": info.get("preMarketChange"),
        "preMarketChangePercent": info.get("preMarketChangePercent"),
        "postMarketPrice": info.get("postMarketPrice"),
        "postMarketChange": info.get("postMarketChange"),
        "postMarketChangePercent": info.get("postMarketChangePercent"),
        "trailingPE": info.get("trailingPE", "N/A")
    }
    return df, stock_info

# --- Run ---
if submit:
    df, info = get_data(symbol_input, tf_code)

    if df is None or df.empty:
        st.error("ไม่พบข้อมูล")
        st.stop()

    # Indicator เดิม
    df["EMA20"] = ta.ema(df["Close"], 20)
    df["EMA50"] = ta.ema(df["Close"], 50)
    df["EMA200"] = ta.ema(df["Close"], 200)
    df["RSI"] = ta.rsi(df["Close"], 14)

    last = df.iloc[-1]

    st.markdown(f"## ({symbol_input})")

    # ===== ราคา (ตำแหน่งเดียวกับ 17.53) =====
    price = info["regularMarketPrice"]
    chg = info["regularMarketChange"]
    chg_pct = info["regularMarketChangePercent"]

    color = "#16a34a" if chg and chg > 0 else "#dc2626"

    st.markdown(f"""
    <div style="margin-bottom:10px">
        <div style="font-size:40px;font-weight:600">
            {price:.2f}
        </div>
        <div style="display:inline-block;
                    background:#e6f4ea;
                    color:{color};
                    padding:6px 14px;
                    border-radius:999px;
                    font-size:18px;
                    font-weight:600;">
            {arrow_html(chg)} {chg:+.2f} ({chg_pct:.2f}%) วันนี้
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- Pre Market ---
    if info["preMarketPrice"] is not None:
        st.markdown(f"""
        <div style="font-size:16px;color:#6b7280">
        ก่อนเปิดตลาด {info["preMarketPrice"]:.2f}
        <span style="color:{'#16a34a' if info['preMarketChange']>0 else '#dc2626'}">
        {arrow_html(info["preMarketChange"])}
        {info["preMarketChange"]:+.2f} ({info["preMarketChangePercent"]:.2f}%)
        </span>
        </div>
        """, unsafe_allow_html=True)

    # --- Post Market ---
    if info["postMarketPrice"] is not None:
        st.markdown(f"""
        <div style="font-size:16px;color:#6b7280">
        หลังปิดตลาด {info["postMarketPrice"]:.2f}
        <span style="color:{'#16a34a' if info['postMarketChange']>0 else '#dc2626'}">
        {arrow_html(info["postMarketChange"])}
        {info["postMarketChange"]:+.2f} ({info["postMarketChangePercent"]:.2f}%)
        </span>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ===== ส่วนเดิม (ไม่แตะ) =====
    st.subheader("📈 กราฟราคา")
    st.line_chart(df["Close"])

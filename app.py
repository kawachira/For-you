import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from datetime import datetime

# =============================
# PAGE CONFIG
# =============================
st.set_page_config(page_title="AI Stock Master", page_icon="💎", layout="wide")

# =============================
# CSS
# =============================
st.markdown("""
<style>
.block-container { padding-top: 2rem; }
h1 { text-align:center; }
</style>
""", unsafe_allow_html=True)

# =============================
# HEADER
# =============================
st.markdown("<h1>💎 AI Stock Master</h1>", unsafe_allow_html=True)

# =============================
# INPUT
# =============================
col1, col2 = st.columns([3,1])
with col1:
    symbol = st.text_input("ชื่อหุ้น", "EOSE").upper()
with col2:
    tf = st.selectbox("Timeframe", ["1d","1wk"])

# =============================
# DATA
# =============================
@st.cache_data(ttl=1800)
def load_data(symbol, tf):
    t = yf.Ticker(symbol)
    df = t.history(period="2y", interval=tf)

    fi = t.fast_info
    info = t.info

    return df, fi, info

# =============================
# ANALYZE
# =============================
if st.button("🚀 วิเคราะห์"):
    df, fi, info = load_data(symbol, tf)

    if df.empty:
        st.error("ไม่พบข้อมูล")
        st.stop()

    # -------------------------
    # INDICATORS
    # -------------------------
    df["EMA20"] = ta.ema(df["Close"], 20)
    df["EMA50"] = ta.ema(df["Close"], 50)
    df["EMA200"] = ta.ema(df["Close"], 200)
    df["RSI"] = ta.rsi(df["Close"], 14)
    macd = ta.macd(df["Close"])
    df = pd.concat([df, macd], axis=1)

    # -------------------------
    # PRICE DATA
    # -------------------------
    price = fi.last_price
    prev_close = fi.previous_close

    change = price - prev_close
    pct = (change / prev_close) * 100

    color = "green" if change >= 0 else "red"
    arrow = "▲" if change >= 0 else "▼"
    sign = "+" if change >= 0 else ""

    # =============================
    # PRICE DISPLAY (เหมือน Google)
    # =============================
    st.markdown(f"""
    <div style="text-align:center">
        <span style="font-size:3rem;font-weight:bold">{price:.2f}</span>
        <span style="font-size:1.2rem"> USD</span>
        <span style="color:{color};font-size:1.4rem">
            {sign}{change:.2f} ({sign}{pct:.2f}%) {arrow} วันนี้
        </span>
    </div>
    """, unsafe_allow_html=True)

    # -------------------------
    # PRE / POST MARKET
    # -------------------------
    market_text = ""
    if fi.pre_market_price:
        pm = fi.pre_market_price - prev_close
        pm_pct = (pm / prev_close) * 100
        market_text = f"ก่อนเปิดตลาด {fi.pre_market_price:.2f} {pm:+.2f} ({pm_pct:+.2f}%)"
    elif fi.post_market_price:
        pm = fi.post_market_price - price
        pm_pct = (pm / price) * 100
        market_text = f"หลังปิดตลาด {fi.post_market_price:.2f} {pm:+.2f} ({pm_pct:+.2f}%)"

    if market_text:
        st.markdown(f"<p style='text-align:center;color:gray'>{market_text}</p>", unsafe_allow_html=True)

    st.divider()

    # =============================
    # SCORE SYSTEM
    # =============================
    score = 0
    reasons = []

    last = df.iloc[-1]

    if price > last.EMA200:
        score += 25; reasons.append("ยืนเหนือ EMA200")
    if last.RSI < 70 and last.RSI > 40:
        score += 20; reasons.append("RSI แข็งแรง")
    if last.MACD_12_26_9 > last.MACDs_12_26_9:
        score += 20; reasons.append("MACD ตัดขึ้น")
    if price > last.EMA50:
        score += 20; reasons.append("ยืนเหนือ EMA50")
    if last.RSI < 30:
        score += 15; reasons.append("Oversold")

    score = min(score, 100)

    # =============================
    # ALERT
    # =============================
    if last.RSI > 70:
        st.warning("⚠️ RSI > 70 : เริ่มร้อน")
    if price < last.EMA200:
        st.error("🚨 หลุด EMA200 : เทรนด์เสีย")

    # =============================
    # DISPLAY
    # =============================
    colA, colB = st.columns(2)

    with colA:
        st.subheader("📊 AI Score")
        st.metric("Bullish Score", f"{score}%")
        for r in reasons:
            st.write("•", r)

    with colB:
        st.subheader("📉 Indicator")
        st.write(f"RSI: {last.RSI:.2f}")
        st.write(f"EMA20 / 50 / 200")
        st.write(f"{last.EMA20:.2f} / {last.EMA50:.2f} / {last.EMA200:.2f}")

    # =============================
    # WATCHLIST
    # =============================
    st.divider()
    st.subheader("⭐ Watchlist (ตัวอย่าง)")
    watchlist = ["EOSE","TSLA","NVDA","AAPL"]

    wl_data = []
    for s in watchlist:
        t = yf.Ticker(s)
        p = t.fast_info.last_price
        wl_data.append({"Symbol":s,"Price":p})

    st.dataframe(pd.DataFrame(wl_data))

import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# =============================
# PAGE CONFIG
# =============================
st.set_page_config(
    page_title="AI Stock Master",
    page_icon="💎",
    layout="wide"
)

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
c1, c2 = st.columns([3, 1])
with c1:
    symbol = st.text_input("ชื่อหุ้น", "EOSE").upper().strip()
with c2:
    tf = st.selectbox("Timeframe", ["1d", "1wk"])

# =============================
# DATA FUNCTIONS
# =============================
@st.cache_data(ttl=1800)
def load_price_data(symbol, tf):
    ticker = yf.Ticker(symbol)
    return ticker.history(period="2y", interval=tf)

def load_realtime(symbol):
    ticker = yf.Ticker(symbol)
    return ticker.fast_info, ticker.info

# =============================
# ANALYZE
# =============================
if st.button("🚀 วิเคราะห์"):
    df = load_price_data(symbol, tf)
    fi, info = load_realtime(symbol)

    if df is None or df.empty:
        st.error("❌ ไม่พบข้อมูลหุ้น")
        st.stop()

    # =============================
    # INDICATORS
    # =============================
    df["EMA20"] = ta.ema(df["Close"], 20)
    df["EMA50"] = ta.ema(df["Close"], 50)
    df["EMA200"] = ta.ema(df["Close"], 200)
    df["RSI"] = ta.rsi(df["Close"], 14)

    macd = ta.macd(df["Close"])
    df = pd.concat([df, macd], axis=1)

    last = df.iloc[-1]

    # =============================
    # PRICE DATA
    # =============================
    price = fi.get("last_price")
    prev_close = fi.get("previous_close")

    if price is None or prev_close is None:
        st.error("❌ ไม่สามารถดึงราคาปัจจุบันได้")
        st.stop()

    change = price - prev_close
    pct = (change / prev_close) * 100

    color = "green" if change >= 0 else "red"
    arrow = "▲" if change >= 0 else "▼"
    sign = "+" if change >= 0 else ""

    # =============================
    # GOOGLE STYLE PRICE
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

    # =============================
    # PRE / POST MARKET
    # =============================
    pre = fi.get("pre_market_price")
    post = fi.get("post_market_price")

    if pre:
        diff = pre - prev_close
        pct2 = (diff / prev_close) * 100
        st.markdown(
            f"<p style='text-align:center;color:gray'>ก่อนเปิดตลาด {pre:.2f} {diff:+.2f} ({pct2:+.2f}%)</p>",
            unsafe_allow_html=True
        )
    elif post:
        diff = post - price
        pct2 = (diff / price) * 100
        st.markdown(
            f"<p style='text-align:center;color:gray'>หลังปิดตลาด {post:.2f} {diff:+.2f} ({pct2:+.2f}%)</p>",
            unsafe_allow_html=True
        )

    st.divider()

    # =============================
    # AI SCORE
    # =============================
    score = 0
    reasons = []

    if price > last.EMA200:
        score += 25
        reasons.append("ยืนเหนือ EMA200")

    if price > last.EMA50:
        score += 20
        reasons.append("ยืนเหนือ EMA50")

    if last.RSI >= 40 and last.RSI <= 70:
        score += 20
        reasons.append("RSI แข็งแรง")

    if last.MACD_12_26_9 > last.MACDs_12_26_9:
        score += 20
        reasons.append("MACD ตัดขึ้น")

    if last.RSI < 30:
        score += 15
        reasons.append("Oversold")

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
        st.subheader("📊 AI Bullish Score")
        st.metric("Score", f"{score}%")
        for r in reasons:
            st.write("•", r)

    with colB:
        st.subheader("📉 Indicator")
        st.write(f"RSI: {last.RSI:.2f}")
        st.write(f"EMA20: {last.EMA20:.2f}")
        st.write(f"EMA50: {last.EMA50:.2f}")
        st.write(f"EMA200: {last.EMA200:.2f}")

    # =============================
    # WATCHLIST
    # =============================
    st.divider()
    st.subheader("⭐ Watchlist")

    watchlist = ["EOSE", "TSLA", "NVDA", "AAPL"]

    rows = []
    for s in watchlist:
        t = yf.Ticker(s)
        p = t.fast_info.get("last_price")
        if p:
            rows.append({"Symbol": s, "Price": round(p, 2)})

    st.dataframe(pd.DataFrame(rows), use_container_width=True)

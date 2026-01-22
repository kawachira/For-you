import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# =====================
# PAGE CONFIG
# =====================
st.set_page_config(page_title="💎 AI Stock Master", layout="wide")
st.title("💎 AI Stock Master")

# =====================
# INPUT
# =====================
symbol = st.text_input("ชื่อหุ้น (เช่น AAPL, TSLA, EOSE)", "EOSE")
timeframe = st.selectbox("Timeframe", ["1d", "1wk", "1mo"])

# =====================
# CACHE ONLY PRICE DATA
# =====================
@st.cache_data
def load_price(symbol, timeframe):
    return yf.download(
        symbol,
        period="6mo",
        interval=timeframe,
        auto_adjust=True,
        progress=False
    )

if symbol:
    df = load_price(symbol, timeframe)

    if df.empty or len(df) < 50:
        st.error("❌ ไม่สามารถดึงข้อมูลราคาได้")
        st.stop()

    # =====================
    # LIVE DATA (NO CACHE)
    # =====================
    ticker = yf.Ticker(symbol)

    try:
        price = ticker.fast_info["last_price"]
        prev_close = ticker.fast_info["previous_close"]
    except:
        price = df["Close"].iloc[-1]
        prev_close = df["Close"].iloc[-2]

    change_pct = (price - prev_close) / prev_close * 100

    # =====================
    # INDICATORS
    # =====================
    df["EMA50"] = df["Close"].ewm(span=50).mean()
    df["EMA200"] = df["Close"].ewm(span=200).mean()

    # RSI
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    rs = gain.rolling(14).mean() / loss.rolling(14).mean()
    df["RSI"] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = df["Close"].ewm(span=12).mean()
    ema26 = df["Close"].ewm(span=26).mean()
    df["MACD"] = ema12 - ema26
    df["Signal"] = df["MACD"].ewm(span=9).mean()

    # =====================
    # SCORE SYSTEM
    # =====================
    score = 0
    if price > df["EMA50"].iloc[-1]: score += 1
    if price > df["EMA200"].iloc[-1]: score += 1
    if df["RSI"].iloc[-1] < 70: score += 1
    if df["MACD"].iloc[-1] > df["Signal"].iloc[-1]: score += 1

    bullish = score / 4 * 100

    # =====================
    # UI
    # =====================
    c1, c2, c3 = st.columns(3)
    c1.metric("📌 ราคา", f"{price:.2f}")
    c2.metric("📈 เปลี่ยนแปลง", f"{change_pct:.2f}%")
    c3.metric("📊 Bullish Score", f"{bullish:.0f}%")

    # =====================
    # ALERTS
    # =====================
    if df["RSI"].iloc[-1] > 70:
        st.warning("⚠ RSI > 70 (Overbought)")

    if price < df["EMA200"].iloc[-1]:
        st.error("🚨 ราคาหลุด EMA200")

    # =====================
    # CHARTS
    # =====================
    st.subheader("📉 Price")
    st.line_chart(df[["Close", "EMA50", "EMA200"]])

    st.subheader("📊 MACD")
    st.line_chart(df[["MACD", "Signal"]])

    st.subheader("📈 RSI")
    st.line_chart(df["RSI"])

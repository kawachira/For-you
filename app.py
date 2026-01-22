import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="💎 AI Stock Master",
    layout="wide"
)

st.title("💎 AI Stock Master")

# =========================
# INPUT
# =========================
symbol = st.text_input("ชื่อหุ้น (เช่น AAPL, TSLA, EOSE)", "EOSE")
timeframe = st.selectbox("Timeframe", ["1d", "1wk", "1mo"])

# =========================
# DATA LOADER (SAFE)
# =========================
@st.cache_data
def load_data(symbol, timeframe):
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="6mo", interval=timeframe)
    info = ticker.info
    fast_info = ticker.fast_info
    return df, info, fast_info

if symbol:
    df, info, fi = load_data(symbol, timeframe)

    if df.empty or len(df) < 50:
        st.error("❌ ดึงข้อมูลไม่สำเร็จ หรือข้อมูลน้อยเกินไป")
        st.stop()

    # =========================
    # SAFE PRICE FETCH
    # =========================
    price = (
        fi.get("last_price")
        or info.get("regularMarketPrice")
        or df["Close"].iloc[-1]
    )

    prev_close = (
        fi.get("previous_close")
        or info.get("regularMarketPreviousClose")
        or df["Close"].iloc[-2]
    )

    if price is None or prev_close is None:
        st.error("❌ ไม่สามารถดึงราคาหุ้นได้")
        st.stop()

    change_pct = (price - prev_close) / prev_close * 100

    # =========================
    # INDICATORS
    # =========================
    # EMA
    df["EMA50"] = df["Close"].ewm(span=50).mean()
    df["EMA200"] = df["Close"].ewm(span=200).mean()

    # RSI
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = df["Close"].ewm(span=12).mean()
    ema26 = df["Close"].ewm(span=26).mean()
    df["MACD"] = ema12 - ema26
    df["Signal"] = df["MACD"].ewm(span=9).mean()

    # =========================
    # SCORE SYSTEM
    # =========================
    score = 0
    max_score = 4

    if price > df["EMA50"].iloc[-1]:
        score += 1
    if price > df["EMA200"].iloc[-1]:
        score += 1
    if df["RSI"].iloc[-1] < 70:
        score += 1
    if df["MACD"].iloc[-1] > df["Signal"].iloc[-1]:
        score += 1

    bullish_pct = score / max_score * 100
    bearish_pct = 100 - bullish_pct

    # =========================
    # DISPLAY
    # =========================
    col1, col2, col3 = st.columns(3)

    col1.metric("📌 ราคา", f"{price:.2f}")
    col2.metric("📈 เปลี่ยนแปลง", f"{change_pct:.2f} %")
    col3.metric("📊 Score", f"{bullish_pct:.0f}% Bullish")

    st.divider()

    # =========================
    # ALERTS
    # =========================
    if df["RSI"].iloc[-1] > 70:
        st.warning("⚠ RSI > 70 (Overbought)")

    if price < df["EMA200"].iloc[-1]:
        st.error("🚨 หลุด EMA200")

    # =========================
    # CHART
    # =========================
    st.subheader("📉 Price Chart")
    st.line_chart(df[["Close", "EMA50", "EMA200"]])

    st.subheader("📊 MACD")
    st.line_chart(df[["MACD", "Signal"]])

    st.subheader("📈 RSI")
    st.line_chart(df["RSI"])

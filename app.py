import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="AI Expert Trader", page_icon="💎", layout="wide")

# ปรับแต่ง CSS เพื่อลดขนาดหัวข้อและสร้างกรอบสีแดง
st.markdown("""
    <style>
    /* ลดขนาด Title และจัดให้อยู่ 2 บรรทัด */
    .block-container h1 {
        font-size: 2.5rem !important;
        padding-top: 0rem !important;
        line-height: 1.2 !important;
    }
    
    /* สร้างกรอบสีแดงใน Sidebar เฉพาะส่วน Form */
    div[data-testid="stForm"] {
        border: 2px solid red;
        padding: 20px;
        border-radius: 10px;
        background-color: #f9f9f9;
    }
    </style>
    """, unsafe_allow_html=True)

# ชื่อแอป 2 บรรทัด (ใช้ <br> ขึ้นบรรทัดใหม่)
st.markdown("<h1>💎 AI Expert Trader<br><span style='font-size: 1.5rem; color: gray;'>ระบบวิเคราะห์หุ้นอัจฉริยะ</span></h1>", unsafe_allow_html=True)

# --- 2. ฟังก์ชันดึงข้อมูล (Cached) ---
@st.cache_data(ttl=3600, show_spinner=False)
def get_stock_data(symbol, period="max", interval="1d"):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        return df, ticker
    except Exception as e:
        return None, None

# --- 3. Sidebar ค้นหา (มีกรอบแดง) ---
with st.sidebar:
    st.header("⚙️ ตั้งค่าการวิเคราะห์")
    
    # ใช้ Form เพื่อให้มีกรอบ (CSS จะจับที่ stForm นี้)
    with st.form(key='search_form'):
        st.markdown("### 🔍 ค้นหาหุ้น")
        symbol_input = st.text_input("ชื่อหุ้น (เช่น PTT.BK, TSLA):", value="EOSE").upper().strip()
        timeframe = st.selectbox("Timeframe:", ["1d", "1wk"], index=0)
        run_btn = st.form_submit_button("🚀 วิเคราะห์เลย")
    
    st.caption("เทคนิค: 1d เล่นสั้น / 1wk ถือยาว")

# --- 4. เริ่มทำงาน ---
if run_btn:
    with st.spinner(f"กำลังประมวลผลข้อมูล {symbol_input}..."):
        try:
            # ดึงข้อมูล
            df, ticker = get_stock_data(symbol_input, interval=timeframe)

            if df is not None and not df.empty:
                # แก้บั๊กหัวตาราง
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)

                # ข้อมูลพื้นฐาน
                info = ticker.info
                pe_ratio = info.get('trailingPE', 'N/A')
                long_name = info.get('longName', symbol_input)
                market_cap = info.get('marketCap', 'N/A')

                # คำนวณอินดิเคเตอร์
                df['EMA20']  = ta.ema(df['Close'], length=20)
                df['EMA50']  = ta.ema(df['Close'], length=50)
                df['EMA200'] = ta.ema(df['Close'], length=200)
                df['RSI'] = ta.rsi(df['Close'], length=14)

                last = df.iloc[-1]
                prev = df.iloc[-2]
                price = last['Close']
                change_val = price - prev['Close']
                change_pct = (change_val / prev['Close']) * 100
                
                # --- แสดงผล Dashboard ---
                
                # Header ชื่อหุ้น
                st.markdown(f"## 🏢 {long_name} ({symbol_input})")
                
                # Metrics
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("ราคาล่าสุด", f"{price:.2f}", f"{change_val:.2f} ({change_pct:.2f}%)")
                
                # RSI พร้อมสี
                rsi_val = last['RSI']
                rsi_delta = "Overbought (แพง)" if rsi_val > 70 else "Oversold (ถูก)" if rsi_val < 30 else "Neutral"
                rsi_color = "inverse" if rsi_val > 70 else "normal"
                c2.metric("RSI (14)", f"{rsi_val:.2f}", delta=rsi_delta, delta_color=rsi_color)
                
                # PE Ratio
                pe_fmt = f"{pe_ratio:.2f}" if isinstance(pe_ratio, (int, float)) else "N/A"
                c3.metric("P/E Ratio", pe_fmt)
                
                # Trend Status
                trend = "ขาขึ้น (Bullish)" if price > last['EMA200'] else "ขาลง (Bearish)"
                c4.success(f"📈 {trend}") if price > last['EMA200'] else c4.error(f"📉 {trend}")

                st.divider()

                # --- กราฟและ AI Report ---
                col_main, col_info = st.columns([2, 1])
                
                with col_main:
                    st.line_chart(df.tail(100)['Close']) # ดึงกราฟ 100 แท่งล่าสุดให้ดูง่าย
                    
                with col_info:
                    st.subheader("🤖 AI Report")
                    if price > last['EMA200']:
                        st.success("✅ **โครงสร้างขาขึ้น**\nราคาอยู่เหนือเส้น EMA 200")
                        st.info("💡 **คำแนะนำ:**\nหาจังหวะย่อซื้อ (Buy on Dip) ตามแนวรับ EMA")
                    else:
                        st.error("🔻 **โครงสร้างขาลง**\nราคาอยู่ใต้เส้น EMA 200")
                        st.warning("💡 **คำแนะนำ:**\nเด้งขาย (Sell on Rise) หรือรอจนกว่าจะยืนเหนือ EMA 200")
                
                # คำอธิบาย RSI (Expander)
                with st.expander("ℹ️ ความหมายของค่า RSI"):
                    st.write("""
                    - **RSI > 70 (Overbought):** ซื้อมากเกินไป ระวังแรงขายทำกำไร (หุ้นอาจย่อ)
                    - **RSI < 30 (Oversold):** ขายมากเกินไป ลุ้นเด้งรีบาวด์ (ของถูกเริ่มน่าสนใจ)
                    - **RSI 50:** จุดกึ่งกลาง วัดพลังซื้อขาย
                    """)
                    
            else:
                st.error(f"❌ ไม่พบข้อมูลหุ้น {symbol_input} หรือตลาดปิด")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {e}")

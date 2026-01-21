import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="Pro Stock Trader", page_icon="📈", layout="wide")
st.title("📈 Pro Stock Trader: ระบบวิเคราะห์หุ้น (Stable)")

# --- 2. ระบบความจำ (Session State) แก้ปัญหากด 2 ที ---
if 'df' not in st.session_state:
    st.session_state.df = None
if 'symbol' not in st.session_state:
    st.session_state.symbol = ""

# --- 3. กล่องค้นหา (Sidebar) ---
with st.sidebar:
    st.header("🔍 ค้นหาหุ้น")
    with st.form(key='my_form'):
        # รับค่าชื่อหุ้น
        symbol_input = st.text_input("ชื่อหุ้น (เช่น EOSE, TSLA, PTT.BK):", value="EOSE").upper().strip()
        # ปุ่มกด
        submit_button = st.form_submit_button(label='🚀 วิเคราะห์ (กดทีเดียว)')

# --- 4. Logic การดึงข้อมูล (ทำงานเมื่อกดปุ่ม) ---
if submit_button:
    with st.spinner(f"กำลังดึงข้อมูล {symbol_input}..."):
        try:
            # ใช้ yf.Ticker จะเสถียรกว่า download ปกติ
            ticker = yf.Ticker(symbol_input)
            df = ticker.history(period="2y")
            
            if df.empty:
                # ลองอีกวิธีถ้าวิธีแรกไม่มา
                df = yf.download(symbol_input, period="2y", progress=False)

            if not df.empty:
                # จัดการข้อมูลให้เรียบร้อยก่อนบันทึก
                df = df.reset_index()
                # แก้ชื่อคอลัมน์ซ้อน (MultiIndex)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [c[0] for c in df.columns]
                # แปลงชื่อคอลัมน์เป็น Title Case (Open, High, Low, Close)
                df.columns = [c.capitalize() for c in df.columns]
                
                # ถ้ามีข้อมูล Save ลงความจำทันที (Session State)
                if 'Close' in df.columns:
                    st.session_state.df = df
                    st.session_state.symbol = symbol_input
                else:
                    st.error("ข้อมูลหุ้นมาไม่ครบ (ไม่มีราคาปิด)")
            else:
                st.error(f"❌ ไม่พบข้อมูลหุ้น: {symbol_input}")
                
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {e}")

# --- 5. ส่วนแสดงผล (ดึงจากความจำมาโชว์) ---
if st.session_state.df is not None:
    # ดึงข้อมูลจากความจำมาใช้
    df = st.session_state.df
    symbol = st.session_state.symbol
    
    # คำนวณ Indicator (คำนวณใหม่ทุกครั้งที่โชว์)
    df['EMA200'] = ta.ema(df['Close'], length=200)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    
    last = df.iloc[-1]
    price = last['Close']
    
    # -- แสดงผล Dashboard --
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("ชื่อหุ้น", symbol)
    with col2:
        st.metric("ราคาปัจจุบัน", f"{price:.2f}")
    with col3:
        st.metric("RSI", f"{last['RSI']:.2f}")

    st.divider()
    
    # -- ส่วนวิเคราะห์ --
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.subheader("📊 กราฟราคา")
        st.line_chart(df.set_index('Date')['Close'])
        
    with c2:
        st.subheader("🤖 AI Analysis")
        
        # Logic การวิเคราะห์
        if pd.notna(last['EMA200']):
            if price > last['EMA200']:
                st.success("✅ **TREND: ขาขึ้น (Uptrend)**")
                st.write(f"ราคายืนเหนือเส้น 200 วัน ({last['EMA200']:.2f})")
                st.info("กลยุทธ์: หาจังหวะย่อซื้อ (Buy on Dip)")
            else:
                st.error("🔻 **TREND: ขาลง (Downtrend)**")
                st.write(f"ราคาอยู่ใต้เส้น 200 วัน ({last['EMA200']:.2f})")
                st.warning("กลยุทธ์: เด้งเพื่อขาย หรือรอ (Wait & See)")
        else:
            st.warning("⚠️ ข้อมูลไม่พอคำนวณเส้น 200 วัน")
            
    # โชว์ข้อมูลดิบกันเหนียว
    with st.expander("ดูข้อมูลย้อนหลัง (Raw Data)"):
        st.dataframe(df.tail())

elif submit_button:
    # กรณีนี้คือพยายามกดแล้วแต่ไม่เจอข้อมูล
    pass
else:
    # หน้าจอแรกเริ่ม
    st.info("👈 กรอกชื่อหุ้นที่เมนูด้านซ้าย แล้วกดปุ่มวิเคราะห์ได้เลยครับ")

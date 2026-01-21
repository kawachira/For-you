import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="Stock Fix", page_icon="🔧", layout="wide")
st.title("🔧 Stock AI: Debug Version")

# --- 2. ส่วนค้นหา ---
with st.sidebar:
    st.header("🔍 ค้นหาหุ้น")
    symbol = st.text_input("ชื่อหุ้น (เช่น TSLA, NVDA, PTT.BK):", value="EOSE").upper().strip()
    st.caption("⚠️ หุ้นไทยต้องมี .BK (เช่น CPALL.BK)")
    
    if st.button("ล้าง Cache (กดเมื่อค้าง)", type="secondary"):
        st.cache_data.clear()

# --- 3. ฟังก์ชันดึงข้อมูล (ใช้ Cache ป้องกันการโดนบล็อก) ---
@st.cache_data(ttl=300) # เก็บข้อมูลไว้ 5 นาที ไม่ต้องโหลดใหม่บ่อยๆ
def get_stock_data(ticker_symbol):
    try:
        # วิธีที่ 1: ใช้ Ticker.history (เสถียรกว่าสำหรับหุ้นรายตัว)
        stock = yf.Ticker(ticker_symbol)
        df = stock.history(period="1y")
        
        # ถ้าวิธี 1 ไม่ได้ผล ลองวิธี 2: download
        if df.empty:
            df = yf.download(ticker_symbol, period="1y", progress=False)
        
        return df
    except Exception as e:
        return None

# --- 4. เริ่มทำงาน ---
if symbol:
    st.subheader(f"ผลการตรวจสอบ: {symbol}")
    
    with st.spinner('กำลังเชื่อมต่อ Yahoo Finance...'):
        df = get_stock_data(symbol)

    # เช็คว่าได้ข้อมูลมาจริงไหม
    if df is None or df.empty:
        st.error(f"❌ ไม่พบข้อมูล: {symbol}")
        st.warning("สาเหตุที่เป็นไปได้:\n1. ชื่อหุ้นผิด (อย่าลืม .BK สำหรับหุ้นไทย)\n2. Yahoo Finance บล็อก IP ของ Streamlit ชั่วคราว (รอ 15 นาทีแล้วลองใหม่)")
    else:
        # --- ถ้ามีข้อมูล ให้จัดการ Format ---
        # Reset Index ให้ Date เป็น Column ปกติ (แก้อาการ Index ซ้อน)
        df = df.reset_index()
        
        # แก้ปัญหา Column ซ้อน (MultiIndex) ที่ yfinance ชอบเป็น
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]
            
        # แปลงชื่อ Column เป็นตัวพิมพ์ใหญ่ทั้งหมด (แก้ปัญหา Close vs close)
        df.columns = [c.capitalize() for c in df.columns]

        # เช็คว่ามีคอลัมน์ราคาไหม
        if 'Close' in df.columns:
            # คำนวณเบื้องต้น
            current_price = df['Close'].iloc[-1]
            
            # --- แสดงผล ---
            col1, col2 = st.columns(2)
            col1.metric("ราคาล่าสุด", f"{current_price:.2f}")
            col1.success("✅ ดึงข้อมูลสำเร็จ!")
            
            # โชว์ตารางข้อมูลดิบ (เพื่อยืนยันว่าข้อมูลมาจริง)
            with st.expander("ดูข้อมูลดิบ (Raw Data)", expanded=True):
                st.dataframe(df.tail(5)) # โชว์ 5 วันล่าสุด
                
            # --- ส่วนกราฟและวิเคราะห์ (ย่อ) ---
            try:
                # คำนวณ RSI & EMA
                df['RSI'] = ta.rsi(df['Close'], length=14)
                df['EMA200'] = ta.ema(df['Close'], length=200)
                
                last_rsi = df['RSI'].iloc[-1]
                
                col2.metric("RSI", f"{last_rsi:.2f}")
                
                st.line_chart(df.set_index('Date')['Close'])
                
            except Exception as e:
                st.warning(f"คำนวณกราฟไม่ได้: {e}")
                
        else:
            st.error("⚠️ ดึงข้อมูลได้ แต่ไม่เจอคอลัมน์ราคา (Close)")
            st.write("คอลัมน์ที่มีตอนนี้:", df.columns.tolist())
            

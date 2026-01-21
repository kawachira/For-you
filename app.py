import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="Stock Anti-Block", page_icon="🛡️", layout="wide")
st.title("🛡️ Stock AI: ระบบป้องกันการโดนบล็อก")

# --- 2. ฟังก์ชันปลอมตัว (Session Hack) ---
def get_session():
    session = requests.Session()
    # ปลอมเป็น Chrome บน Windows เพื่อหลอก Yahoo
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5'
    })
    return session

# --- 3. Sidebar ---
with st.sidebar:
    st.header("🔍 ค้นหาหุ้น")
    symbol_input = st.text_input("ชื่อหุ้น (เช่น EOSE, TSLA, PTT.BK):", value="EOSE").upper().strip()
    
    st.caption("เทคนิค: หากยัง Error ให้กดปุ่ม 'Reboot App' ในเมนูของ Streamlit")
    
    # ปุ่มเริ่มทำงาน
    run_btn = st.button("🚀 วิเคราะห์ (กดเลย)")

# --- 4. เริ่มทำงาน ---
if run_btn:
    with st.spinner(f"กำลังแอบดึงข้อมูล {symbol_input} ..."):
        try:
            # ใช้ Session ที่ปลอมตัวแล้ว ส่งเข้าไปดึงข้อมูล
            session = get_session()
            
            # ดึงข้อมูลผ่าน Ticker โดยยัด Session เข้าไป (ถ้าทำได้)
            ticker = yf.Ticker(symbol_input, session=session)
            df = ticker.history(period="1y")
            
            # ถ้าวิธีแรกไม่มา ลองวิธี download แบบบ้านๆ แต่ใส่ session
            if df.empty:
                # yfinance เวอร์ชั่นใหม่บางทีรับ session โดยตรงไม่ได้ ต้องลอง download ปกติแต่ลุ้น IP
                df = yf.download(symbol_input, period="1y", progress=False)

            if df is None or df.empty:
                st.error(f"❌ ยังคงไม่พบข้อมูล: {symbol_input}")
                st.warning("สาเหตุ: IP ของ Server นี้อาจจะติด Blacklist ของ Yahoo ชั่วคราว")
                st.info("💡 วิธีแก้: ให้กดปุ่ม 3 จุด (มุมขวาบน) -> Manage app -> Reboot app (เพื่อเปลี่ยนเครื่อง Server ใหม่)")
            else:
                # --- จัดการข้อมูลให้สวยงาม ---
                df = df.reset_index()
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [c[0] for c in df.columns]
                
                # ตรวจสอบชื่อคอลัมน์
                df.columns = [c.capitalize() for c in df.columns] # Close, Open, High, Low
                
                if 'Close' in df.columns:
                    # คำนวณค่าต่างๆ
                    last_price = df['Close'].iloc[-1]
                    df['EMA200'] = ta.ema(df['Close'], length=200)
                    df['RSI'] = ta.rsi(df['Close'], length=14)
                    
                    # --- แสดงผล ---
                    st.success(f"✅ ดึงข้อมูลสำเร็จ! ({len(df)} วันทำการ)")
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("ชื่อหุ้น", symbol_input)
                    c2.metric("ราคาล่าสุด", f"{last_price:.2f}")
                    c3.metric("RSI", f"{df['RSI'].iloc[-1]:.2f}")
                    
                    st.line_chart(df.set_index('Date')['Close'])
                    
                    # Logic ง่ายๆ
                    ema200 = df['EMA200'].iloc[-1]
                    if pd.notna(ema200):
                        if last_price > ema200:
                            st.info(f"📈 ขาขึ้น (ราคาอยู่เหนือเส้น 200 วันที่ {ema200:.2f})")
                        else:
                            st.error(f"📉 ขาลง (ราคาอยู่ต่ำกว่าเส้น 200 วันที่ {ema200:.2f})")
                    
                    with st.expander("ดูข้อมูลดิบ"):
                        st.dataframe(df.tail())
                else:
                    st.error("ข้อมูลมาไม่ครบ (ขาดราคา Close)")

        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {e}")
            st.write("ลองกด Reboot App ดูนะครับ")
            

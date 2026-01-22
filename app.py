import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="AI Stock Analyst", page_icon="💎", layout="wide")

# CSS: ปรับแต่งกรอบค้นหาและหัวข้อ
st.markdown("""
    <style>
    /* ปรับแต่ง Title */
    h1 {
        text-align: center;
        font-size: 2.5rem !important;
        margin-bottom: 20px;
    }
    
    /* กรอบแดงสำหรับช่องค้นหา (อยู่กลางหน้า) */
    div[data-testid="stForm"] {
        border: 2px solid red;
        padding: 30px;
        border-radius: 15px;
        background-color: #f8f9fa;
        max-width: 700px;
        margin: 0 auto; /* จัดกึ่งกลาง */
    }
    
    /* ปรับปุ่มกดให้เต็มความกว้าง */
    div[data-testid="stFormSubmitButton"] button {
        width: 100%;
        font-size: 1.2rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ส่วนหัวข้อและช่องค้นหา (อยู่หน้าเดียวกัน) ---
st.markdown("<h1>Ai<br>ระบบวิเคราะห์หุ้นอัจฉริยะ</h1>", unsafe_allow_html=True)

st.write("") # เว้นบรรทัดนิดนึง

# สร้าง Form ค้นหาไว้ตรงกลางหน้าจอ
with st.form(key='search_form'):
    c1, c2 = st.columns([3, 1])
    with c1:
        symbol_input = st.text_input("ชื่อหุ้น (เช่น PTT.BK, TSLA, NVDA):", value="EOSE").upper().strip()
    with c2:
        timeframe = st.selectbox("Timeframe:", ["1d (เล่นสั้น)", "1wk (ถือยาว)"], index=0)
        # แปลงค่ากลับเป็นรหัสที่ถูกต้อง
        tf_code = "1wk" if "1wk" in timeframe else "1d"
        
    submit_btn = st.form_submit_button("🚀 วิเคราะห์หุ้นเดี๋ยวนี้")

# --- 3. ฟังก์ชันดึงข้อมูล (Cached) ---
# แก้ไข: ส่งค่ากลับเฉพาะ DataFrame และ Dictionary เท่านั้น (ห้ามส่ง Ticker object)
@st.cache_data(ttl=3600, show_spinner=False)
def get_stock_data(symbol, interval):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="max", interval=interval)
        
        # ดึงข้อมูล Info ออกมาเก็บใส่ตัวแปรเลย (เพื่อให้ Cache จำได้)
        stock_info = ticker.info 
        
        return df, stock_info
    except:
        return None, None

# --- 4. แสดงผลลัพธ์ ---
if submit_btn:
    st.divider() # ขีดเส้นคั่น
    with st.spinner(f"กำลังให้ AI วิเคราะห์ {symbol_input}..."):
        try:
            # รับค่า df และ info (ที่เป็น Dictionary ธรรมดาแล้ว)
            df, info = get_stock_data(symbol_input, tf_code)

            if df is not None and not df.empty:
                # แก้บั๊กหัวตาราง
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)

                # ดึงข้อมูลจาก Info Dictionary ที่เราเตรียมไว้
                # ใช้ .get() เพื่อป้องกัน Error ถ้าไม่มีข้อมูล
                pe_ratio = info.get('trailingPE', 'N/A')
                long_name = info.get('longName', symbol_input)
                
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
                
                # --- ส่วนแสดงผล Dashboard ---
                
                # Header ชื่อหุ้น
                st.markdown(f"<h2 style='text-align: center;'>🏢 {long_name} ({symbol_input})</h2>", unsafe_allow_html=True)
                
                # Metrics (ราคา, RSI, PE)
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("ราคาล่าสุด", f"{price:.2f}", f"{change_val:.2f} ({change_pct:.2f}%)")
                
                rsi_val = last['RSI']
                rsi_delta = "Overbought" if rsi_val > 70 else "Oversold" if rsi_val < 30 else "Neutral"
                m2.metric("RSI (14)", f"{rsi_val:.2f}", delta=rsi_delta, delta_color="inverse" if rsi_val > 70 else "normal")
                
                pe_show = f"{pe_ratio:.2f}" if isinstance(pe_ratio, (int, float)) else "N/A"
                m3.metric("P/E Ratio", pe_show)
                
                trend = "ขาขึ้น (Bullish)" if price > last['EMA200'] else "ขาลง (Bearish)"
                if price > last['EMA200']:
                    m4.success(f"📈 {trend}")
                else:
                    m4.error(f"📉 {trend}")

                st.write("") # เว้นบรรทัด

                # กราฟราคา
                st.line_chart(df.tail(150)['Close'])
                
                # AI Analysis Box
                st.subheader("🤖 ผลวิเคราะห์จาก AI")
                
                col_ai1, col_ai2 = st.columns(2)
                with col_ai1:
                    if price > last['EMA200']:
                        st.success("✅ **โครงสร้างกราฟ: แข็งแกร่ง (Strong)**\nราคาอยู่เหนือเส้นค่าเฉลี่ย 200 วัน เป็นสัญญาณขาขึ้นระยะยาว")
                    else:
                        st.error("🔻 **โครงสร้างกราฟ: อ่อนแอ (Weak)**\nราคาอยู่ใต้เส้นค่าเฉลี่ย 200 วัน เป็นสัญญาณขาลง ต้องระวัง")
                        
                with col_ai2:
                    if price > last['EMA200']:
                        if price < last['EMA50']:
                            st.info("💡 **กลยุทธ์:** ราคาย่อตัวลงมา (Dip) เป็นโอกาสทยอยสะสม")
                        else:
                            st.info("💡 **กลยุทธ์:** ถือรันเทรนด์ (Let Profit Run) ใช้เส้น 20 วันบังทุน")
                    else:
                        if rsi_val < 30:
                            st.warning("💡 **กลยุทธ์:** เล่นเด้งสั้นๆ (Rebound) ได้ แต่อย่าถือนาน")
                        else:
                            st.warning("💡 **กลยุทธ์:** ชะลอการลงทุน (Wait & See) รอให้กราฟฟื้นตัวก่อน")

                # Expander ความรู้
                with st.expander("📖 คู่มืออ่านค่า RSI (คลิกเพื่ออ่าน)"):
                    st.markdown("""
                    * **RSI > 70:** หุ้นแพง/แรงเกินไป ระวังโดนเทขาย (Overbought)
                    * **RSI < 30:** หุ้นถูก/ลงแรงเกินไป ลุ้นเด้งกลับ (Oversold)
                    * **RSI 50:** จุดวัดใจ ถ้าเกิน 50 คือแรงซื้อชนะ
                    """)
                    
            else:
                st.error(f"❌ ไม่พบข้อมูลหุ้นชื่อ {symbol_input} หรือตลาดปิดอยู่ครับ")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {e}")
            st.warning("ลองกดปุ่ม Reboot App หรือตรวจสอบชื่อหุ้นอีกครั้งครับ")

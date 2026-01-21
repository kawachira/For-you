import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="Stock Analyzer", page_icon="📈", layout="wide")
st.title("📈 Stock Analyzer: ระบบวิเคราะห์หุ้น (Cached)")

# --- 2. ฟังก์ชันดึงข้อมูล (หัวใจสำคัญ: ใส่ Cache ไว้กันโดนบล็อก) ---
# ttl=3600 แปลว่า จำข้อมูลไว้ 1 ชั่วโมง (ถ้าค้นตัวเดิมภายใน 1 ชม. จะไม่ยิง Yahoo ใหม่)
@st.cache_data(ttl=3600, show_spinner=False)
def get_stock_data(symbol):
    try:
        # ปล่อยให้ yf จัดการตัวเอง (ตามที่ Error แนะนำ)
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="2y")
        return df
    except Exception as e:
        return None

# --- 3. Sidebar ค้นหา ---
with st.sidebar:
    st.header("🔍 ค้นหาหุ้น")
    # ใช้ Form เพื่อให้กด Enter ได้และไม่รีโหลดบ่อยเกินไป
    with st.form(key='search_form'):
        symbol_input = st.text_input("ชื่อหุ้น (เช่น EOSE, TSLA, PTT.BK):", value="EOSE").upper().strip()
        submit_btn = st.form_submit_button(label='🚀 วิเคราะห์')
    
    st.caption("ระบบจะจำข้อมูลไว้ 1 ชม. เพื่อลดโอกาสโดนบล็อก")
    
    if st.button("ล้างความจำ (Clear Cache)"):
        st.cache_data.clear()
        st.rerun()

# --- 4. เริ่มทำงาน ---
if submit_btn or symbol_input:
    # โชว์หมุนๆ ตรงนี้แทน
    with st.spinner(f"กำลังดึงข้อมูล {symbol_input}..."):
        df = get_stock_data(symbol_input)

    if df is None or df.empty:
        st.error(f"❌ ไม่พบข้อมูล: {symbol_input}")
        st.warning("สาเหตุที่เป็นไปได้:\n1. ชื่อหุ้นผิด\n2. Server ของ Streamlit โดน Yahoo บล็อก IP (อันนี้ต้องรอ หรือกด Reboot App)")
    else:
        try:
            # --- จัดการข้อมูล ---
            df = df.reset_index()
            # แก้ MultiIndex
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]
            # แก้ชื่อคอลัมน์เป็นตัวพิมพ์ใหญ่
            df.columns = [c.capitalize() for c in df.columns]

            if 'Close' in df.columns:
                # คำนวณ Indicator
                df['EMA200'] = ta.ema(df['Close'], length=200)
                df['RSI'] = ta.rsi(df['Close'], length=14)
                
                last = df.iloc[-1]
                price = last['Close']
                ema200 = last['EMA200']
                
                # --- แสดงผล Dashboard ---
                col1, col2, col3 = st.columns(3)
                col1.metric("ชื่อหุ้น", symbol_input)
                col1.success("✅ ดึงข้อมูลสำเร็จ")
                col2.metric("ราคาล่าสุด", f"{price:.2f}")
                col3.metric("RSI", f"{last['RSI']:.2f}")

                st.divider()

                # กราฟ
                st.line_chart(df.set_index('Date')['Close'])
                
                # Logic วิเคราะห์
                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("🤖 วิเคราะห์เทรนด์")
                    if pd.notna(ema200):
                        if price > ema200:
                            st.success(f"📈 **ขาขึ้น (Uptrend)**\nราคาอยู่เหนือเส้น 200 วัน ({ema200:.2f})")
                        else:
                            st.error(f"📉 **ขาลง (Downtrend)**\nราคาอยู่ต่ำกว่าเส้น 200 วัน ({ema200:.2f})")
                    else:
                        st.warning("ข้อมูลไม่พอคำนวณเส้น EMA 200")
                
                with c2:
                    st.subheader("💡 คำแนะนำ")
                    if pd.notna(ema200):
                        if price > ema200:
                            st.info("หาจังหวะ **Buy on Dip** (ย่อซื้อ) ตามแนวรับ")
                        else:
                            st.warning("ควร **Wait & See** หรือหาจังหวะเด้งขาย (Sell on Rise)")

                # ข้อมูลดิบ
                with st.expander("ดูข้อมูลย้อนหลัง"):
                    st.dataframe(df.tail())
            else:
                st.error("ข้อมูลมาไม่ครบ (ไม่มีราคา Close)")
                
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการคำนวณ: {e}")

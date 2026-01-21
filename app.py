import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="AI Expert Trader", page_icon="💎", layout="wide")
st.title("💎 AI Expert Trader: ระบบวิเคราะห์หุ้นอัจฉริยะ")

# --- 2. ส่วนค้นหา (ใส่ใน Form เพื่อให้กด Enter ได้) ---
with st.sidebar:
    st.header("🔍 ค้นหาหุ้น")
    with st.form(key='search_form'):
        symbol_input = st.text_input("พิมพ์ชื่อหุ้น (เช่น EOSE, TSLA, PTT.BK):", value="EOSE")
        timeframe = st.selectbox("Timeframe:", ["1d", "1wk"], index=0)
        submitted = st.form_submit_button("🚀 วิเคราะห์ (กด Enter)")
        
    st.caption("💡 **Tip:** หุ้นไทยให้เติม .BK (เช่น CPALL.BK, PTT.BK)")

# --- 3. เริ่มทำงาน ---
# (ทำงานทันทีเมื่อกดปุ่ม หรือ เมื่อเปิดเว็บครั้งแรก)
if submitted or symbol_input:
    symbol = symbol_input.upper().strip()
    
    with st.spinner(f"กำลังดึงข้อมูล {symbol}..."):
        try:
            # ดึงข้อมูล (เพิ่ม auto_adjust=True เพื่อลดปัญหาข้อมูลเพี้ยน)
            df = yf.download(symbol, period="2y", interval=timeframe, progress=False, auto_adjust=True)

            # เช็คว่ามีข้อมูลไหม
            if df.empty:
                st.error(f"❌ ไม่พบข้อมูลหุ้นชื่อ: **{symbol}**")
                st.info("คำแนะนำ: \n- ตรวจสอบตัวสะกด \n- ถ้าเป็นหุ้นไทยต้องมี .BK ต่อท้าย \n- ตลาดหุ้นอาจจะปิดอยู่หรือไม่มีข้อมูลในช่วงนี้")
            else:
                # แก้บั๊กหัวตาราง (สำหรับ yfinance เวอร์ชั่นใหม่)
                if isinstance(df.columns, pd.MultiIndex):
                    try:
                        # พยายามดึง level ที่ถูกต้อง
                        df.columns = df.columns.get_level_values(0)
                    except:
                        pass
                
                # ตรวจสอบว่ามีคอลัมน์ Close ไหม (กัน Error)
                if 'Close' not in df.columns and 'Adj Close' in df.columns:
                     df['Close'] = df['Adj Close']

                if 'Close' in df.columns:
                    # --- คำนวณอินดิเคเตอร์ ---
                    df['EMA20']  = ta.ema(df['Close'], length=20)
                    df['EMA50']  = ta.ema(df['Close'], length=50)
                    df['EMA200'] = ta.ema(df['Close'], length=200)
                    df['RSI'] = ta.rsi(df['Close'], length=14)

                    # ข้อมูลล่าสุด
                    last = df.iloc[-1]
                    price = last['Close']
                    
                    # ป้องกัน Error กรณีข้อมูลไม่พอคำนวณ EMA200
                    if pd.isna(last['EMA200']):
                        st.warning("⚠️ ข้อมูลหุ้นตัวนี้มีไม่ถึง 200 วัน ทำให้คำนวณเส้น EMA200 ไม่ได้ครับ")
                        last['EMA200'] = price # ให้ค่าเท่ากับราคาไปก่อนเพื่อไม่ให้ Error

                    # --- LOGIC การวิเคราะห์ ---
                    supports = []
                    trend_status = ""
                    trend_color = ""

                    if price > last['EMA200']:
                        trend_status = "BULLISH (ขาขึ้น)"
                        trend_color = "green"
                        sup_raw = [(last['EMA20'], "EMA 20"), (last['EMA50'], "EMA 50"), (last['EMA200'], "EMA 200")]
                        supports = [s for s in sup_raw if s[0] < price]
                        supports.sort(key=lambda x: x[0], reverse=True)
                    else:
                        trend_status = "BEARISH (ขาลง)"
                        trend_color = "red"
                        # หา Low ย้อนหลัง
                        lows = [
                            (df['Low'].tail(60).min(), "Swing Low ล่าสุด"),
                            (df['Low'].tail(252).min(), "52-Week Low"),
                            (df['Low'].min(), "All-Time Low")
                        ]
                        seen = set()
                        for v, d in lows:
                            if v < (price * 0.999) and v not in seen:
                                supports.append((v, d))
                                seen.add(v)
                        supports.sort(key=lambda x: x[0], reverse=True)

                    # --- แสดงผลหน้าจอ ---
                    c1, c2 = st.columns([1, 2])
                    
                    with c1:
                        st.metric("ราคาล่าสุด", f"{price:.2f}")
                        if price > last['EMA200']:
                            st.success(f"📈 {trend_status}")
                        else:
                            st.error(f"📉 {trend_status}")
                        st.metric("RSI (14)", f"{last['RSI']:.2f}")

                    with c2:
                        st.subheader("🤖 AI Analysis")
                        if price > last['EMA200']:
                            st.info(f"✅ หุ้นเป็นขาขึ้น ใช้เส้น EMA เป็นแนวรับสำคัญ")
                            if supports:
                                st.write(f"🟢 **ไม้แรกที่ควรรอ:** {supports[0][0]:.2f} ({supports[0][1]})")
                        else:
                            st.warning(f"🔻 หุ้นเป็นขาลง ห้ามรับมีด! รอให้ยืนเหนือเส้น 20 วันก่อน")
                            if supports:
                                st.write(f"🟢 **แนวรับถัดไป (รอเด้ง):** {supports[0][0]:.2f} ({supports[0][1]})")
                    
                    st.divider()
                    st.write("📊 **แผนการเทรด (Support Levels):**")
                    if supports:
                        for val, desc in supports:
                            st.write(f"- {desc}: **{val:.2f}**")
                    else:
                        st.write("- ไม่พบแนวรับที่ชัดเจน (ระวัง New Low)")

                else:
                    st.error("ข้อมูลหุ้นตัวนี้ผิดปกติ (ไม่มีราคา Close) ลองเปลี่ยนชื่อหุ้นดูครับ")

        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {e}")

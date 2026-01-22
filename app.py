import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="AI Stock Master", page_icon="💎", layout="wide")

# --- 2. CSS ปรับแต่งความสวยงาม ---
st.markdown("""
    <style>
    /* จัด Title ให้อยู่ตรงกลาง */
    h1 {
        text-align: center;
        font-size: 2.8rem !important;
        margin-bottom: 10px;
    }
    
    /* กรอบค้นหา (สีแดง) ให้อยู่ตรงกลางและดูโปร */
    div[data-testid="stForm"] {
        border: 2px solid #ff4b4b; /* สีแดง */
        padding: 30px;
        border-radius: 15px;
        background-color: #ffffff;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        max-width: 800px;
        margin: 0 auto;
    }
    
    /* ปรับปุ่มกดให้เต็มและตัวใหญ่ */
    div[data-testid="stFormSubmitButton"] button {
        width: 100%;
        border-radius: 10px;
        font-size: 1.2rem;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ส่วนหัวข้อและค้นหา ---
st.markdown("<h1>Ai<br><span style='font-size: 1.5rem; color: gray;'>ระบบวิเคราะห์หุ้นอัจฉริยะ</span></h1>", unsafe_allow_html=True)

st.write("") # เว้นระยะ

# สร้าง Form ค้นหา (จัดกึ่งกลางด้วย Columns)
col_space1, col_form, col_space2 = st.columns([1, 2, 1])

with col_form:
    with st.form(key='search_form'):
        st.markdown("### 🔍 ค้นหาหุ้นที่ต้องการ")
        c1, c2 = st.columns([3, 1])
        with c1:
            symbol_input = st.text_input("ชื่อหุ้น (เช่น PTT.BK, TSLA, BTC-USD):", value="EOSE").upper().strip()
        with c2:
            timeframe = st.selectbox("Timeframe:", ["1d (รายวัน)", "1wk (รายสัปดาห์)"], index=0)
            tf_code = "1wk" if "1wk" in timeframe else "1d"
            
        submit_btn = st.form_submit_button("🚀 วิเคราะห์ทันที")

# --- 4. ฟังก์ชันดึงข้อมูล (ปลอดภัยต่อ Cache) ---
@st.cache_data(ttl=1800, show_spinner=False)
def get_data(symbol, interval):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="2y", interval=interval) # ดึง 2 ปีเพื่อให้คำนวณ EMA200 ได้แม่น
        
        # ดึงเฉพาะข้อมูลที่จำเป็นออกมาเป็น Dictionary (แก้ Error Pickle)
        stock_info = {
            'longName': ticker.info.get('longName', symbol),
            'trailingPE': ticker.info.get('trailingPE', 'N/A'),
            'marketCap': ticker.info.get('marketCap', 'N/A'),
            'sector': ticker.info.get('sector', '-')
        }
        return df, stock_info
    except:
        return None, None

# --- 5. ฟังก์ชันสมอง AI (Advanced Logic) ---
def analyze_market_structure(price, ema20, ema50, ema200, rsi):
    status = ""
    color = ""
    advice = ""
    
    # Logic แยกแยะสถานการณ์
    if price > ema200:
        # โซนขาขึ้น (Uptrend Zone)
        if price > ema20 and price > ema50:
            status = "Strong Uptrend (ขาขึ้นแข็งแกร่ง)"
            color = "green"
            advice = "🟢 **Let Profit Run:** ถือต่อไป ใช้เส้น EMA20 เป็นจุดล็อคกำไร"
            if rsi > 75:
                advice += "\n⚠️ **ระวัง:** RSI สูงมาก (Overbought) ห้ามไล่ราคา อาจมีย่อตัวสั้นๆ"
        elif price < ema50:
            status = "Correction in Uptrend (พักตัวในขาขึ้น)"
            color = "orange"
            advice = "🟡 **Buy on Dip:** ราคาย่อลงมาหาแนวรับ เป็นโอกาสสะสมของ (ถ้ารับอยู่)"
        else:
            status = "Uptrend (ขาขึ้นปกติ)"
            color = "green"
            advice = "🟢 **Hold:** ถือหุ้นต่อ แนวโน้มยังดี"
    else:
        # โซนขาลง (Downtrend Zone)
        if price < ema20 and price < ema50:
            status = "Strong Downtrend (ขาลงรุนแรง)"
            color = "red"
            advice = "🔴 **Avoid/Sell:** ห้ามรับมีด! แรงขายยังเชี่ยว รอให้กราฟสร้างฐานก่อน"
            if rsi < 25:
                advice = "⚡ **Sniper Zone:** RSI ต่ำมาก (Oversold) ลุ้นเด้งสั้นๆ เร็วๆ นี้ (เสี่ยงสูง)"
        elif price > ema20:
            status = "Recovery Attempt (พยายามฟื้นตัว)"
            color = "orange"
            advice = "🟠 **Wait & See:** ราคากำลังสู้เพื่อกลับตัว รอให้ยืนเหนือ EMA50 ให้ได้ก่อนเข้า"
        else:
            status = "Downtrend (ขาลง)"
            color = "red"
            advice = "🔴 **Defensive:** เน้นถือเงินสด หรือเด้งเพื่อขายลดพอร์ต"
            
    return status, color, advice

# --- 6. ส่วนแสดงผล (Display) ---
if submit_btn:
    st.divider()
    with st.spinner(f"AI กำลังประมวลผลกราฟ {symbol_input} ..."):
        df, info = get_data(symbol_input, tf_code)

        if df is not None and not df.empty and len(df) > 200:
            # คำนวณ Indicator
            df['EMA20']  = ta.ema(df['Close'], length=20)
            df['EMA50']  = ta.ema(df['Close'], length=50)
            df['EMA200'] = ta.ema(df['Close'], length=200)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            
            # ข้อมูลล่าสุด
            last = df.iloc[-1]
            prev = df.iloc[-2]
            
            price = last['Close']
            ema20 = last['EMA20']
            ema50 = last['EMA50']
            ema200 = last['EMA200']
            rsi = last['RSI']
            
            change = price - prev['Close']
            change_pct = (change / prev['Close']) * 100

            # เรียกใช้สมอง AI
            ai_status, ai_color, ai_advice = analyze_market_structure(price, ema20, ema50, ema200, rsi)

            # --- เริ่มแสดงผล ---
            
            # 1. Header & Basic Info
            st.markdown(f"<h2 style='text-align: center;'>🏢 {info['longName']} ({symbol_input})</h2>", unsafe_allow_html=True)
            
            # 2. Metrics Bar
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("💰 ราคาล่าสุด", f"{price:.2f}", f"{change:.2f} ({change_pct:.2f}%)")
            
            rsi_txt = "Overbought" if rsi > 70 else "Oversold" if rsi < 30 else "Neutral"
            m2.metric("⚡ RSI (14)", f"{rsi:.2f}", rsi_txt, delta_color="inverse" if rsi > 70 else "normal")
            
            pe_val = info['trailingPE']
            pe_str = f"{pe_val:.2f}" if isinstance(pe_val, (int, float)) else "N/A"
            m3.metric("📊 P/E Ratio", pe_str)
            
            # Trend Status Box
            if ai_color == "green":
                m4.success(f"📈 {ai_status}")
            elif ai_color == "red":
                m4.error(f"📉 {ai_status}")
            else:
                m4.warning(f"⚖️ {ai_status}")

            st.write("") # เว้นบรรทัด

            # 3. Chart & AI Report (แบ่งครึ่งจอ)
            col_chart, col_ai = st.columns([1.8, 1.2])
            
            with col_chart:
                st.subheader("📈 กราฟราคา (Trend)")
                st.line_chart(df.tail(150)['Close'])
            
            with col_ai:
                st.subheader("🤖 บทวิเคราะห์ AI (AI Opinion)")
                
                # กล่องสรุปสถานะ
                if ai_color == "green":
                    st.success(f"**สถานะ:** {ai_status}")
                elif ai_color == "red":
                    st.error(f"**สถานะ:** {ai_status}")
                else:
                    st.warning(f"**สถานะ:** {ai_status}")
                
                # กล่องคำแนะนำ
                with st.chat_message("assistant"):
                    st.write(ai_advice)
                    st.divider()
                    st.markdown("**🔍 ปัจจัยทางเทคนิค:**")
                    st.write(f"- ราคาเทียบเส้น 200 วัน: {'✅ ยืนเหนือ' if price > ema200 else '❌ หลุดต่ำกว่า'} ({ema200:.2f})")
                    st.write(f"- โมเมนตัม RSI: {rsi:.2f} ({rsi_txt})")

            # 4. Support & Resistance Table (Smart Table)
            st.subheader("🚧 แผนการเทรด (Support & Resistance)")
            
            # คำนวณแนวรับต้านอัตโนมัติ
            supports = []
            resistances = []
            
            # แนวต้าน (High เดิม)
            res_val = df['High'].tail(60).max()
            resistances.append((res_val, "High เดิม (60 วัน)"))
            if price < ema200: resistances.append((ema200, "เส้น EMA 200"))
            
            # แนวรับ
            if price > ema200:
                supports.append((ema20, "EMA 20 (รับซิ่ง)"))
                supports.append((ema50, "EMA 50 (รับหลัก)"))
                supports.append((ema200, "EMA 200 (รับสุดท้าย)"))
            else:
                low_val = df['Low'].tail(60).min()
                supports.append((low_val, "Low เดิม (Swing Low)"))
                year_low = df['Low'].tail(252).min()
                supports.append((year_low, "Low รอบ 1 ปี"))

            c_sup, c_res = st.columns(2)
            with c_sup:
                st.markdown("#### 🟢 แนวรับ (จุดรอซื้อ)")
                for v, d in supports:
                    if v < price:
                        st.write(f"- **{v:.2f}** : {d}")
            
            with c_res:
                st.markdown("#### 🔴 แนวต้าน (จุดรอขาย)")
                for v, d in resistances:
                    if v > price:
                        st.write(f"- **{v:.2f}** : {d}")

            # 5. ความรู้เพิ่มเติม (Expander)
            with st.expander("📚 คู่มืออ่านค่า RSI และ P/E"):
                st.markdown("""
                * **RSI (Relative Strength Index):**
                  * > 70: แรงซื้อเยอะเกินไป (ระวังดอย)
                  * < 30: แรงขายเยอะเกินไป (ลุ้นเด้ง)
                * **P/E (Price to Earnings):**
                  * ยิ่งต่ำยิ่งถูก (เทียบกับกลุ่มอุตสาหกรรม)
                  * ถ้า N/A แปลว่าบริษัทขาดทุน หรือไม่มีข้อมูล
                """)

        elif df is not None and len(df) < 200:
             st.warning(f"⚠️ หุ้น {symbol_input} เป็นหุ้นใหม่ (ข้อมูลไม่ถึง 200 วัน) ระบบ AI คำนวณ EMA200 ไม่ได้ครับ")
             st.line_chart(df['Close'])
        else:
            st.error(f"❌ ไม่พบข้อมูลหุ้น: **{symbol_input}**")
            st.info("คำแนะนำ: ตรวจสอบตัวสะกด หรือ ลองเติม .BK ถ้าเป็นหุ้นไทย")

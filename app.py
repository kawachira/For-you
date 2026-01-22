import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="AI Stock Master", page_icon="💎", layout="wide")

# --- 2. CSS ปรับแต่ง (ดันขึ้นบนสุด + ดีไซน์ใหม่) ---
st.markdown("""
    <style>
    /* ดันทุกอย่างขึ้นไปข้างบน ลดพื้นที่ว่างส่วนหัว */
    .block-container {
        padding-top: 1rem !important; /* ลดจากปกติ 5-6rem เหลือ 1rem */
        padding-bottom: 5rem;
    }
    
    /* จัด Title ให้อยู่ตรงกลางและกระชับ */
    h1 {
        text-align: center;
        font-size: 2.2rem !important;
        margin-bottom: 10px;
        margin-top: 0px;
    }
    
    /* กรอบค้นหาแบบ Clean (ไม่มีสีแดง, มีเงา) */
    div[data-testid="stForm"] {
        border: none;
        padding: 20px 30px;
        border-radius: 20px;
        background-color: var(--secondary-background-color);
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        max-width: 800px;
        margin: 0 auto;
    }
    
    /* ปรับปุ่มกด */
    div[data-testid="stFormSubmitButton"] button {
        width: 100%;
        border-radius: 12px;
        font-weight: bold;
    }
    
    /* ปรับขนาด Metric */
    div[data-testid="stMetricValue"] { font-size: 1.6rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ส่วนหัวข้อและค้นหา ---
st.markdown("<h1>💎 Ai ระบบวิเคราะห์หุ้นอัจฉริยะ</h1>", unsafe_allow_html=True)

# สร้าง Form ค้นหา
col_space1, col_form, col_space2 = st.columns([1, 2, 1])
with col_form:
    with st.form(key='search_form'):
        c1, c2 = st.columns([3, 1])
        with c1:
            symbol_input = st.text_input("ชื่อหุ้น (เช่น TSLA, PTT.BK):", value="EOSE").upper().strip()
        with c2:
            timeframe = st.selectbox("Timeframe:", ["1d (รายวัน)", "1wk (รายสัปดาห์)"], index=0)
            tf_code = "1wk" if "1wk" in timeframe else "1d"
        submit_btn = st.form_submit_button("🚀 วิเคราะห์ทันที")

# --- 4. ฟังก์ชันแปลผล (Interpretation) ---
def get_rsi_interpretation(rsi):
    if rsi >= 70: return "🔴 **Overbought (แพงไป):** ระวังย่อตัว"
    elif rsi <= 30: return "🟢 **Oversold (ถูกไป):** ลุ้นเด้งกลับ"
    else: return "⚪ **Neutral (ปกติ):** ราคาสมดุล"

def get_pe_interpretation(pe):
    if pe == 'N/A': return "⚪ ไม่มีข้อมูล"
    if pe < 0: return "🔴 ขาดทุน"
    if pe < 15: return "🟢 หุ้นถูก (Value)"
    if pe > 30: return "🟠 หุ้นแพง (Growth)"
    return "🟡 ราคาเหมาะสม"

# --- 5. ฟังก์ชันดึงข้อมูล (Cache) ---
@st.cache_data(ttl=1800, show_spinner=False)
def get_data(symbol, interval):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="2y", interval=interval)
        
        # ดึงข้อมูลเพิ่มเติม: Pre/Post Market
        # หมายเหตุ: yfinance บางทีอาจไม่ส่ง Pre/Post มาใน history ปกติ ต้องดูจาก info หรือ fast_info
        # แต่เพื่อความง่าย เราจะดึงราคาล่าสุดจาก fast_info แทน
        
        fast_info = ticker.fast_info
        current_price = fast_info.last_price if fast_info.last_price else df['Close'].iloc[-1]
        prev_close = fast_info.previous_close if fast_info.previous_close else df['Close'].iloc[-2]
        
        # ข้อมูลพื้นฐาน
        stock_info = {
            'longName': ticker.info.get('longName', symbol),
            'trailingPE': ticker.info.get('trailingPE', 'N/A'),
            'currency': ticker.info.get('currency', 'USD'),
            # ลองดึงข้อมูล Pre/Post (ถ้ามี)
            'currentPrice': current_price,
            'previousClose': prev_close
        }
        return df, stock_info
    except:
        return None, None

# --- 6. ฟังก์ชันสมอง AI ---
def analyze_market_structure(price, ema20, ema50, ema200, rsi):
    status, color, advice = "", "", ""
    if price > ema200: 
        if price > ema20 and price > ema50:
            status, color = "Strong Uptrend (ขาขึ้นแข็งแกร่ง)", "green"
            advice = "🟢 **Let Profit Run:** ถือต่อไป ใช้ EMA20 ล็อคกำไร"
        elif price < ema50:
            status, color = "Correction (พักตัว)", "orange"
            advice = "🟡 **Buy on Dip:** ย่อหาแนวรับ EMA เป็นโอกาสสะสม"
        else:
            status, color = "Uptrend (ขาขึ้น)", "green"
            advice = "🟢 **Hold:** ถือต่อ แนวโน้มดี"
    else: 
        if price < ema20 and price < ema50:
            status, color = "Strong Downtrend (ขาลงหนัก)", "red"
            advice = "🔴 **Avoid:** ห้ามรับมีด รอสร้างฐาน"
            if rsi < 25: advice = "⚡ **Sniper:** ลุ้นเด้งสั้นๆ (เสี่ยง)"
        elif price > ema20:
            status, color = "Recovery (ฟื้นตัว)", "orange"
            advice = "🟠 **Wait:** รอให้ยืนเหนือ EMA50"
        else:
            status, color = "Downtrend (ขาลง)", "red"
            advice = "🔴 **Defensive:** ถือเงินสด"
    return status, color, advice

# --- 7. ส่วนแสดงผล ---
if submit_btn:
    st.divider()
    with st.spinner(f"AI กำลังคำนวณ {symbol_input}..."):
        df, info = get_data(symbol_input, tf_code)

        if df is not None and not df.empty and len(df) > 200:
            # Indicator Calculation
            df['EMA20'] = ta.ema(df['Close'], length=20)
            df['EMA50'] = ta.ema(df['Close'], length=50)
            df['EMA200'] = ta.ema(df['Close'], length=200)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            
            last = df.iloc[-1]
            # ใช้ราคา Realtime จาก fast_info ที่ดึงมา
            price = info['currentPrice']
            prev_c = info['previousClose']
            
            # คำนวณ % เปลี่ยนแปลง
            change_val = price - prev_c
            change_pct = (change_val / prev_c) * 100
            
            rsi = last['RSI']
            ema20=last['EMA20']; ema50=last['EMA50']; ema200=last['EMA200']
            
            # AI Logic
            ai_status, ai_color, ai_advice = analyze_market_structure(price, ema20, ema50, ema200, rsi)

            # --- HEADER: ชื่อหุ้น ---
            st.markdown(f"<h2 style='text-align: center; margin-bottom: 5px;'>🏢 {info['longName']} ({symbol_input})</h2>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: center; color: gray;'>Currency: {info['currency']}</p>", unsafe_allow_html=True)

            # --- SECTION 1: ราคาและข้อมูลตลาด (Price Info) ---
            # จัดรูปแบบสีราคา (เขียว/แดง)
            price_color = "green" if change_val >= 0 else "red"
            sign = "+" if change_val >= 0 else ""
            
            # แสดงผลแบบ HTML เพื่อจัดระเบียบเอง (Custom Layout)
            st.markdown(f"""
            <div style="display: flex; justify-content: center; align-items: baseline; gap: 15px; margin-bottom: 20px;">
                <span style="font-size: 3rem; font-weight: bold;">{price:,.2f}</span>
                <span style="font-size: 1.5rem; color: {price_color};">
                    {sign}{change_val:.2f} ({sign}{change_pct:.2f}%)
                </span>
            </div>
            """, unsafe_allow_html=True)
            
            # Pre/Post Market (จำลองการแสดงผล)
            # เนื่องจาก yfinance ฟรีอาจไม่ส่ง real-time pre/post แม่นยำตลอดเวลา 
            # เราจะแสดงเป็น Previous Close แทนเพื่อให้เห็นภาพเปรียบเทียบ
            col_mk1, col_mk2 = st.columns(2)
            with col_mk1:
                st.info(f"🕒 **ราคอปิดวันก่อน:** {prev_c:,.2f}")
            with col_mk2:
                # คำนวณ gap เปิดตลาด (ราคาปัจจุบัน vs ปิดวันก่อน)
                gap = price - prev_c
                gap_color = "green" if gap > 0 else "red"
                gap_sign = "+" if gap > 0 else ""
                st.markdown(f"""
                <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; text-align: center;">
                    <b>Gap เปิดตลาด:</b> <span style="color:{gap_color}">{gap_sign}{gap:.2f}</span>
                </div>
                """, unsafe_allow_html=True)

            st.write("") 

            # --- SECTION 2: ตัวเลขสำคัญ (Metrics) & EMA Values ---
            c1, c2, c3, c4 = st.columns(4)
            
            # AI Status
            if ai_color == "green": c1.success(f"📈 {ai_status}")
            elif ai_color == "red": c1.error(f"📉 {ai_status}")
            else: c1.warning(f"⚖️ {ai_status}")

            # RSI
            rsi_txt = "Overbought" if rsi>70 else "Oversold" if rsi<30 else "Neutral"
            c2.metric("⚡ RSI (14)", f"{rsi:.2f}", rsi_txt, delta_color="inverse" if rsi>70 else "normal")
            c2.caption(get_rsi_interpretation(rsi))
            
            # P/E
            pe_val = info['trailingPE']
            pe_str = f"{pe_val:.2f}" if isinstance(pe_val, (int, float)) else "N/A"
            c3.metric("📊 P/E Ratio", pe_str)
            c3.caption(get_pe_interpretation(pe_val))
            
            # EMA Values Show (แสดงค่า EMA เฉยๆ ตามคำขอ)
            with c4:
                st.markdown("**เส้นค่าเฉลี่ย (EMA Values):**")
                st.markdown(f"- EMA 20: **{ema20:.2f}**")
                st.markdown(f"- EMA 50: **{ema50:.2f}**")
                st.markdown(f"- EMA 200: **{ema200:.2f}**")

            st.divider()

            # --- SECTION 3: AI Advice & Support/Resistance ---
            # ไม่มีกราฟแล้ว (ลบออก)
            
            col_ai, col_plan = st.columns([1, 1])
            
            with col_ai:
                st.subheader("🤖 บทวิเคราะห์ AI")
                with st.chat_message("assistant"):
                    st.write(ai_advice)
                    st.write(f"**เหตุผล:** ราคาปัจจุบัน ({price:.2f}) เทียบกับ EMA200 ({ema200:.2f})")

            with col_plan:
                st.subheader("🚧 แผนการเทรด (แนวรับ/ต้าน)")
                
                # Logic แนวรับต้านเดิม (ไม่เกี่ยวกับค่า EMA ที่โชว์เมื่อกี้)
                supports, resistances = [], []
                res_val = df['High'].tail(60).max(); resistances.append((res_val, "High เดิม (60 วัน)"))
                if price < ema200: resistances.append((ema200, "เส้น EMA 200"))
                
                if price > ema200: supports.extend([(ema20, "EMA 20"), (ema50, "EMA 50"), (ema200, "EMA 200")])
                else: supports.extend([(df['Low'].tail(60).min(), "Low เดิม"), (df['Low'].tail(252).min(), "Low 1 ปี")])

                c_sup, c_res = st.columns(2)
                with c_sup:
                    st.markdown("#### 🟢 รอซื้อ (แนวรับ)")
                    for v, d in supports: 
                        if v < price: st.write(f"- **{v:.2f}** : {d}")
                with c_res:
                    st.markdown("#### 🔴 รอขาย (แนวต้าน)")
                    for v, d in resistances:
                        if v > price: st.write(f"- **{v:.2f}** : {d}")

        elif df is not None: st.warning("⚠️ หุ้นใหม่ ข้อมูลไม่พอคำนวณ EMA200"); st.line_chart(df['Close'])
        else: st.error(f"❌ ไม่พบข้อมูลหุ้น: {symbol_input}")

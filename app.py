import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="AI Stock Master", page_icon="💎", layout="wide")

# --- 2. CSS ปรับแต่งความสวยงาม (รองรับ Dark Mode) ---
st.markdown("""
    <style>
    /* จัด Title ให้อยู่ตรงกลาง */
    h1 {
        text-align: center;
        font-size: 2.8rem !important;
        margin-bottom: 10px;
    }
    
    /* กรอบค้นหาแบบใหม่: ไม่มีสีแดง แต่ชัดเจนด้วยเงาและสีพื้นหลังตามธีม */
    div[data-testid="stForm"] {
        border: none; /* เอาขอบสีแดงออก */
        padding: 30px;
        border-radius: 20px; /* มุมโค้งมนขึ้น */
        background-color: var(--secondary-background-color); /* ใช้สีพื้นหลังรองตามธีม (ปรับอัตโนมัติ) */
        box-shadow: 0 8px 24px rgba(0,0,0,0.12); /* เพิ่มเงาให้นูนเด่นชัด */
        max-width: 800px;
        margin: 0 auto;
    }
    
    /* ปรับปุ่มกดให้เต็มและตัวใหญ่ */
    div[data-testid="stFormSubmitButton"] button {
        width: 100%;
        border-radius: 12px;
        font-size: 1.2rem;
        font-weight: bold;
        padding: 15px 0;
    }
    
    /* ปรับขนาดตัวหนังสือใน Metric ให้ใหญ่ขึ้น */
    div[data-testid="metric-container"] label { font-size: 1.1rem; }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] { font-size: 1.8rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ส่วนหัวข้อและค้นหา ---
# เพิ่มรูปเพชรหน้า Ai
st.markdown("<h1>💎 Ai<br><span style='font-size: 1.5rem; opacity: 0.7;'>ระบบวิเคราะห์หุ้นอัจฉริยะ</span></h1>", unsafe_allow_html=True)

st.write("") # เว้นระยะ

# สร้าง Form ค้นหา (จัดกึ่งกลาง)
col_space1, col_form, col_space2 = st.columns([1, 2, 1])

with col_form:
    with st.form(key='search_form'):
        st.markdown("### 🔍 ค้นหาหุ้นที่ต้องการ")
        c1, c2 = st.columns([3, 1])
        with c1:
            symbol_input = st.text_input("ชื่อหุ้น (เช่น PTT.BK, TSLA):", value="EOSE").upper().strip()
        with c2:
            timeframe = st.selectbox("Timeframe:", ["1d (รายวัน)", "1wk (รายสัปดาห์)"], index=0)
            tf_code = "1wk" if "1wk" in timeframe else "1d"
            
        submit_btn = st.form_submit_button("🚀 วิเคราะห์ทันที")

# --- 4. ฟังก์ชันช่วยแปลความหมาย (Interpretation Functions) ---
def get_rsi_interpretation(rsi):
    if rsi >= 80: return "🔴 **Extreme Overbought (แพงสุดขีด):** ระวังแรงเทขายหนัก ห้ามไล่ราคาเด็ดขาด"
    elif rsi >= 70: return "🟠 **Overbought (ซื้อมากเกินไป):** ราคาสูง มีโอกาสย่อตัวพักฐาน"
    elif rsi >= 60: return "🟢 **Strong Bullish (ขาขึ้นแข็งแกร่ง):** โมเมนตัมดี แต่อาจใกล้จุดพักตัวระยะสั้น"
    elif rsi > 40: return "⚪ **Neutral (ปกติ):** ราคาสมดุล เคลื่อนไหวตามเทรนด์หลัก"
    elif rsi > 30: return "🟠 **Bearish (ขาลง):** แรงขายเริ่มเยอะ แนวโน้มอ่อนแอ"
    elif rsi > 20: return "🟢 **Oversold (ขายมากเกินไป):** ราคาถูก เริ่มมีโอกาสเด้งกลับ (Rebound)"
    else: return "🟢 **Extreme Oversold (ถูกสุดขีด):** ราคาลงลึกมาก เป็นจุดวัดใจลุ้นเด้งแรง"

def get_pe_interpretation(pe):
    if isinstance(pe, str) and pe == 'N/A': return "⚪ **N/A:** ไม่มีข้อมูล หรือบริษัทขาดทุน (คำนวณไม่ได้)"
    if pe < 0: return "🔴 **ขาดทุน (Negative P/E):** บริษัทยังไม่มีกำไร"
    if pe < 15: return "🟢 **หุ้นถูก (Low P/E):** ราคาต่ำเมื่อเทียบกับกำไร (Value Stock) หรือตลาดคาดหวังต่ำ"
    if pe < 30: return "🟡 **ราคาเหมาะสม (Average P/E):** ราคาอยู่ในเกณฑ์ค่าเฉลี่ยปกติ"
    return "🟠 **หุ้นแพง (High P/E):** ราคาสูง หรือตลาดคาดหวังการเติบโตสูงมาก (Growth Stock)"

# --- 5. ฟังก์ชันดึงข้อมูล (Cache) ---
@st.cache_data(ttl=1800, show_spinner=False)
def get_data(symbol, interval):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="2y", interval=interval)
        stock_info = {
            'longName': ticker.info.get('longName', symbol),
            'trailingPE': ticker.info.get('trailingPE', 'N/A')
        }
        return df, stock_info
    except:
        return None, None

# --- 6. ฟังก์ชันสมอง AI ---
def analyze_market_structure(price, ema20, ema50, ema200, rsi):
    status, color, advice = "", "", ""
    if price > ema200: # โซนขาขึ้น
        if price > ema20 and price > ema50:
            status, color = "Strong Uptrend (ขาขึ้นแข็งแกร่ง)", "green"
            advice = "🟢 **Let Profit Run:** ถือต่อไป ใช้ EMA20 เป็นจุดล็อคกำไร"
            if rsi > 75: advice += "\n⚠️ **ระวัง:** RSI สูงมาก ห้ามไล่ราคา อาจมีย่อตัว"
        elif price < ema50:
            status, color = "Correction (พักตัวในขาขึ้น)", "orange"
            advice = "🟡 **Buy on Dip:** ราคาย่อหาแนวรับ เป็นโอกาสสะสม (ถ้ารับอยู่)"
        else:
            status, color = "Uptrend (ขาขึ้นปกติ)", "green"
            advice = "🟢 **Hold:** ถือหุ้นต่อ แนวโน้มยังดี"
    else: # โซนขาลง
        if price < ema20 and price < ema50:
            status, color = "Strong Downtrend (ขาลงรุนแรง)", "red"
            advice = "🔴 **Avoid/Sell:** ห้ามรับมีด! แรงขายเชี่ยว รอสร้างฐานก่อน"
            if rsi < 25: advice = "⚡ **Sniper Zone:** RSI ต่ำมาก ลุ้นเด้งสั้นๆ (เสี่ยงสูง)"
        elif price > ema20:
            status, color = "Recovery (พยายามฟื้นตัว)", "orange"
            advice = "🟠 **Wait & See:** ราคากำลังสู้ รอให้ยืนเหนือ EMA50 ก่อน"
        else:
            status, color = "Downtrend (ขาลง)", "red"
            advice = "🔴 **Defensive:** ถือเงินสด หรือเด้งเพื่อขายลดพอร์ต"
    return status, color, advice

# --- 7. ส่วนแสดงผล ---
if submit_btn:
    st.divider()
    with st.spinner(f"AI กำลังประมวลผลกราฟ {symbol_input} ..."):
        df, info = get_data(symbol_input, tf_code)

        if df is not None and not df.empty and len(df) > 200:
            # คำนวณ Indicator
            df['EMA20'] = ta.ema(df['Close'], length=20); df['EMA50'] = ta.ema(df['Close'], length=50)
            df['EMA200'] = ta.ema(df['Close'], length=200); df['RSI'] = ta.rsi(df['Close'], length=14)
            
            last = df.iloc[-1]; prev = df.iloc[-2]
            price = last['Close']; rsi = last['RSI']
            ema20=last['EMA20']; ema50=last['EMA50']; ema200=last['EMA200']
            change = price - prev['Close']; change_pct = (change/prev['Close'])*100

            # AI Analysis
            ai_status, ai_color, ai_advice = analyze_market_structure(price, ema20, ema50, ema200, rsi)

            # --- เริ่มแสดงผล ---
            st.markdown(f"<h2 style='text-align: center; margin-bottom: 25px;'>🏢 {info['longName']} ({symbol_input})</h2>", unsafe_allow_html=True)
            
            # Row 1: ราคา และ สถานะ AI
            c1, c2 = st.columns(2)
            c1.metric("💰 ราคาล่าสุด", f"{price:.2f}", f"{change:.2f} ({change_pct:.2f}%)")
            if ai_color == "green": c2.success(f"📈 {ai_status}")
            elif ai_color == "red": c2.error(f"📉 {ai_status}")
            else: c2.warning(f"⚖️ {ai_status}")

            # Row 2: P/E และ RSI พร้อมคำอธิบายละเอียด
            c3, c4 = st.columns(2)
            with c3:
                pe_val = info['trailingPE']
                pe_str = f"{pe_val:.2f}" if isinstance(pe_val, (int, float)) else "N/A"
                st.metric("📊 P/E Ratio", pe_str)
                st.caption(get_pe_interpretation(pe_val)) # แสดงคำอธิบาย P/E
            with c4:
                rsi_txt = "Overbought" if rsi>70 else "Oversold" if rsi<30 else "Neutral"
                st.metric("⚡ RSI (14)", f"{rsi:.2f}", rsi_txt, delta_color="inverse" if rsi>70 else "normal")
                st.caption(get_rsi_interpretation(rsi)) # แสดงคำอธิบาย RSI

            st.write("") # เว้นบรรทัด

            # Chart & AI Report
            col_chart, col_ai = st.columns([1.8, 1.2])
            with col_chart:
                st.subheader("📈 กราฟราคา (Trend)")
                st.line_chart(df.tail(150)['Close'])
            with col_ai:
                st.subheader("🤖 บทวิเคราะห์ AI")
                with st.chat_message("assistant"):
                    st.write(ai_advice)
                    st.divider()
                    st.markdown(f"**🔍 ปัจจัยทางเทคนิค:**\n- EMA200: {'✅ ยืนเหนือ' if price>ema200 else '❌ หลุดต่ำกว่า'} ({ema200:.2f})\n- RSI: {rsi:.2f} ({rsi_txt})")

            # Support & Resistance
            st.subheader("🚧 แผนการเทรด (Support & Resistance)")
            supports, resistances = [], []
            res_val = df['High'].tail(60).max(); resistances.append((res_val, "High เดิม (60 วัน)"))
            if price < ema200: resistances.append((ema200, "เส้น EMA 200"))
            if price > ema200: supports.extend([(ema20, "EMA 20 (รับซิ่ง)"), (ema50, "EMA 50 (รับหลัก)"), (ema200, "EMA 200 (รับสุดท้าย)")])
            else: supports.extend([(df['Low'].tail(60).min(), "Low เดิม"), (df['Low'].tail(252).min(), "Low รอบ 1 ปี")])

            c_sup, c_res = st.columns(2)
            with c_sup:
                st.markdown("#### 🟢 แนวรับ (จุดรอซื้อ)")
                for v, d in supports: 
                    if v < price: st.write(f"- **{v:.2f}** : {d}")
            with c_res:
                st.markdown("#### 🔴 แนวต้าน (จุดรอขาย)")
                for v, d in resistances:
                    if v > price: st.write(f"- **{v:.2f}** : {d}")

        elif df is not None: st.warning("⚠️ หุ้นใหม่ ข้อมูลไม่พอคำนวณ EMA200"); st.line_chart(df['Close'])
        else: st.error(f"❌ ไม่พบข้อมูลหุ้น: {symbol_input}")

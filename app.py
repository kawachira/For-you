import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="AI Stock Master", page_icon="💎", layout="wide")

# --- 2. CSS ปรับแต่ง (ดันขึ้นบนสุด + ดีไซน์ใหม่) ---
st.markdown("""
    <style>
    /* 1. ดันทุกอย่างขึ้นไปข้างบน ลดพื้นที่ว่างส่วนหัว */
    .block-container {
        padding-top: 2rem !important; 
        padding-bottom: 5rem;
    }
    
    /* จัด Title ให้อยู่ตรงกลางและกระชับ */
    h1 {
        text-align: center;
        font-size: 2.2rem !important;
        margin-bottom: 15px;
        margin-top: 0px;
    }
    
    /* กรอบค้นหาแบบ Clean */
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
st.markdown("<h1>💎 Ai<br><span style='font-size: 1.5rem; opacity: 0.7;'>ระบบวิเคราะห์หุ้นอัจฉริยะ</span></h1>", unsafe_allow_html=True)

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
        
        # พยายามดึงข้อมูล Realtime/Pre-Post Market จาก fast_info
        fast_info = ticker.fast_info
        current_price = fast_info.last_price if fast_info.last_price else df['Close'].iloc[-1]
        prev_close = fast_info.previous_close if fast_info.previous_close else df['Close'].iloc[-2]
        
        # ข้อมูลพื้นฐาน
        stock_info = {
            'longName': ticker.info.get('longName', symbol),
            'trailingPE': ticker.info.get('trailingPE', 'N/A'),
            'currency': ticker.info.get('currency', 'USD'),
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
            advice = "🟢 **Let Profit Run:** ถือต่อไป ใช้ EMA20 เป็นจุดล็อคกำไร"
            if rsi > 75: advice += "\n⚠️ **ระวัง:** RSI สูงมาก ห้ามไล่ราคา อาจมีย่อตัว"
        elif price < ema50:
            status, color = "Correction (พักตัวในขาขึ้น)", "orange"
            advice = "🟡 **Buy on Dip:** ราคาย่อหาแนวรับ เป็นโอกาสสะสม (ถ้ารับอยู่)"
        else:
            status, color = "Uptrend (ขาขึ้นปกติ)", "green"
            advice = "🟢 **Hold:** ถือหุ้นต่อ แนวโน้มยังดี"
    else: 
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
    with st.spinner(f"AI กำลังคำนวณ {symbol_input}..."):
        df, info = get_data(symbol_input, tf_code)

        if df is not None and not df.empty and len(df) > 200:
            # Indicator Calculation
            df['EMA20'] = ta.ema(df['Close'], length=20)
            df['EMA50'] = ta.ema(df['Close'], length=50)
            df['EMA200'] = ta.ema(df['Close'], length=200)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            
            last = df.iloc[-1]
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

            # --- 2. การแสดงผลราคา (ตามรูป) ---
            price_color = "green" if change_val >= 0 else "red"
            sign = "+" if change_val >= 0 else ""
            arrow = "▲" if change_val >= 0 else "▼"
            
            # HTML Layout สำหรับราคาแบบกำหนดเอง
            st.markdown(f"""
            <div style="text-align: center; margin-bottom: 10px;">
                <span style="font-size: 3.5rem; font-weight: bold;">{price:,.2f}</span> 
                <span style="font-size: 1.2rem; color: gray;">{info['currency']}</span>
            </div>
            <div style="text-align: center; font-size: 1.5rem; color: {price_color}; margin-bottom: 20px;">
                {sign}{change_val:.2f} ({sign}{change_pct:.2f}%) {arrow} วันนี้
            </div>
            """, unsafe_allow_html=True)

            # Pre/Post Market (ราคาก่อน/หลังตลาด)
            # เนื่องจากเราใช้ yfinance ฟรี ข้อมูลนี้อาจไม่ real-time ตลอดเวลา แต่มันจะโชว์ถ้ามี gap
            gap = price - prev_c
            mk_status = "ราคาหลังตลาดปิด (Post-Market)" # สมมติฐาน (เพราะ yfinance มักจะอัปเดตช้า)
            
            col_mk1, col_mk2, col_mk3 = st.columns([1, 2, 1])
            with col_mk2:
                st.info(f"🕒 **ราคาก่อน/หลังตลาด:** {prev_c:.2f} (Previous Close)")

            st.divider()

            # --- 3. ข้อมูลสำคัญ (Metrics) & EMA ---
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
            
            # EMA Values (แสดงค่าเฉยๆ)
            with c4:
                st.markdown("**เส้นค่าเฉลี่ย (EMA):**")
                st.markdown(f"- EMA 20: **{ema20:.2f}**")
                st.markdown(f"- EMA 50: **{ema50:.2f}**")
                st.markdown(f"- EMA 200: **{ema200:.2f}**")

            st.write("") 

            # --- 4. AI Advice & Support/Resistance (ลบกราฟออกแล้ว) ---
            col_ai, col_plan = st.columns([1, 1])
            
            with col_ai:
                st.subheader("🤖 บทวิเคราะห์ AI")
                with st.chat_message("assistant"):
                    st.write(ai_advice)
                    st.divider()
                    st.markdown(f"**🔍 ปัจจัยทางเทคนิค:**\n- EMA200: {'✅ ยืนเหนือ' if price>ema200 else '❌ หลุดต่ำกว่า'} ({ema200:.2f})\n- RSI: {rsi:.2f} ({rsi_txt})")

            with col_plan:
                st.subheader("🚧 แผนการเทรด (แนวรับ/ต้าน)")
                # Logic แนวรับต้านเดิม
                supports, resistances = [], []
                res_val = df['High'].tail(60).max(); resistances.append((res_val, "High เดิม (60 วัน)"))
                if price < ema200: resistances.append((ema200, "เส้น EMA 200"))
                
                if price > ema200: supports.extend([(ema20, "EMA 20"), (ema50, "EMA 50"), (ema200, "EMA 200")])
                else: supports.extend([(df['Low'].tail(60).min(), "Low เดิม"), (df['Low'].tail(252).min(), "Low 1 ปี")])

                c_sup, c_res = st.columns(2)
                with c_sup:
                    st.markdown("#### 🟢 แนวรับ")
                    for v, d in supports: 
                        if v < price: st.write(f"- **{v:.2f}** : {d}")
                with c_res:
                    st.markdown("#### 🔴 แนวต้าน")
                    for v, d in resistances:
                        if v > price: st.write(f"- **{v:.2f}** : {d}")

        elif df is not None: st.warning("⚠️ หุ้นใหม่ ข้อมูลไม่พอคำนวณ EMA200"); st.metric("ราคาล่าสุด", f"{info['currentPrice']:.2f}")
        else: st.error(f"❌ ไม่พบข้อมูลหุ้น: {symbol_input}")

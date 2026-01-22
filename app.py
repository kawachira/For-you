import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="AI Stock Master", page_icon="💎", layout="wide")

# --- 2. CSS ปรับแต่งความสวยงาม ---
st.markdown("""
    <style>
    /* ลดระยะห่างด้านบน */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
    }

    /* ล็อคการเลื่อนหน้าจอ (Scroll) เป็นค่าเริ่มต้น */
    div[data-testid="stAppViewContainer"] {
        overflow: hidden !important;
    }

    /* จัด Title ให้อยู่ตรงกลาง */
    h1 {
        text-align: center;
        font-size: 2.8rem !important;
        margin-bottom: 10px;
    }
    
    /* กรอบค้นหาแบบใหม่ */
    div[data-testid="stForm"] {
        border: none;
        padding: 30px;
        border-radius: 20px;
        background-color: var(--secondary-background-color);
        box-shadow: 0 8px 24px rgba(0,0,0,0.12);
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
            timeframe = st.selectbox("Timeframe:", ["1h (รายชั่วโมง)", "1d (รายวัน)", "1wk (รายสัปดาห์)"], index=1)
            
            # Logic แปลงค่าเป็น code ที่ yfinance เข้าใจ
            if "1wk" in timeframe: tf_code = "1wk"
            elif "1h" in timeframe: tf_code = "1h"
            else: tf_code = "1d"
            
        submit_btn = st.form_submit_button("🚀 วิเคราะห์ทันที")

# --- 4. ฟังก์ชันช่วยแปลความหมาย & Helper Functions ---

def arrow_html(change):
    if change is None: return ""
    if change > 0:
        return "<span style='color:#16a34a;font-weight:600'>▲</span>"  # เขียว
    elif change < 0:
        return "<span style='color:#dc2626;font-weight:600'>▼</span>"  # แดง
    else:
        return "<span style='color:gray'>—</span>"

# [แก้ไข] อัปเกรดคำอธิบาย RSI ให้ละเอียดและครบถ้วนขึ้น
def get_rsi_interpretation(rsi):
    if rsi >= 80: return "🔴 **Extreme Overbought (80+):** แรงซื้อบ้าคลั่ง ระวังการเทขายรุนแรง (ห้ามไล่ราคา)"
    elif rsi >= 70: return "🟠 **Overbought (70-80):** ราคาเริ่มตึงตัว อาจมีการเทขายพักฐานเร็วๆ นี้"
    elif rsi >= 55: return "🟢 **Bullish Zone (55-70):** โมเมนตัมกระทิงครองตลาด ราคาแข็งแกร่ง"
    elif rsi >= 45: return "⚪ **Sideway/Neutral (45-55):** แรงซื้อขายก้ำกึ่ง รอเลือกทางที่ชัดเจน"
    elif rsi >= 30: return "🟠 **Bearish Zone (30-45):** โมเมนตัมหมีครองตลาด ระวังราคาไหลลงต่อ"
    elif rsi > 20: return "🟢 **Oversold (20-30):** ขายมากเกินไป เริ่มเข้าเขต 'ของถูก' ลุ้นเด้งรีบาวด์"
    else: return "🟢 **Extreme Oversold (<20):** ลงลึกมาก Panic Sell จบแล้ว เป็นจุดวัดใจซื้อสวนสั้นๆ"

def get_pe_interpretation(pe):
    if isinstance(pe, str) and pe == 'N/A': return "⚪ **N/A:** ไม่มีข้อมูล หรือบริษัทขาดทุน (คำนวณไม่ได้)"
    if pe < 0: return "🔴 **ขาดทุน (Negative P/E):** บริษัทยังไม่มีกำไร"
    if pe < 15: return "🟢 **หุ้นถูก (Low P/E):** ราคาต่ำเมื่อเทียบกับกำไร (Value Stock) หรือตลาดคาดหวังต่ำ"
    if pe < 30: return "🟡 **ราคาเหมาะสม (Average P/E):** ราคาอยู่ในเกณฑ์ค่าเฉลี่ยปกติ"
    return "🟠 **หุ้นแพง (High P/E):** ราคาสูง หรือตลาดคาดหวังการเติบโตสูงมาก (Growth Stock)"

# --- 5. ฟังก์ชันดึงข้อมูล (Cache) ---
@st.cache_data(ttl=60, show_spinner=False)
def get_data(symbol, interval):
    try:
        ticker = yf.Ticker(symbol)
        
        # Logic เลือก Period: 1h รับได้แค่ 730d, อื่นๆ เอา 10y ให้ชัวร์
        if interval == "1h":
            period_val = "730d"
        else:
            period_val = "10y"
            
        df = ticker.history(period=period_val, interval=interval)
        
        stock_info = {
            'longName': ticker.info.get('longName', symbol),
            'trailingPE': ticker.info.get('trailingPE', 'N/A'),
            
            'regularMarketPrice': ticker.info.get('regularMarketPrice'),
            'regularMarketChange': ticker.info.get('regularMarketChange'),
            'regularMarketChangePercent': ticker.info.get('regularMarketChangePercent'),

            'preMarketPrice': ticker.info.get('preMarketPrice'),
            'preMarketChange': ticker.info.get('preMarketChange'),
            'preMarketChangePercent': ticker.info.get('preMarketChangePercent'),

            'postMarketPrice': ticker.info.get('postMarketPrice'),
            'postMarketChange': ticker.info.get('postMarketChange'),
            'postMarketChangePercent': ticker.info.get('postMarketChangePercent'),
        }
        
        if stock_info['regularMarketPrice'] is None and not df.empty:
             stock_info['regularMarketPrice'] = df['Close'].iloc[-1]
             stock_info['regularMarketChange'] = df['Close'].iloc[-1] - df['Close'].iloc[-2]
             stock_info['regularMarketChangePercent'] = (stock_info['regularMarketChange'] / df['Close'].iloc[-2])

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
    # ปลดล็อคให้ Scroll ได้
    st.markdown("""
        <style>
        div[data-testid="stAppViewContainer"] {
            overflow: auto !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.divider()
    with st.spinner(f"AI กำลังประมวลผล {symbol_input} ..."):
        df, info = get_data(symbol_input, tf_code)

        if df is not None and not df.empty and len(df) > 200:
            # คำนวณ Indicator
            df['EMA20'] = ta.ema(df['Close'], length=20); df['EMA50'] = ta.ema(df['Close'], length=50)
            df['EMA200'] = ta.ema(df['Close'], length=200); df['RSI'] = ta.rsi(df['Close'], length=14)
            
            last = df.iloc[-1]; prev = df.iloc[-2]
            price = info['regularMarketPrice'] if info['regularMarketPrice'] else last['Close']
            rsi = last['RSI']
            ema20=last['EMA20']; ema50=last['EMA50']; ema200=last['EMA200']

            # AI Analysis
            ai_status, ai_color, ai_advice = analyze_market_structure(price, ema20, ema50, ema200, rsi)

            # --- เริ่มแสดงผล ---
            
            st.markdown(f"<h2 style='text-align: center; margin-top: -15px; margin-bottom: 25px;'>🏢 {info['longName']} ({symbol_input})</h2>", unsafe_allow_html=True)
            
            # Row 1: ราคา
            c1, c2 = st.columns(2)
            
            with c1:
                reg_price = info.get('regularMarketPrice')
                reg_chg = info.get('regularMarketChange')
                reg_pct = info.get('regularMarketChangePercent')
                if reg_pct and abs(reg_pct) < 1: reg_pct *= 100
                
                color_text = "#16a34a" if reg_chg and reg_chg > 0 else "#dc2626"
                bg_color = "#e8f5ec" if reg_chg and reg_chg > 0 else "#fee2e2"
                
                st.markdown(f"""
                <div style="margin-bottom:10px;">
                  <div style="font-size:40px;font-weight:600;">
                    {reg_price:,.2f}
                  </div>
                  <div style="
                    display:inline-flex; align-items:center; gap:6px;
                    background:{bg_color}; color:{color_text};
                    padding:6px 12px; border-radius:999px;
                    font-size:18px; font-weight:500;
                  ">
                    {arrow_html(reg_chg)}
                    {reg_chg:+.2f} ({reg_pct:.2f}%)
                  </div>
                </div>
                """, unsafe_allow_html=True)

                pre_price = info.get('preMarketPrice')
                pre_chg = info.get('preMarketChange')
                pre_pct = info.get('preMarketChangePercent')
                if pre_pct and abs(pre_pct) < 1: pre_pct *= 100

     อาจมีการพักฐานเร็วๆce = info.get('postMarketPrice')
                post_chg = info.get('postMarketChange')
                post_pct = info.get('postMarketChangePercent')
                if post_pct and abs(post_pct) < 1: post_pct *= 100

                if pre_price and pre_chg is not None:
                    st.markdown(f"""
                    <div style="font-size:14px;color:#6b7280; margin-bottom:2px;">
                        ☀️ ก่อนเปิดตลาด: <b>{pre_price:.2f}</b>
                        <span style="color:{'#16a34a' if pre_chg>0 else '#dc2626'}; margin-left:5px;">
                            {arrow_html(pre_chg)} {pre_chg:+.2f} ({pre_pct:+.2f}%)
                        </span>
                    </div>""", unsafe_allow_html=True)
                
                if post_price and post_chg is not None:
                    st.markdown(f"""
                    <div style="font-size:14px;color:#6b7280;">
                        🌙 หลังปิดตลาด: <b>{post_price:.2f}</b>
                        <span style="color:{'#16a34a' if post_chg>0 else '#dc2626'}; margin-left:5px;">
                            {arrow_html(post_chg)} {post_chg:+.2f} ({post_pct:+.2f}%)
                        </span>
                    </div>""", unsafe_allow_html=True)

            # Logic สร้าง Label ระบุ Timeframe
            if tf_code == "1h": tf_label = "TF 1 Hour"
            elif tf_code == "1wk": tf_label = "TF Week"
            else: tf_label = "TF Day"

            if ai_color == "green": c2.success(f"📈 {ai_status}\n\n**{tf_label}**")
            elif ai_color == "red": c2.error(f"📉 {ai_status}\n\n**{tf_label}**")
            else: c2.warning(f"⚖️ {ai_status}\n\n**{tf_label}**")

            # Row 2: P/E และ RSI
            c3, c4 = st.columns(2)
            with c3:
                pe_val = info['trailingPE']
                pe_str = f"{pe_val:.2f}" if isinstance(pe_val, (int, float)) else "N/A"
                st.metric("📊 P/E Ratio", pe_str)
                st.caption(get_pe_interpretation(pe_val))
            with c4:
                # [แก้ไข] ปรับข้อความ RSI Label ให้สั้นกระชับ
                if rsi >= 70: rsi_label = "Overbought"
                elif rsi <= 30: rsi_label = "Oversold"
                else: rsi_label = "Neutral"
                
                st.metric("⚡ RSI (14)", f"{rsi:.2f}", rsi_label, delta_color="inverse" if rsi>70 else "normal")
                # เรียกใช้ฟังก์ชันแปลความหมาย RSI ตัวใหม่
                st.caption(get_rsi_interpretation(rsi))

            st.write("") 

            # EMA แบบย่อ
            col_ema, col_ai = st.columns([1.5, 1.5])
            
            with col_ema:
                st.subheader("📉 ค่าเส้นค่าเฉลี่ย (EMA)")
                st.markdown(f"""
                    <div style='font-size: 1.1rem; line-height: 1.8;'>
                        <b>EMA 20</b> = {ema20:.2f}<br>
                        <b>EMA 50</b> = {ema50:.2f}<br>
                        <b>EMA 200</b> = {ema200:.2f}
                    </div>
                """, unsafe_allow_html=True)
                
            with col_ai:
                st.subheader("🤖 บทวิเคราะห์ AI")
                with st.chat_message("assistant"):
                    st.write(ai_advice)
                    st.divider()
                    st.markdown(f"**🔍 ปัจจัยทางเทคนิค:**\n- EMA200: {'✅ ยืนเหนือ' if price>ema200 else '❌ หลุดต่ำกว่า'} ({ema200:.2f})\n- RSI: {rsi:.2f} ({rsi_label})")

            # Support & Resistance
            st.subheader("🚧 แผนการเทรด (Support & Resistance)")
            supports, resistances = [], []
            res_val = df['High'].tail(60).max(); resistances.append((res_val, "High เดิม (60 แท่ง)"))
            if price < ema200: resistances.append((ema200, "เส้น EMA 200"))
            if price > ema200: supports.extend([(ema20, "EMA 20 (รับซิ่ง)"), (ema50, "EMA 50 (รับหลัก)"), (ema200, "EMA 200 (รับสุดท้าย)")])
            else: supports.extend([(df['Low'].tail(60).min(), "Low เดิม"), (df['Low'].tail(200).min(), "Low รอบใหญ่")])

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

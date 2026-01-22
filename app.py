import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="AI Stock Master", page_icon="💎", layout="wide")

# --- 2. CSS ปรับแต่ง ---
st.markdown("""
    <style>
    .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; }
    h1 { text-align: center; font-size: 2.8rem !important; margin-bottom: 10px; }
    div[data-testid="stForm"] {
        border: none; padding: 30px; border-radius: 20px;
        background-color: var(--secondary-background-color);
        box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        max-width: 800px; margin: 0 auto;
    }
    div[data-testid="stFormSubmitButton"] button {
        width: 100%; border-radius: 12px; font-size: 1.2rem; font-weight: bold; padding: 15px 0;
    }
    div[data-testid="metric-container"] label { font-size: 1.1rem; }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] { font-size: 1.8rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ส่วนหัวข้อ ---
st.markdown("<h1>💎 Ai<br><span style='font-size: 1.5rem; opacity: 0.7;'>ระบบวิเคราะห์หุ้นอัจฉริยะ</span></h1>", unsafe_allow_html=True)
st.write("")

# --- Form ค้นหา ---
col_space1, col_form, col_space2 = st.columns([1, 2, 1])
with col_form:
    with st.form(key='search_form'):
        st.markdown("### 🔍 ค้นหาหุ้นที่ต้องการ")
        c1, c2 = st.columns([3, 1])
        with c1:
            symbol_input = st.text_input("ชื่อหุ้น (เช่น PTT.BK, TSLA):", value="EOSE").upper().strip()
        with c2:
            timeframe = st.selectbox("Timeframe:", ["1h (รายชั่วโมง)", "1d (รายวัน)", "1wk (รายสัปดาห์)"], index=1)
            if "1wk" in timeframe: tf_code = "1wk"
            elif "1h" in timeframe: tf_code = "1h"
            else: tf_code = "1d"
            
        submit_btn = st.form_submit_button("🚀 วิเคราะห์ทันที / รีเฟรชข้อมูล")

# --- 4. Helper Functions ---
def arrow_html(change):
    if change is None: return ""
    return "<span style='color:#16a34a;font-weight:600'>▲</span>" if change > 0 else "<span style='color:#dc2626;font-weight:600'>▼</span>"

def get_rsi_interpretation(rsi):
    if rsi >= 80: return "🔴 **Extreme Overbought (80+):** แรงซื้อบ้าคลั่ง ระวังการเทขายรุนแรง"
    elif rsi >= 70: return "🟠 **Overbought (70-80):** ราคาเริ่มตึงตัว อาจมีการเทขายพักฐานเร็วๆ นี้"
    elif rsi >= 55: return "🟢 **Bullish Zone (55-70):** โมเมนตัมกระทิงครองตลาด ราคาแข็งแกร่ง"
    elif rsi >= 45: return "⚪ **Sideway/Neutral (45-55):** แรงซื้อขายก้ำกึ่ง รอเลือกทางที่ชัดเจน"
    elif rsi >= 30: return "🟠 **Bearish Zone (30-45):** โมเมนตัมหมีครองตลาด ระวังราคาไหลลงต่อ"
    elif rsi > 20: return "🟢 **Oversold (20-30):** ขายมากเกินไป เริ่มเข้าเขต 'ของถูก' ลุ้นเด้งรีบาวด์"
    else: return "🟢 **Extreme Oversold (<20):** ลงลึกมาก Panic Sell จบแล้ว"

def get_pe_interpretation(pe):
    if isinstance(pe, str) and pe == 'N/A': return "⚪ N/A"
    if pe < 0: return "🔴 ขาดทุน"
    if pe < 15: return "🟢 หุ้นถูก (Value)"
    if pe < 30: return "🟡 ราคาเหมาะสม"
    return "🟠 หุ้นแพง (Growth)"

# --- 5. Get Data (หัวใจสำคัญของการรองรับคนเยอะ) ---
# ttl=60 แปลว่า ข้อมูลจะถูกจำไว้ 60 วินาที 
# ถ้าเพื่อน 100 คนกดหุ้นตัวเดิมใน 1 นาทีนี้ ระบบจะดึงจาก Yahoo แค่ครั้งเดียว!
@st.cache_data(ttl=60, show_spinner=False)
def get_data(symbol, interval):
    try:
        ticker = yf.Ticker(symbol)
        period_val = "730d" if interval == "1h" else "10y"
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

# --- 6. AI Logic ---
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

# --- 7. Display ---
if submit_btn:
    st.divider()
    with st.spinner(f"AI กำลังประมวลผล {symbol_input} ..."):
        df, info = get_data(symbol_input, tf_code)

        if df is not None and not df.empty and len(df) > 200:
            df['EMA20'] = ta.ema(df['Close'], length=20); df['EMA50'] = ta.ema(df['Close'], length=50)
            df['EMA200'] = ta.ema(df['Close'], length=200); df['RSI'] = ta.rsi(df['Close'], length=14)
            
            last = df.iloc[-1]
            price = info['regularMarketPrice'] if info['regularMarketPrice'] else last['Close']
            rsi = last['RSI']
            ema20=last['EMA20']; ema50=last['EMA50']; ema200=last['EMA200']
            ai_status, ai_color, ai_advice = analyze_market_structure(price, ema20, ema50, ema200, rsi)

            # Header
            st.markdown(f"<h2 style='text-align: center; margin-top: -15px; margin-bottom: 25px;'>🏢 {info['longName']} ({symbol_input})</h2>", unsafe_allow_html=True)
            
            # Info Section
            c1, c2 = st.columns(2)
            with c1:
                reg_price = info.get('regularMarketPrice')
                reg_chg = info.get('regularMarketChange')
                reg_pct = info.get('regularMarketChangePercent')
                if reg_pct and abs(reg_pct) < 1: reg_pct *= 100
                
                color_text = "#16a34a" if reg_chg and reg_chg > 0 else "#dc2626"
                bg_color = "#e8f5ec" if reg_chg and reg_chg > 0 else "#fee2e2"
                
                # Main Price
                st.markdown(f"""
                <div style="margin-bottom:5px; display: flex; align-items: center; gap: 15px; flex-wrap: wrap;">
                  <div style="font-size:40px; font-weight:600; line-height: 1;">
                    {reg_price:,.2f} <span style="font-size: 20px; color: #6b7280; font-weight: 400;">USD</span>
                  </div>
                  <div style="
                    display:inline-flex; align-items:center; gap:6px; background:{bg_color}; color:{color_text};
                    padding:4px 12px; border-radius:999px; font-size:18px; font-weight:500;">
                    {arrow_html(reg_chg)} {reg_chg:+.2f} ({reg_pct:.2f}%)
                  </div>
                </div>
                """, unsafe_allow_html=True)

                # Pre/Post Market
                pre_p = info.get('preMarketPrice'); pre_c = info.get('preMarketChange'); pre_pc = info.get('preMarketChangePercent')
                post_p = info.get('postMarketPrice'); post_c = info.get('postMarketChange'); post_pc = info.get('postMarketChangePercent')
                if pre_pc and abs(pre_pc)<1: pre_pc*=100
                if post_pc and abs(post_pc)<1: post_pc*=100

                extra_html = ""
                if pre_p and pre_c is not None:
                    extra_html += f"<div>☀️ ก่อนเปิด: <b>{pre_p:.2f}</b> <span style='color:{'#16a34a' if pre_c>0 else '#dc2626'}'>{arrow_html(pre_c)} {pre_c:+.2f} ({pre_pc:+.2f}%)</span></div>"
                if post_p and post_c is not None:
                    extra_html += f"<div>🌙 หลังปิด: <b>{post_p:.2f}</b> <span style='color:{'#16a34a' if post_c>0 else '#dc2626'}'>{arrow_html(post_c)} {post_c:+.2f} ({post_pc:+.2f}%)</span></div>"
                
                if extra_html:
                    st.markdown(f"<div style='font-size:14px; color:#6b7280; display:flex; gap: 15px; flex-wrap: wrap; margin-top: 5px;'>{extra_html}</div>", unsafe_allow_html=True)

            # AI Status
            tf_label = "TF 1 Hour" if tf_code == "1h" else ("TF Week" if tf_code == "1wk" else "TF Day")
            if ai_color == "green": c2.success(f"📈 {ai_status}\n\n**{tf_label}**")
            elif ai_color == "red": c2.error(f"📉 {ai_status}\n\n**{tf_label}**")
            else: c2.warning(f"⚖️ {ai_status}\n\n**{tf_label}**")

            # Metrics
            c3, c4 = st.columns(2)
            with c3:
                st.metric("📊 P/E Ratio", f"{info['trailingPE']:.2f}" if isinstance(info['trailingPE'], (int,float)) else "N/A")
                st.caption(get_pe_interpretation(info['trailingPE']))
            with c4:
                rsi_lbl = "Overbought" if rsi>=70 else ("Oversold" if rsi<=30 else "Neutral")
                st.metric("⚡ RSI (14)", f"{rsi:.2f}", rsi_lbl, delta_color="inverse" if rsi>70 else "normal")
                st.caption(get_rsi_interpretation(rsi))

            st.write("") 

            # Analysis Section
            c_ema, c_ai = st.columns([1.5, 1.5])
            with c_ema:
                st.subheader("📉 ค่าเส้นค่าเฉลี่ย (EMA)")
                st.markdown(f"<div style='font-size: 1.1rem; line-height: 1.8;'><b>EMA 20</b> = {ema20:.2f}<br><b>EMA 50</b> = {ema50:.2f}<br><b>EMA 200</b> = {ema200:.2f}</div>", unsafe_allow_html=True)
            with c_ai:
                st.subheader("🤖 บทวิเคราะห์ AI")
                with st.chat_message("assistant"):
                    st.write(ai_advice)
                    st.divider()
                    st.markdown(f"**🔍 ปัจจัยทางเทคนิค:**\n- EMA200: {'✅ ยืนเหนือ' if price>ema200 else '❌ หลุดต่ำกว่า'} ({ema200:.2f})\n- RSI: {rsi:.2f} ({rsi_lbl})")

            # S/R
            st.subheader("🚧 แผนการเทรด (Support & Resistance)")
            supports, resistances = [], []
            res_val = df['High'].tail(60).max(); resistances.append((res_val, "High เดิม (60 แท่ง)"))
            if price < ema200: resistances.append((ema200, "เส้น EMA 200"))
            if price > ema200: supports.extend([(ema20, "EMA 20"), (ema50, "EMA 50"), (ema200, "EMA 200")])
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

        elif df is not None: st.warning("⚠️ ข้อมูลไม่พอคำนวณ"); st.line_chart(df['Close'])
        else: st.error(f"❌ ไม่พบข้อมูล: {symbol_input}")

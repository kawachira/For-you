import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="AI Stock Master", page_icon="💎", layout="wide")

# --- 2. CSS ปรับแต่งความสวยงาม ---
st.markdown("""
    <style>
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
    /* ปรับแต่ง Font ให้ดู Modern */
    .price-display { font-family: 'Helvetica', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ส่วนหัวข้อและค้นหา ---
st.markdown("<h1>💎 Ai<br><span style='font-size: 1.5rem; opacity: 0.7;'>ระบบวิเคราะห์หุ้นอัจฉริยะ</span></h1>", unsafe_allow_html=True)
st.write("")

col_space1, col_form, col_space2 = st.columns([1, 2, 1])
with col_form:
    with st.form(key='search_form'):
        st.markdown("### 🔍 ค้นหาหุ้นที่ต้องการ")
        c1, c2 = st.columns([3, 1])
        with c1:
            symbol_input = st.text_input("ชื่อหุ้น (เช่น TSLA, AAPL):", value="EOSE").upper().strip()
        with c2:
            timeframe = st.selectbox("Timeframe:", ["1d (รายวัน)", "1wk (รายสัปดาห์)"], index=0)
            tf_code = "1wk" if "1wk" in timeframe else "1d"
            
        submit_btn = st.form_submit_button("🚀 วิเคราะห์ทันที")

# --- 4. Helper Functions (ส่วนที่เพิ่มเข้ามา) ---
def arrow_html(change):
    if change is None: return ""
    if change > 0:
        return "<span style='color:#16a34a;font-weight:600'>▲</span>" # เขียว
    elif change < 0:
        return "<span style='color:#dc2626;font-weight:600'>▼</span>" # แดง
    else:
        return "<span style='color:gray'>—</span>"

def get_rsi_interpretation(rsi):
    if rsi >= 80: return "🔴 Extreme Overbought (แพงสุดขีด)"
    elif rsi >= 70: return "🟠 Overbought (ระวังย่อ)"
    elif rsi >= 60: return "🟢 Strong Bullish (ขาขึ้นแกร่ง)"
    elif rsi > 40: return "⚪ Neutral (ปกติ)"
    elif rsi > 30: return "🟠 Bearish (ขาลง)"
    elif rsi > 20: return "🟢 Oversold (ขายมากไป)"
    else: return "🟢 Extreme Oversold (จุดวัดใจ)"

# --- 5. ฟังก์ชันดึงข้อมูล (อัปเดตใหม่ตาม Snippet 6) ---
@st.cache_data(ttl=60, show_spinner=False) # ลด ttl เหลือ 60 วิ เพื่อให้ราคา Realtime ขึ้น
def get_data(symbol, interval):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="2y", interval=interval)
        
        # ดึงข้อมูล Realtime/Pre/Post market (Snippet 6)
        stock_info = {
            'longName': ticker.info.get('longName', symbol),
            'trailingPE': ticker.info.get('trailingPE', 'N/A'),
            
            'regularMarketPrice': ticker.info.get('regularMarketPrice'),
            'regularMarketChange': ticker.info.get('regularMarketChange'),
            'regularMarketChangePercent': ticker.info.get('regularMarketChangePercent'), # บางที yfinance ส่งค่ามาเป็น % หรือทศนิยม ต้องเช็ค

            'preMarketPrice': ticker.info.get('preMarketPrice'),
            'preMarketChange': ticker.info.get('preMarketChange'),
            'preMarketChangePercent': ticker.info.get('preMarketChangePercent'),

            'postMarketPrice': ticker.info.get('postMarketPrice'),
            'postMarketChange': ticker.info.get('postMarketChange'),
            'postMarketChangePercent': ticker.info.get('postMarketChangePercent'),
        }
        
        # Fallback กรณี info ไม่มีข้อมูลราคา (ใช้ราคาปิดล่าสุดจาก df แทน)
        if stock_info['regularMarketPrice'] is None and not df.empty:
            last_row = df.iloc[-1]
            prev_row = df.iloc[-2]
            stock_info['regularMarketPrice'] = last_row['Close']
            stock_info['regularMarketChange'] = last_row['Close'] - prev_row['Close']
            stock_info['regularMarketChangePercent'] = (stock_info['regularMarketChange'] / prev_row['Close']) # เป็นทศนิยม
            
        return df, stock_info
    except:
        return None, None

# --- 6. AI Logic ---
def analyze_market_structure(price, ema20, ema50, ema200, rsi):
    status, color, advice = "", "", ""
    if price > ema200: 
        if price > ema20 and price > ema50:
            status, color = "Strong Uptrend", "green"
            advice = "🟢 **Let Profit Run:** ถือต่อ ใช้ EMA20 ล็อคกำไร"
        elif price < ema50:
            status, color = "Correction", "orange"
            advice = "🟡 **Buy on Dip:** ราคาย่อหาแนวรับ โอกาสสะสม"
        else:
            status, color = "Uptrend", "green"
            advice = "🟢 **Hold:** ถือหุ้นต่อ แนวโน้มยังดี"
    else:
        if price < ema20 and price < ema50:
            status, color = "Strong Downtrend", "red"
            advice = "🔴 **Avoid:** อย่าเพิ่งรับมีด รอสร้างฐาน"
        elif price > ema20:
            status, color = "Recovery", "orange"
            advice = "🟠 **Wait & See:** รอยืนเหนือ EMA50"
        else:
            status, color = "Downtrend", "red"
            advice = "🔴 **Defensive:** ถือเงินสด"
    return status, color, advice

# --- 7. ส่วนแสดงผล ---
if submit_btn:
    st.divider()
    with st.spinner(f"AI กำลังประมวลผล {symbol_input} ..."):
        df, info = get_data(symbol_input, tf_code)

        if df is not None and not df.empty and len(df) > 100:
            # คำนวณ Indicator
            df['EMA20'] = ta.ema(df['Close'], length=20); df['EMA50'] = ta.ema(df['Close'], length=50)
            df['EMA200'] = ta.ema(df['Close'], length=200); df['RSI'] = ta.rsi(df['Close'], length=14)
            
            last = df.iloc[-1]
            # ใช้ราคาจาก info ก่อน ถ้าไม่มีให้ใช้จาก df (สำหรับการคำนวณกราฟ)
            calc_price = info['regularMarketPrice'] if info['regularMarketPrice'] else last['Close']
            rsi = last['RSI']
            ema20=last['EMA20']; ema50=last['EMA50']; ema200=last['EMA200']

            # AI Analysis
            ai_status, ai_color, ai_advice = analyze_market_structure(calc_price, ema20, ema50, ema200, rsi)

            # --- เริ่มแสดงผล Header ---
            st.markdown(f"<h2 style='text-align: center; margin-bottom: 5px;'>🏢 {info['longName']} ({symbol_input})</h2>", unsafe_allow_html=True)
            
            # --- ส่วนแสดงราคาใหม่ (Snippet 8 + 4 + 5) ---
            # ดึงค่าตัวแปร
            price = info.get('regularMarketPrice')
            chg = info.get('regularMarketChange')
            chg_pct = info.get('regularMarketChangePercent')
            
            # ปรับหน่วย % (บางทีมาเป็น 0.05 แทน 5.0)
            if chg_pct and abs(chg_pct) < 1: chg_pct *= 100 

            # สีหลัก
            main_color = "#16a34a" if chg and chg >= 0 else "#dc2626"
            bg_color = "#e8f5ec" if chg and chg >= 0 else "#fee2e2" # ปรับพื้นหลังให้เข้ากับสี (เขียวอ่อน/แดงอ่อน)

            # สร้าง HTML ราคาหลัก (Snippet 8)
            st.markdown(f"""
            <div style="text-align: center; margin-bottom: 20px;">
              <div style="font-size:50px;font-weight:700;line-height:1.2;">
                {price:,.2f}
              </div>
              <div style="
                display:inline-flex; align-items:center; gap:8px;
                background:{bg_color}; color:{main_color};
                padding:8px 16px; border-radius:30px;
                font-size:20px; font-weight:600; margin-top:5px;
              ">
                {arrow_html(chg)}
                {chg:+.2f} ({chg_pct:+.2f}%)
              </div>
            </div>
            """, unsafe_allow_html=True)

            # สร้าง HTML Pre/Post Market (Snippet 4, 5, 9)
            pre_price = info.get('preMarketPrice')
            pre_chg = info.get('preMarketChange')
            pre_pct = info.get('preMarketChangePercent')
            if pre_pct and abs(pre_pct) < 1: pre_pct *= 100

            post_price = info.get('postMarketPrice')
            post_chg = info.get('postMarketChange')
            post_pct = info.get('postMarketChangePercent')
            if post_pct and abs(post_pct) < 1: post_pct *= 100
            
            # แสดง Pre/Post แบบจัดกึ่งกลาง
            c_pre, c_post = st.columns(2)
            with c_pre:
                if pre_price and pre_chg is not None:
                    st.markdown(f"""
                    <div style="text-align:right; font-size:16px; color:#6b7280;">
                        ☀️ ก่อนเปิดตลาด: <b>{pre_price:.2f}</b>
                        <span style="color:{'#16a34a' if pre_chg>0 else '#dc2626'}; margin-left:5px;">
                            {arrow_html(pre_chg)} {pre_chg:+.2f} ({pre_pct:+.2f}%)
                        </span>
                    </div>""", unsafe_allow_html=True)
            with c_post:
                if post_price and post_chg is not None:
                    st.markdown(f"""
                    <div style="text-align:left; font-size:16px; color:#6b7280;">
                        🌙 หลังปิดตลาด: <b>{post_price:.2f}</b>
                        <span style="color:{'#16a34a' if post_chg>0 else '#dc2626'}; margin-left:5px;">
                            {arrow_html(post_chg)} {post_chg:+.2f} ({post_pct:+.2f}%)
                        </span>
                    </div>""", unsafe_allow_html=True)

            st.write("") 
            st.divider()

            # --- ส่วน Technical เดิม ---
            c3, c4, c5 = st.columns([1, 1, 2])
            with c3:
                pe_val = info['trailingPE']
                pe_str = f"{pe_val:.2f}" if isinstance(pe_val, (int, float)) else "N/A"
                st.metric("📊 P/E Ratio", pe_str)
            with c4:
                rsi_txt = "Overbought" if rsi>70 else "Oversold" if rsi<30 else "Neutral"
                st.metric("⚡ RSI (14)", f"{rsi:.2f}", rsi_txt)
            with c5:
                if ai_color == "green": st.success(f"📈 {ai_status}\n\n{ai_advice}")
                elif ai_color == "red": st.error(f"📉 {ai_status}\n\n{ai_advice}")
                else: st.warning(f"⚖️ {ai_status}\n\n{ai_advice}")

            # Chart
            col_chart, col_data = st.columns([2, 1])
            with col_chart:
                st.subheader("📈 Trend Chart")
                st.line_chart(df.tail(150)['Close'])
            
            with col_data:
                st.subheader("🚧 Key Levels")
                if calc_price > ema200:
                    st.markdown(f"**Support (แนวรับ):**")
                    st.write(f"- EMA20: {ema20:.2f}")
                    st.write(f"- EMA50: {ema50:.2f}")
                    st.write(f"- EMA200: {ema200:.2f}")
                else:
                    st.markdown(f"**Resistance (แนวต้าน):**")
                    st.write(f"- EMA200: {ema200:.2f}")
                    st.write(f"- EMA50: {ema50:.2f}")
                    st.write(f"- EMA20: {ema20:.2f}")

        elif df is not None: 
            st.warning("⚠️ ข้อมูลหุ้นมาใหม่ อินดิเคเตอร์ยังคำนวณไม่ได้"); st.line_chart(df['Close'])
        else: st.error(f"❌ ไม่พบข้อมูลหุ้น: {symbol_input}")

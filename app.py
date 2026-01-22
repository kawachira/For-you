import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="AI Stock Master Pro", page_icon="💎", layout="wide")

# --- 2. CSS ปรับแต่งความสวยงาม (Pro Theme) ---
st.markdown("""
    <style>
    h1 { text-align: center; font-size: 2.5rem !important; margin-bottom: 10px; }
    
    div[data-testid="stForm"] {
        border: none; padding: 25px; border-radius: 15px;
        background-color: var(--secondary-background-color);
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        max-width: 900px; margin: 0 auto;
    }
    
    div[data-testid="stFormSubmitButton"] button {
        width: 100%; border-radius: 10px; font-weight: bold; height: 50px;
    }
    
    /* ปรับแต่ง Metric ให้ดูแพง */
    div[data-testid="stMetricValue"] { font-size: 1.6rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ส่วนหัวข้อและค้นหา ---
st.markdown("<h1>💎 AI Stock Master <span style='color:#FFD700;'>PRO</span></h1>", unsafe_allow_html=True)
st.write("")

# สร้าง Form ค้นหา
with st.form(key='search_form'):
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        symbol_input = st.text_input("ชื่อหุ้น (Symbol)", value="TSLA", placeholder="เช่น PTT.BK, AAPL").upper().strip()
    with c2:
        timeframe = st.selectbox("Timeframe", ["1d (Day)", "1wk (Week)", "1h (Hour)"], index=0)
    with c3:
        # ปุ่มกด
        st.write("") # ดันปุ่มลงมาหน่อย
        submit_btn = st.form_submit_button("🚀 วิเคราะห์กราฟ")

    # แปลงค่า Timeframe ให้ yfinance เข้าใจ
    tf_map = {"1d (Day)": "1d", "1wk (Week)": "1wk", "1h (Hour)": "1h"}
    tf_code = tf_map[timeframe]
    period = "730d" if tf_code == "1d" else "2y" if tf_code == "1wk" else "60d"

# --- 4. ฟังก์ชันคำนวณและแปลผล ---
def get_rsi_interpretation(rsi):
    if rsi >= 70: return "🔴 Overbought (ระวังแรงขาย)"
    elif rsi <= 30: return "🟢 Oversold (ลุ้นเด้ง)"
    return "⚪ Neutral (ปกติ)"

# ฟังก์ชันหา FVG (Fair Value Gap) - หัวใจของ ICT
def find_fvg(df):
    fvg_list = []
    # วนลูปย้อนหลังหา FVG ล่าสุด 3 จุด
    for i in range(len(df)-1, 2, -1):
        # Bullish FVG (แท่ง 1 High < แท่ง 3 Low)
        if df['Low'].iloc[i] > df['High'].iloc[i-2]:
            fvg_list.append({
                'type': 'Bullish 🟢',
                'top': df['Low'].iloc[i],
                'bottom': df['High'].iloc[i-2],
                'index': df.index[i]
            })
        # Bearish FVG (แท่ง 1 Low > แท่ง 3 High)
        elif df['High'].iloc[i] < df['Low'].iloc[i-2]:
            fvg_list.append({
                'type': 'Bearish 🔴',
                'top': df['Low'].iloc[i-2],
                'bottom': df['High'].iloc[i],
                'index': df.index[i]
            })
        if len(fvg_list) >= 2: break # เอาแค่ 2 อันล่าสุดพอ กันรก
    return fvg_list

# --- 5. ฟังก์ชันดึงข้อมูล ---
@st.cache_data(ttl=300)
def get_data(symbol, p, i):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=p, interval=i)
        return df, ticker.info
    except: return None, None

# --- 6. ส่วนแสดงผล ---
if submit_btn:
    st.divider()
    with st.spinner(f"AI กำลังสแกนหาโครงสร้างราคา {symbol_input}..."):
        df, info = get_data(symbol_input, period, tf_code)
        
        if df is not None and not df.empty:
            # คำนวณ Indicator
            df['EMA20'] = ta.ema(df['Close'], length=20)
            df['EMA50'] = ta.ema(df['Close'], length=50)
            df['EMA200'] = ta.ema(df['Close'], length=200)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            
            # ข้อมูลล่าสุด
            last = df.iloc[-1]
            price = last['Close']
            change = price - df.iloc[-2]['Close']
            pct = (change / df.iloc[-2]['Close']) * 100
            
            # ----------------------------------
            # A. ส่วนแสดงผลข้อมูลพื้นฐาน (Header)
            # ----------------------------------
            st.markdown(f"### 🏢 {info.get('longName', symbol_input)}")
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            
            col_m1.metric("ราคาล่าสุด", f"{price:,.2f}", f"{change:+.2f} ({pct:+.2f}%)")
            col_m2.metric("RSI (14)", f"{last['RSI']:.2f}", get_rsi_interpretation(last['RSI']))
            
            trend = "Bullish 🟢" if price > last['EMA200'] else "Bearish 🔴"
            col_m3.metric("Trend (EMA200)", trend, f"เส้น 200: {last['EMA200']:.2f}", delta_color="off")
            
            vol_stat = "High" if last['Volume'] > df['Volume'].mean() else "Normal"
            col_m4.metric("Volume", f"{last['Volume']/1000000:.1f}M", vol_stat)

            # ----------------------------------
            # B. กราฟเทคนิค Interactive (Plotly)
            # ----------------------------------
            st.subheader("📊 Chart & ICT Analysis")
            
            fig = go.Figure()

            # 1. แท่งเทียน
            fig.add_trace(go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                name="Price"
            ))

            # 2. เส้น EMA
            colors = ['#FFD700', '#00BFFF', '#FF4500'] # ทอง, ฟ้า, ส้มแดง
            for idx, ema in enumerate(['EMA20', 'EMA50', 'EMA200']):
                if df[ema].iloc[-1] > 0: # เช็คว่ามีค่า
                    fig.add_trace(go.Scatter(x=df.index, y=df[ema], line=dict(color=colors[idx], width=1.5), name=ema))

            # 3. วาดกล่อง FVG (ICT Concept)
            fvgs = find_fvg(df)
            for fvg in fvgs:
                fill_col = "rgba(0, 255, 0, 0.1)" if "Bullish" in fvg['type'] else "rgba(255, 0, 0, 0.1)"
                border_col = "green" if "Bullish" in fvg['type'] else "red"
                
                # วาดสี่เหลี่ยม
                fig.add_shape(type="rect",
                    x0=fvg['index'], y0=fvg['bottom'], x1=df.index[-1], y1=fvg['top'],
                    fillcolor=fill_col, line=dict(color=border_col, width=1, dash="dot")
                )
                # ใส่ Label
                fig.add_annotation(x=df.index[-1], y=fvg['top'], text=f"FVG {fvg['type']}", showarrow=False, xanchor="left")

            # จัดหน้าตากราฟ
            fig.update_layout(
                height=600, 
                xaxis_rangeslider_visible=False,
                template="plotly_dark",
                margin=dict(l=0, r=0, t=30, b=0),
                legend=dict(orientation="h", y=1, x=0, xanchor="left")
            )

            st.plotly_chart(fig, use_container_width=True)

            # ----------------------------------
            # C. AI สรุปผล
            # ----------------------------------
            with st.expander("🧠 อ่านบทวิเคราะห์ AI แบบละเอียด (คลิก)", expanded=True):
                advice_col, signal_col = st.columns([2, 1])
                
                with advice_col:
                    st.markdown("#### คำแนะนำการเทรด")
                    if price > last['EMA200']:
                        if last['RSI'] < 30: st.info("🔥 **Opportunity:** หุ้นเป็นขาขึ้นแต่ย่อตัวหนัก (Oversold) หาจังหวะเข้าทำกำไรได้")
                        elif price < last['EMA20']: st.warning("🟡 **Pullback:** ราคาย่อตัวลงมาต่ำกว่า EMA20 รอให้ยืนเหนือเส้นนี้ก่อนค่อยเข้า")
                        else: st.success("🚀 **Strong Trend:** ราคาแข็งแกร่ง รันเทรนด์ต่อไป (Let profit run)")
                    else:
                        st.error("⛔ **Downtrend:** หุ้นเป็นขาลง ควร Wait & See หรือเล่นเด้งสั้นๆ เท่านั้น")

                with signal_col:
                    st.markdown("#### ตรวจจับ ICT")
                    if fvgs:
                        for fvg in fvgs:
                            st.write(f"- พบ **{fvg['type']}** ช่วงราคา {fvg['bottom']:.2f} - {fvg['top']:.2f}")
                    else:
                        st.write("- ไม่พบ FVG ที่ชัดเจนในช่วงล่าสุด")

        else:
            st.error("❌ ไม่พบข้อมูลหุ้น หรือชื่อหุ้นผิด กรุณาลองใหม่")

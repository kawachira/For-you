import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots  # <--- เพิ่มตัวช่วยสร้างกราฟย่อย (ราคา+Volume)

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="AI Stock Master", page_icon="💎", layout="wide")

# --- 2. CSS ปรับแต่ง (TradingView Style) ---
st.markdown("""
    <style>
    .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; }
    h1 { text-align: center; font-size: 2.8rem !important; margin-bottom: 10px; }
    /* ปรับแต่ง Form */
    div[data-testid="stForm"] {
        border: none; padding: 20px; border-radius: 15px;
        background-color: #1e222d; /* สีพื้นหลังแบบ TV */
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        max-width: 800px; margin: 0 auto; color: white;
    }
    div[data-testid="stFormSubmitButton"] button {
        width: 100%; border-radius: 8px; font-weight: bold; padding: 12px 0;
        background-color: #2962ff; color: white; border: none;
    }
    div[data-testid="stFormSubmitButton"] button:hover {
        background-color: #1e54e4;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ส่วนหัวข้อ ---
st.markdown("<h1>💎 Ai<br><span style='font-size: 1.5rem; opacity: 0.7;'>ระบบวิเคราะห์หุ้นอัจฉริยะ</span></h1>", unsafe_allow_html=True)
st.write("")

# --- Form ค้นหา ---
col_space1, col_form, col_space2 = st.columns([1, 2, 1])
with col_form:
    with st.form(key='search_form'):
        st.markdown("### 🔍 ค้นหาหุ้น (TradingView Style)")
        c1, c2 = st.columns([3, 1])
        with c1:
            symbol_input = st.text_input("ชื่อหุ้น (เช่น AMZN, TSLA):", value="EOSE").upper().strip()
        with c2:
            timeframe = st.selectbox("Timeframe:", ["1h", "1d", "1wk"], index=1)
            if "1wk" in timeframe: tf_code = "1wk"
            elif "1h" in timeframe: tf_code = "1h"
            else: tf_code = "1d"
            
        submit_btn = st.form_submit_button("🚀 วิเคราะห์กราฟ")

# --- 4. Helper Functions ---
def arrow_html(change):
    if change is None: return ""
    return "<span style='color:#089981;font-weight:600'>▲</span>" if change > 0 else "<span style='color:#f23645;font-weight:600'>▼</span>"

def get_rsi_interpretation(rsi):
    if rsi >= 80: return "🔴 Extreme Overbought"
    elif rsi >= 70: return "🟠 Overbought"
    elif rsi >= 55: return "🟢 Bullish Zone"
    elif rsi >= 45: return "⚪ Neutral"
    elif rsi >= 30: return "🟠 Bearish Zone"
    elif rsi > 20: return "🟢 Oversold"
    else: return "🟢 Extreme Oversold"

def get_pe_interpretation(pe):
    if isinstance(pe, str) and pe == 'N/A': return "⚪ N/A"
    if pe < 0: return "🔴 Loss"
    if pe < 15: return "🟢 Value"
    if pe < 30: return "🟡 Fair"
    return "🟠 Growth"

# --- 5. Get Data ---
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
        }
        
        if stock_info['regularMarketPrice'] is None and not df.empty:
             stock_info['regularMarketPrice'] = df['Close'].iloc[-1]
             stock_info['regularMarketChange'] = df['Close'].iloc[-1] - df['Close'].iloc[-2]

        return df, stock_info
    except:
        return None, None

# --- 6. AI Logic ---
def analyze_market_structure(price, ema20, ema50, ema200, rsi):
    status, color, advice = "", "", ""
    if price > ema200:
        if price > ema20 and price > ema50:
            status, color = "Strong Uptrend", "green"
            advice = "🟢 **BUY / HOLD:** เทรนด์ขาขึ้นแข็งแกร่ง รันเทรนด์ต่อได้"
        elif price < ema50:
            status, color = "Correction", "orange"
            advice = "🟡 **WAIT:** ราคาย่อตัว หาจังหวะเข้าซื้อเมื่อยืนเหนือแนวรับ"
        else:
            status, color = "Uptrend", "green"
            advice = "🟢 **HOLD:** ถือต่อ แนวโน้มยังเป็นขาขึ้น"
    else:
        if price < ema20 and price < ema50:
            status, color = "Strong Downtrend", "red"
            advice = "🔴 **SELL / AVOID:** ขาลงชัดเจน ห้ามรับมีด"
        elif price > ema20:
            status, color = "Recovery", "orange"
            advice = "🟠 **MONITOR:** พยายามกลับตัว รอเบรค EMA50"
        else:
            status, color = "Downtrend", "red"
            advice = "🔴 **DEFENSIVE:** ตลาดหมี ถือเงินสดปลอดภัยกว่า"
    return status, color, advice

# --- 7. Display ---
if submit_btn:
    st.divider()
    with st.spinner(f"กำลังโหลดกราฟ {symbol_input} ..."):
        df, info = get_data(symbol_input, tf_code)

        if df is not None and not df.empty and len(df) > 200:
            # Calculate Indicators
            df['EMA20'] = ta.ema(df['Close'], length=20)
            df['EMA50'] = ta.ema(df['Close'], length=50)
            df['EMA200'] = ta.ema(df['Close'], length=200)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            
            last = df.iloc[-1]
            price = info['regularMarketPrice'] if info['regularMarketPrice'] else last['Close']
            ema20=last['EMA20']; ema50=last['EMA50']; ema200=last['EMA200']; rsi=last['RSI']
            ai_status, ai_color, ai_advice = analyze_market_structure(price, ema20, ema50, ema200, rsi)

            # Header Info
            st.markdown(f"<h2 style='text-align: center;'>{symbol_input} </h2>", unsafe_allow_html=True)
            
            # Price Banner
            reg_price = info.get('regularMarketPrice')
            reg_chg = info.get('regularMarketChange')
            pct_chg = (reg_chg / (reg_price - reg_chg) * 100) if reg_price and reg_chg else 0
            
            color_text = "#089981" if reg_chg > 0 else "#f23645" # TV Green/Red
            
            st.markdown(f"""
            <div style="text-align:center; margin-bottom: 20px;">
              <span style="font-size:48px; font-weight:bold; color:white;">{reg_price:,.2f}</span>
              <span style="font-size:24px; color:{color_text}; margin-left:10px;">
                {reg_chg:+.2f} ({pct_chg:.2f}%)
              </span>
            </div>
            """, unsafe_allow_html=True)

            # ==================================================
            # 🔥🔥 กราฟ TradingView Style (ใหม่) 🔥🔥
            # ==================================================
            
            # 1. สร้าง Subplots (บน=ราคา, ล่าง=Volume)
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                vertical_spacing=0.03, subplot_titles=('Price', 'Volume'), 
                                row_width=[0.2, 0.7]) # ราคาเอาไป 70%, Volume 20%

            # 2. แท่งเทียน (Candlestick) สีแบบ TradingView เป๊ะๆ
            fig.add_trace(go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                name='Price',
                increasing_line_color='#089981', increasing_fillcolor='#089981', # เขียว TV
                decreasing_line_color='#f23645', decreasing_fillcolor='#f23645'  # แดง TV
            ), row=1, col=1)

            # 3. เส้น EMA (ทำให้เส้นคมๆ)
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA20'], mode='lines', name='EMA 20', line=dict(color='#fbbf24', width=1)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA50'], mode='lines', name='EMA 50', line=dict(color='#2962ff', width=1.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA200'], mode='lines', name='EMA 200', line=dict(color='#d1d4dc', width=2, dash='dot')), row=1, col=1)

            # 4. Volume (สีตามแท่งเทียน: ปิดบวก=เขียว, ปิดลบ=แดง)
            vol_colors = ['#089981' if c >= o else '#f23645' for c, o in zip(df['Close'], df['Open'])]
            fig.add_trace(go.Bar(
                x=df.index, y=df['Volume'], name='Volume', marker_color=vol_colors
            ), row=2, col=1)

            # 5. จัด Layout ให้เหมือนแอป TradingView Dark Mode
            fig.update_layout(
                height=600, # ความสูงกราฟ
                margin=dict(l=10, r=10, t=30, b=10),
                paper_bgcolor='#131722', # สีพื้นหลังเข้มแบบ TV
                plot_bgcolor='#131722',
                font=dict(color='#d1d4dc'), # สีตัวอักษร
                xaxis_rangeslider_visible=False, # ปิดตัวเลื่อนด้านล่าง (เกะกะบนมือถือ)
                dragmode='pan', # โหมดเลื่อนกราฟเป็นหลัก (ใช้นิ้วถูได้เลย)
                showlegend=False, # ซ่อน Legend ไม่ให้รก
                hovermode='x unified' # เส้น Crosshair แนวตั้ง
            )
            
            # ปรับแต่งเส้นตาราง (Grid) ให้จางๆ แบบมือโปร
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#2a2e39')
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#2a2e39')

            # แสดงกราฟ
            st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': False})
            
            # ==================================================

            # AI Status Box
            if ai_color == "green": st.success(f"📈 {ai_status}\n\n{ai_advice}")
            elif ai_color == "red": st.error(f"📉 {ai_status}\n\n{ai_advice}")
            else: st.warning(f"⚖️ {ai_status}\n\n{ai_advice}")

            # Metrics & Analysis Details (เหมือนเดิม)
            c_ema, c_ai = st.columns(2)
            with c_ema:
                st.markdown(f"""
                <div style='background-color: #1e222d; padding: 15px; border-radius: 10px; color: white;'>
                    <h4 style='margin:0'>📉 Key Levels</h4>
                    <p style='color: #fbbf24;'>EMA 20: {ema20:.2f}</p>
                    <p style='color: #2962ff;'>EMA 50: {ema50:.2f}</p>
                    <p style='color: #d1d4dc;'>EMA 200: {ema200:.2f}</p>
                </div>
                """, unsafe_allow_html=True)
            with c_ai:
                st.markdown(f"""
                <div style='background-color: #1e222d; padding: 15px; border-radius: 10px; color: white;'>
                    <h4 style='margin:0'>⚡ Indicators</h4>
                    <p>RSI (14): <b>{rsi:.2f}</b> ({get_rsi_interpretation(rsi)})</p>
                    <p>P/E: {info['trailingPE']}</p>
                </div>
                """, unsafe_allow_html=True)

        elif df is not None: st.warning("⚠️ ข้อมูลไม่พอคำนวณ")
        else: st.error(f"❌ ไม่พบข้อมูล: {symbol_input}")

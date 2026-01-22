import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="AI Expert Trader", page_icon="💎", layout="wide")

st.title("💎 AI ระบบวิเคราะห์หุ้นอัจฉริยะ")

# --- 2. ช่องรับข้อมูล ---
with st.sidebar:
    st.header("⚙️ ตั้งค่าการวิเคราะห์")
    symbol = st.text_input("พิมพ์ชื่อหุ้น (เช่น EOSE, TSLA, NVDA):", value="EOSE").upper()
    timeframe = st.selectbox("เลือก Timeframe:", ["1d", "1wk"], index=0)
    st.caption("แนะนำ: 1d สำหรับเล่นสั้น / 1wk สำหรับถือยาว")
    run_btn = st.button("🚀 วิเคราะห์เลย", type="primary")

# --- 3. เริ่มทำงานเมื่อกดปุ่ม ---
if run_btn:
    with st.spinner(f"กำลังประมวลผลข้อมูล {symbol} ({timeframe})..."):
        try:
            # ใช้ yf.Ticker เพื่อดึงข้อมูลพื้นฐาน (เช่น PE Ratio)
            ticker = yf.Ticker(symbol)
            
            # ดึงข้อมูลกราฟราคา
            period = "max"
            df = ticker.history(period=period, interval=timeframe)

            if len(df) > 0:
                # แก้บั๊กหัวตาราง
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)

                # ดึงข้อมูลพื้นฐาน (Fundamental Data)
                info = ticker.info
                pe_ratio = info.get('trailingPE', 'N/A') # ถ้าไม่มีข้อมูลให้โชว์ N/A
                market_cap = info.get('marketCap', 'N/A')
                long_name = info.get('longName', symbol)

                # คำนวณอินดิเคเตอร์
                df['EMA20']  = ta.ema(df['Close'], length=20)
                df['EMA50']  = ta.ema(df['Close'], length=50)
                df['EMA200'] = ta.ema(df['Close'], length=200)
                df['RSI'] = ta.rsi(df['Close'], length=14)

                # ข้อมูลล่าสุด
                last = df.iloc[-1]
                prev = df.iloc[-2]
                price = last['Close']
                prev_close = prev['Close']
                rsi_val = last['RSI']

                # คำนวณ % Change
                change_val = price - prev_close
                change_pct = (change_val / prev_close) * 100
                
                # สถานะ EMA 200
                ema200_val = last['EMA200']
                
                # ==========================================================
                # 🧠 SMART SUPPORT LOGIC
                # ==========================================================
                supports = []
                trend_status = ""
                
                if price > last['EMA200']:
                    trend_status = "BULLISH (ขาขึ้น)"
                    sup1 = (last['EMA20'], "EMA 20 - แนวรับซิ่ง")
                    sup2 = (last['EMA50'], "EMA 50 - แนวรับหลัก")
                    sup3 = (last['EMA200'], "EMA 200 - แนวรับสุดท้าย")
                    raw_sups = sorted([sup1, sup2, sup3], key=lambda x: x[0], reverse=True)
                    supports = [s for s in raw_sups if s[0] < price]
                else:
                    trend_status = "BEARISH (ขาลง)"
                    recent_low = df['Low'].tail(60).min()
                    year_low = df['Low'].tail(252).min()
                    all_time_low = df['Low'].min()
                    raw_sups = [(recent_low, "Swing Low ล่าสุด"), (year_low, "52-Week Low"), (all_time_low, "All-Time Low")]
                    seen = set()
                    for val, desc in raw_sups:
                        if val < (price * 0.999) and val not in seen:
                            supports.append((val, desc)); seen.add(val)
                    supports = sorted(supports, key=lambda x: x[0], reverse=True)

                res_main = df['High'].tail(60).max()

                # ==========================================================
                # 📊 แสดงผล Dashboard
                # ==========================================================
                
                # --- ชื่อหุ้นและสถานะ ---
                st.header(f"🏢 {long_name} ({symbol})")
                
                # 1. Key Metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("ราคาล่าสุด", f"{price:.2f}", f"{change_val:.2f} ({change_pct:.2f}%)")
                with col2:
                    # แสดงค่า RSI พร้อมสีบอกสถานะ
                    rsi_color = "normal"
                    if rsi_val > 70: rsi_status = "Overbought (แพงไป)"; rsi_color = "off"
                    elif rsi_val < 30: rsi_status = "Oversold (ถูกไป)"; rsi_color = "normal"
                    else: rsi_status = "Neutral (ปกติ)"
                    st.metric("RSI (14)", f"{rsi_val:.2f}", delta=rsi_status, delta_color=rsi_color)
                with col3:
                    # แสดงค่า P/E Ratio
                    pe_display = f"{pe_ratio:.2f}" if isinstance(pe_ratio, (int, float)) else pe_ratio
                    st.metric("P/E Ratio", pe_display)
                with col4:
                    if price > last['EMA200']: st.success(f"📈 {trend_status}")
                    else: st.error(f"📉 {trend_status}")

                st.divider()

                # 2. Support & Resistance Section
                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("🚧 แนวต้าน (Resistance)")
                    st.markdown(f"🔴 **{res_main:.2f}** (High เดิม)")
                    if price < last['EMA200']: st.markdown(f"🔴 **{last['EMA200']:.2f}** (เส้น EMA 200)")
                with c2:
                    st.subheader("🟢 แนวรับ (Smart Support)")
                    if supports:
                        for val, desc in supports[:3]: st.markdown(f"✅ **{val:.2f}** _{desc}_")
                    else: st.warning("⚠️ **ไร้แนวรับ (New Low)**")

                st.divider()

                # 3. AI Intelligent Report
                st.subheader("🤖 AI Intelligent Report")
                
                # Technical Analysis
                st.markdown("##### 🧠 1. บทวิเคราะห์ทางเทคนิค")
                if price > last['EMA200']:
                    if price < last['EMA50']: st.info("หุ้นเป็นขาขึ้นแต่พักตัวลึก (Correction) ราคากำลังทดสอบแนวรับสำคัญ")
                    else: st.success("กระทิงดุ (Strong Bull) โมเมนตัมแข็งแกร่งมาก")
                else:
                    if last['RSI'] < 30: st.warning("ขาลงเต็มตัว แต่ Oversold มาก (ลุ้นเด้งสั้นๆ)")
                    else: st.error("ขาลงสมบูรณ์แบบ (Bear Market) แรงขายยังกดดันต่อเนื่อง")

                # RSI Explanation (New!)
                with st.expander("ℹ️ อ่านค่า RSI อย่างไรให้แม่นยำ?"):
                    st.markdown("""
                    **Relative Strength Index (RSI)** คือดัชนีวัดความแข็งแกร่งของราคา:
                    * 🔴 **RSI > 70 (Overbought):** ราคาขึ้นมาแรงเกินไป มีโอกาสสูงที่จะ **'ย่อตัว'** หรือ **'พักฐาน'** (ระวังการไล่ราคา)
                    * 🟢 **RSI < 30 (Oversold):** ราคาลงมาแรงเกินไป มีโอกาสสูงที่จะ **'เด้งกลับ'** (Rebound) (เป็นจังหวะจับตามอง)
                    * 🔵 **RSI 30-70:** ราคาเคลื่อนไหวในเกณฑ์ปกติ
                        * *RSI > 50:* โมเมนตัมฝั่งซื้อได้เปรียบ
                        * *RSI < 50:* โมเมนตัมฝั่งขายได้เปรียบ
                    """)

                # Action Plan
                st.markdown("##### ✅ 2. สรุปสิ่งที่ควรทำ (Action Plan)")
                if price > last['EMA200']:
                    if price < last['EMA50']: st.write("🟢 **Buy on Dip:** ทยอยสะสมไม้แรกที่แนวรับ EMA")
                    else: st.write("🟡 **Let Profit Run:** ถือต่อ ใช้ EMA 20 บังทุน")
                else:
                    if last['RSI'] < 30: st.write(f"⚡ **Sniper Bounce:** รอซื้อเล่นเด้งที่ {supports[0][0] if supports else 'Low เดิม'}")
                    elif price < last['EMA20']: st.write("⛔ **Wait & See:** นั่งทับมือ! รอให้ยืนเหนือ EMA 20 ให้ได้ก่อน")
                    else: st.write("🟠 **Sell on Rise:** เด้งเพื่อขายลดพอร์ต")

            else:
                st.error(f"❌ ไม่พบข้อมูลหุ้น {symbol} กรุณาตรวจสอบชื่อหุ้น")
        
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {e}")


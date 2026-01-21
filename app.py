import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="AI Expert Trader", page_icon="💎", layout="wide")

st.title("💎 AI Expert Trader: ระบบวิเคราะห์หุ้นอัจฉริยะ")
st.markdown("**(Smart Logic: Strict Support & Resistance Filter)**")

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
            # ดึงข้อมูล
            period = "max"
            df = yf.download(symbol, period=period, interval=timeframe, progress=False)

            if len(df) > 0:
                # แก้บั๊กหัวตาราง
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)

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

                # คำนวณ % Change
                change_val = price - prev_close
                change_pct = (change_val / prev_close) * 100
                
                # สถานะ EMA 200
                ema200_val = last['EMA200']
                diff_ema200_pct = ((price - ema200_val) / ema200_val) * 100
                
                # ==========================================================
                # 🧠 SMART SUPPORT LOGIC (Logic เดียวกับที่คุณชอบ)
                # ==========================================================
                supports = []
                trend_status = ""
                
                if price > last['EMA200']:
                    # 🟢 ขาขึ้น: ใช้ EMA เป็นแนวรับ
                    trend_status = "BULLISH (ขาขึ้น)"
                    trend_color = "green"
                    
                    sup1 = (last['EMA20'], "EMA 20 - แนวรับซิ่ง")
                    sup2 = (last['EMA50'], "EMA 50 - แนวรับหลัก")
                    sup3 = (last['EMA200'], "EMA 200 - แนวรับสุดท้าย")
                    
                    # เรียงลำดับ
                    raw_sups = sorted([sup1, sup2, sup3], key=lambda x: x[0], reverse=True)
                    # กรองเฉพาะที่ต่ำกว่าราคาปัจจุบัน
                    supports = [s for s in raw_sups if s[0] < price]

                else:
                    # 🔴 ขาลง: ใช้ฐานราคาเดิม (Low) เท่านั้น
                    trend_status = "BEARISH (ขาลง)"
                    trend_color = "red"
                    
                    recent_low = df['Low'].tail(60).min()
                    year_low = df['Low'].tail(252).min()
                    all_time_low = df['Low'].min()
                    
                    raw_sups = [
                        (recent_low, "Swing Low ล่าสุด"),
                        (year_low, "52-Week Low"),
                        (all_time_low, "All-Time Low")
                    ]
                    
                    # กรองเข้มงวด: ต้องต่ำกว่าราคาปัจจุบัน
                    seen = set()
                    for val, desc in raw_sups:
                        if val < (price * 0.999) and val not in seen:
                            supports.append((val, desc))
                            seen.add(val)
                    
                    supports = sorted(supports, key=lambda x: x[0], reverse=True)

                res_main = df['High'].tail(60).max()

                # ==========================================================
                # 📊 แสดงผล Dashboard (Streamlit UI)
                # ==========================================================
                
                # 1. Header Metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("ราคาล่าสุด", f"{price:.2f}", f"{change_val:.2f} ({change_pct:.2f}%)")
                with col2:
                    st.metric("RSI (14)", f"{last['RSI']:.2f}")
                with col3:
                    if price > last['EMA200']:
                        st.success(f"📈 {trend_status}")
                    else:
                        st.error(f"📉 {trend_status}")

                st.divider()

                # 2. Support & Resistance Section
                c1, c2 = st.columns(2)
                
                with c1:
                    st.subheader("🚧 แนวต้าน (Resistance)")
                    st.markdown(f"🔴 **{res_main:.2f}** (High เดิม)")
                    if price < last['EMA200']:
                        st.markdown(f"🔴 **{last['EMA200']:.2f}** (เส้น EMA 200)")
                
                with c2:
                    st.subheader("🟢 แนวรับ (Smart Support)")
                    if supports:
                        for val, desc in supports[:3]:
                            st.markdown(f"✅ **{val:.2f}** _{desc}_")
                    else:
                        st.warning("⚠️ **ไร้แนวรับ (New Low)**: ราคาหลุดทุกฐานในอดีต")

                st.divider()

                # 3. AI Intelligent Report
                st.subheader("🤖 AI Intelligent Report")
                
                # Technical Analysis
                st.markdown("##### 🧠 1. บทวิเคราะห์ทางเทคนิค")
                if price > last['EMA200']:
                    if price < last['EMA50']:
                        st.info("หุ้นเป็นขาขึ้นแต่พักตัวลึก (Correction) ราคากำลังทดสอบแนวรับสำคัญ")
                    else:
                        st.success("กระทิงดุ (Strong Bull) โมเมนตัมแข็งแกร่งมาก")
                else:
                    if last['RSI'] < 30:
                        st.warning("ขาลงเต็มตัว แต่ Oversold มาก (ลุ้นเด้งสั้นๆ)")
                    else:
                        st.error("ขาลงสมบูรณ์แบบ (Bear Market) แรงขายยังกดดันต่อเนื่อง")

                # Action Plan
                st.markdown("##### ✅ 2. สรุปสิ่งที่ควรทำ (Action Plan)")
                if price > last['EMA200']:
                    if price < last['EMA50']:
                        st.write("🟢 **Buy on Dip:** ทยอยสะสมไม้แรกที่แนวรับ EMA")
                    else:
                        st.write("🟡 **Let Profit Run:** ถือต่อ ใช้ EMA 20 บังทุน")
                else:
                    if last['RSI'] < 30:
                        st.write(f"⚡ **Sniper Bounce:** รอซื้อเล่นเด้งที่ {supports[0][0] if supports else 'Low เดิม'} (Stop Loss เคร่งครัด)")
                    elif price < last['EMA20']:
                        st.write("⛔ **Wait & See:** นั่งทับมือ! รอให้ยืนเหนือ EMA 20 ให้ได้ก่อน")
                    else:
                        st.write("🟠 **Sell on Rise:** เด้งเพื่อขายลดพอร์ต")

            else:
                st.error(f"❌ ไม่พบข้อมูลหุ้น {symbol} กรุณาตรวจสอบชื่อหุ้น")
        
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {e}")

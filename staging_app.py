import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import datetime, timedelta
import pytz
from streamlit_autorefresh import st_autorefresh

# --- 1. CRM STYLE & CONFIG ---
st.set_page_config(page_title="Gamerarena CRM (Staging)", page_icon="🎮", layout="wide")
st_autorefresh(interval=60000, limit=None, key="crm_refresh")

st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }
    .stButton>button { background: #4F46E5; color: white; border-radius: 6px; width: 100%; font-weight: 600; border: none; transition: 0.2s; }
    .stButton>button:hover { background: #4338CA; box-shadow: 0 4px 6px rgba(0,0,0,0.2); transform: translateY(-1px); }
    .crm-card { background-color: #1E1E2D; padding: 20px; border-radius: 8px; border-left: 4px solid #4F46E5; margin-bottom: 12px; }
    .warning-card { background-color: #2D1E1E; padding: 20px; border-radius: 8px; border-left: 4px solid #EF4444; margin-bottom: 12px; animation: pulse 2s infinite; }
    .overdue-card { background-color: #2D1E1E; padding: 20px; border-radius: 8px; border-left: 4px solid #B91C1C; margin-bottom: 12px; border: 1px solid #EF4444; }
    .cal-box { background-color: #2B2B40; padding: 15px 5px; border-radius: 8px; text-align: center; border-top: 3px solid #10B981; }
    .metric-box { background-color: #1E1E2D; padding: 20px; border-radius: 8px; text-align: center; border: 1px solid #2B2B40; }
    @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); } 70% { box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); } 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); } }
</style>
""", unsafe_allow_html=True)

# --- 2. STATE MANAGEMENT & AUTH ---
if "auth" not in st.session_state: st.session_state.auth = False
if "cart" not in st.session_state: st.session_state.cart = []

if not st.session_state.auth:
    st.title("🔒 Staging CRM Login")
    pwd = st.text_input("Enter Staff Passcode", type="password")
    if st.button("Login"):
        if pwd == "Admin@2026":
            st.session_state.auth = True; st.rerun()
        else: st.error("❌ Invalid Passcode")
    st.stop()

# --- 3. DATABASE ---
try: conn = st.connection("supabase", type=SupabaseConnection)
except: st.error("Database Connection Error."); st.stop()

IST = pytz.timezone('Asia/Kolkata')
SYSTEMS = {"PS1":"PS5", "PS2":"PS5", "PS3":"PS5", "PC1":"PC", "PC2":"PC", "SIM1":"Racing Sim"}
PRICES_1H = {"PC": 100, "PS5": 150, "Racing Sim": 250}
PRICES_30M = {"PC": 70, "PS5": 100, "Racing Sim": 150}

def get_price(cat, dur, extra=0):
    cost = int(dur) * PRICES_1H.get(cat, 0)
    if (dur % 1) != 0: cost += PRICES_30M.get(cat, 0)
    if "PS5" in cat: cost += (extra * 100)
    return cost

# --- 4. TABS ---
t1, t2, t3, t4, t5 = st.tabs(["🕹️ Active Floor", "📝 Bookings & Cart", "📊 Daily Summary", "📅 Reports", "🧠 Vault"])

# --- TAB 1: ACTIVE FLOOR & ARRIVALS ---
with t1:
    col_floor, col_queue = st.columns([2, 1], gap="large")
    
    with col_floor:
        st.subheader("🕹️ Live Timers")
        try:
            res = conn.table("sales_staging").select("*").eq("status", "Active").execute()
            active_df = pd.DataFrame(res.data)
            if not active_df.empty:
                now_ist = datetime.now(IST)
                for _, row in active_df.iterrows():
                    try:
                        entry_dt = pd.to_datetime(f"{row['date'][:10]} {row['entry_time']}").tz_localize(IST)
                        time_left = ((entry_dt + timedelta(hours=row['duration'])) - now_ist).total_seconds() / 60.0
                    except: time_left = 999 

                    if time_left < 0: cc, txt = "overdue-card", f"🚨 OVERDUE ({abs(int(time_left))}m)"
                    elif time_left <= 5: cc, txt = "warning-card", f"⚠️ {int(time_left)}m REMAINING"
                    else: cc, txt = "crm-card", f"⏳ {int(time_left)}m remaining"

                    st.markdown(f"<div class='{cc}'><h4 style='margin:0;color:#E0E7FF;'>{row['system']} | {row['customer']}</h4><p style='margin:5px 0 0 0;color:#9CA3AF;'>In: {row['entry_time']} | {row['duration']} Hrs | ₹{row['total']}<br><b style='color:#FCD34D;'>{txt}</b></p></div>", unsafe_allow_html=True)
                
                st.write("### Manage Floor")
                active_df['lbl'] = active_df['customer'] + " | " + active_df['system']
                sel = st.selectbox("Select Player", active_df['lbl'].tolist(), label_visibility="collapsed")
                row = active_df[active_df['lbl'] == sel].iloc[0]
                
                ca, cb = st.columns(2)
                with ca:
                    ext = st.number_input("Add Hrs", 0.5, 5.0, 0.5)
                    if st.button("➕ Extend"):
                        conn.table("sales_staging").update({"total": row['total'] + get_price(SYSTEMS[row['system']], ext, 0), "duration": row['duration'] + ext}).eq("id", row['id']).execute()
                        st.rerun()
                with cb:
                    pay = st.radio("Pay", ["Cash", "UPI"], horizontal=True, label_visibility="collapsed")
                    if st.button("🛑 Collect & Close"):
                        conn.table("sales_staging").update({"status": "Completed", "method": pay}).eq("id", row['id']).execute()
                        st.balloons(); st.rerun()
            else: st.info("Floor is clear.")
        except: st.write("Loading floor...")

    with col_queue:
        st.subheader("📥 Expected Today")
        try:
            today_str = datetime.now(IST).strftime('%Y-%m-%d')
            q_res = conn.table("sales_staging").select("*").eq("status", "Booked").eq("scheduled_date", today_str).execute()
            q_df = pd.DataFrame(q_res.data)
            if not q_df.empty:
                for _, q in q_df.iterrows():
                    st.markdown(f"<div style='background:#2B2B40; padding:15px; border-radius:8px; margin-bottom:10px;'><b>{q['entry_time']}</b><br>{q['customer']} ({q['system']})<br>{q['duration']} Hrs</div>", unsafe_allow_html=True)
                    if st.button(f"Check-In {q['system']}", key=f"chk_{q['id']}"):
                        now_time = datetime.now(IST).strftime("%I:%M %p")
                        conn.table("sales_staging").update({"status": "Active", "entry_time": now_time}).eq("id", q['id']).execute()
                        st.success("Checked In!"); st.rerun()
            else: st.info("No bookings pending.")
        except: st.write("Loading queue...")

# --- TAB 2: BOOKINGS, CART & SCHEDULE ---
with t2:
    st.subheader("📅 7-Day Pipeline Overview")
    try:
        b_res = conn.table("sales_staging").select("scheduled_date").eq("status", "Booked").execute()
        b_df = pd.DataFrame(b_res.data)
        cal_cols = st.columns(7)
        for i in range(7):
            target_date = datetime.now(IST).date() + timedelta(days=i)
            count = len(b_df[b_df['scheduled_date'] == target_date.strftime('%Y-%m-%d')]) if not b_df.empty else 0
            day_name = "Today" if i == 0 else target_date.strftime('%a %d')
            color = "#10B981" if count > 0 else "#4B5563"
            cal_cols[i].markdown(f"<div class='cal-box' style='border-color:{color};'><b>{day_name}</b><br><h3 style='margin:0;'>{count}</h3></div>", unsafe_allow_html=True)
    except: st.write("Pipeline loading...")
    
    st.divider()
    
    # NEW CLEAN LAYOUT
    col_form, col_cart = st.columns([1.2, 1], gap="large")
    
    with col_form:
        st.subheader("1. Lead & Booking Details")
        with st.container(border=True):
            name = st.text_input("Gamer / Group Name")
            phone = st.text_input("Phone Number (Optional)")
            st.write("---")
            entry_type = st.radio("Booking Type", ["🏃‍♂️ Walk-in (Play Now)", "📅 Advance Booking"], horizontal=True)
            
            h, m, ap = st.columns(3)
            now = datetime.now(IST)
            
            if "Walk-in" in entry_type:
                sch_date = now.strftime('%Y-%m-%d')
                sh = h.selectbox("HH", [f"{i:02d}" for i in range(1, 13)], index=int(now.strftime("%I"))-1)
                sm = m.selectbox("MM", [f"{i:02d}" for i in range(60)], index=int(now.strftime("%M")))
                sa = ap.selectbox("AM/PM", ["AM", "PM"], index=0 if now.strftime("%p")=="AM" else 1)
                final_status = "Active"
                btn_txt = "🚀 Start Session Now"
            else:
                sch_date_obj = st.date_input("Select Booking Date", now.date(), min_value=now.date())
                sch_date = sch_date_obj.strftime('%Y-%m-%d')
                sh = h.selectbox("HH", [f"{i:02d}" for i in range(1, 13)])
                sm = m.selectbox("MM", [f"{i:02d}" for i in range(60)])
                sa = ap.selectbox("AM/PM", ["AM", "PM"])
                final_status = "Booked"
                btn_txt = f"📅 Confirm Reservation for {sch_date}"

        st.subheader("2. Add Hardware to Cart")
        with st.container(border=True):
            sys_col, dur_col, ctrl_col = st.columns([2, 1, 1])
            sel_sys = sys_col.selectbox("Hardware", list(SYSTEMS.keys()))
            dur = dur_col.number_input("Hours", 0.5, 12.0, 1.0, 0.5)
            ctrl = ctrl_col.number_input("Extra Ctrl", 0, 3, 0) if "PS" in sel_sys else 0
            
            if st.button("➕ Add to Group Cart", use_container_width=True):
                st.session_state.cart.append({
                    "system": sel_sys, "duration": dur, "ctrl": ctrl, 
                    "price": get_price(SYSTEMS[sel_sys], dur, ctrl)
                })
                st.rerun()

    with col_cart:
        st.subheader("🛒 Current Cart")
        with st.container(border=True):
            if st.session_state.cart:
                cart_df = pd.DataFrame(st.session_state.cart)
                st.dataframe(cart_df[['system', 'duration', 'price']], hide_index=True, use_container_width=True)
                st.markdown(f"### Total: ₹{cart_df['price'].sum()}")
                
                if st.button(btn_txt, type="primary", use_container_width=True):
                    if not name: st.error("Please provide a Name first.")
                    else:
                        try:
                            for item in st.session_state.cart:
                                conn.table("sales_staging").insert({
                                    "customer": name, "phone": phone, "system": item['system'], "duration": item['duration'], 
                                    "total": item['price'], "method": "Pending", 
                                    "entry_time": f"{sh}:{sm} {sa}", "status": final_status, "scheduled_date": sch_date
                                }).execute()
                            st.session_state.cart = []
                            st.success("Processed successfully!")
                            st.rerun()
                        except Exception as e: st.error(f"Error: {e}")
                
                if st.button("🗑️ Clear Cart", use_container_width=True):
                    st.session_state.cart = []
                    st.rerun()
            else:
                st.info("Cart is empty. Add hardware from the left.")
        
        # NEW: Show existing bookings for the selected date!
        st.subheader(f"📅 Daily Schedule View")
        try:
            day_res = conn.table("sales_staging").select("customer, system, entry_time, duration").eq("status", "Booked").eq("scheduled_date", sch_date).execute()
            day_df = pd.DataFrame(day_res.data)
            if not day_df.empty:
                st.caption(f"Existing bookings for {sch_date}:")
                st.dataframe(day_df, hide_index=True, use_container_width=True)
            else:
                st.caption(f"No advance bookings exist for {sch_date} yet. The floor is open!")
        except: st.caption("Select a date to see schedule.")

# --- TAB 3: DAILY SUMMARY ---
with t3:
    st.subheader("📊 Today's Snapshot")
    try:
        raw = conn.table("sales_staging").select("*").execute()
        df = pd.DataFrame(raw.data)
        if not df.empty:
            df['date_str'] = df['date'].str[:10] 
            today_str = datetime.now(IST).strftime('%Y-%m-%d')
            t_df = df[df['date_str'] == today_str]
            comp = t_df[t_df['status'] == 'Completed']
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Cash Collected", f"₹{comp[comp['method']=='Cash']['total'].sum():,.0f}")
            m2.metric("UPI Collected", f"₹{comp[comp['method']!='Cash']['total'].sum():,.0f}")
            m3.metric("Total Revenue", f"₹{comp['total'].sum():,.0f}")
            m4.metric("Pending on Floor", f"₹{t_df[t_df['status']=='Active']['total'].sum():,.0f}")
            st.dataframe(t_df.sort_values('date', ascending=False), use_container_width=True, hide_index=True)
        else: st.info("No data in staging yet.")
    except Exception as e: st.error(f"Error loading summary: {e}")

# --- TAB 4: REPORTS ---
with t4:
    st.subheader("📅 Deep Filter Reports")
    d_range = st.date_input("Date Range", [datetime.now(IST).date(), datetime.now(IST).date()])
    try:
        if len(d_range) == 2:
            s_dt, e_dt = [d.strftime('%Y-%m-%d') for d in d_range]
            raw_e = conn.table("sales_staging").select("*").execute()
            edf = pd.DataFrame(raw_e.data)
            if not edf.empty:
                edf['date_str'] = edf['date'].str[:10]
                f_edf = edf[(edf['date_str'] >= s_dt) & (edf['date_str'] <= e_dt)]
                if not f_edf.empty:
                    st.download_button("📥 Export Range", f_edf.to_csv(index=False).encode('utf-8'), f"Export_{s_dt}_to_{e_dt}.csv", "text/csv")
                    st.dataframe(f_edf, hide_index=True)
                else: st.warning("No records.")
    except: st.info("Select valid dates.")

# --- TAB 5: VAULT ---
with t5:
    st.subheader("🔐 Intelligence Vault")
    if st.text_input("Master Key", type="password") == "Shreenad@0511":
        try:
            raw_v = conn.table("sales_staging").select("*").execute()
            vdf = pd.DataFrame(raw_v.data)
            if not vdf.empty:
                vdf['date_str'] = vdf['date'].str[:10]
                pdf = vdf[vdf['status'] == 'Completed'].copy()
                now = datetime.now(IST)
                s_tw = (now - timedelta(days=now.weekday())).strftime('%Y-%m-%d')
                s_tm = now.replace(day=1).strftime('%Y-%m-%d')
                c1, c2 = st.columns(2)
                c1.markdown(f"<div class='metric-box'><h4>WTD Revenue</h4><h2 style='color:#34D399;'>₹{pdf[pdf['date_str'] >= s_tw]['total'].sum():,.0f}</h2></div>", unsafe_allow_html=True)
                c2.markdown(f"<div class='metric-box'><h4>MTD Revenue</h4><h2 style='color:#34D399;'>₹{pdf[pdf['date_str'] >= s_tm]['total'].sum():,.0f}</h2></div>", unsafe_allow_html=True)
                st.divider()
                h_map = {"PC1":"PC","PC2":"PC","PS1":"Playstation 5","PS2":"Playstation 5","PS3":"Playstation 5","SIM1":"Racing Simulator"}
                pdf['Hardware'] = pdf['system'].map(h_map).fillna(pdf['system'])
                st.bar_chart(pdf.groupby('Hardware')['total'].sum(), color="#4F46E5")
            else: st.warning("No completed data found.")
        except Exception as e: st.error(f"Vault processing error: {e}")

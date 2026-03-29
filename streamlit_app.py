import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import datetime, timedelta
import pytz
from streamlit_autorefresh import st_autorefresh

# --- 1. CRM STYLE & CONFIG ---
st.set_page_config(page_title="Gamerarena CRM", page_icon="🎮", layout="wide")
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
IST = pytz.timezone('Asia/Kolkata')
now_ist = datetime.now(IST)

if "auth" not in st.session_state: st.session_state.auth = False
if "cart" not in st.session_state: st.session_state.cart = []

if "f_name" not in st.session_state: st.session_state.f_name = ""
if "f_phone" not in st.session_state: st.session_state.f_phone = ""
if "b_type" not in st.session_state: st.session_state.b_type = "🏃‍♂️ Walk-in (Play Now)"
if "b_date" not in st.session_state: st.session_state.b_date = now_ist.date()
if "b_time" not in st.session_state: st.session_state.b_time = now_ist.time()

if not st.session_state.auth:
    st.title("🔒 Gamerarena Central Login")
    pwd = st.text_input("Enter Staff Passcode", type="password")
    if st.button("Login"):
        if pwd == "Admin@2026":
            st.session_state.auth = True; st.rerun()
        else: st.error("❌ Invalid Passcode")
    st.stop()

# --- 3. DATABASE & PRICING ---
try: conn = st.connection("supabase", type=SupabaseConnection)
except: st.error("Database Connection Error."); st.stop()

SYSTEMS = {"PS1":"PS5", "PS2":"PS5", "PS3":"PS5", "PC1":"PC", "PC2":"PC", "SIM1":"Racing Sim"}

def get_price(cat, dur, extra=0):
    if cat == "PS5":
        rate_1h = 150 + (extra * 100)
        rate_30m = 100 + (extra * 100)
    elif cat == "PC":
        rate_1h = 100
        rate_30m = 70
    elif cat == "Racing Sim":
        rate_1h = 250
        rate_30m = 150
    else:
        rate_1h = 0; rate_30m = 0
        
    full_hrs = int(dur)
    half_hr = 1 if (dur % 1) != 0 else 0
    return (full_hrs * rate_1h) + (half_hr * rate_30m)

# --- 4. TABS ---
t1, t2, t3, t4, t5 = st.tabs(["🕹️ Active Floor", "📝 Bookings & Cart", "📊 Daily Summary", "📅 Reports", "🧠 Vault"])

# --- TAB 1: ACTIVE FLOOR & ARRIVALS ---
with t1:
    col_floor, col_queue = st.columns([2, 1], gap="large")
    with col_floor:
        st.subheader("🕹️ Live Timers")
        try:
            res = conn.table("sales").select("*").eq("status", "Active").execute()
            active_df = pd.DataFrame(res.data)
            if not active_df.empty:
                for _, row in active_df.iterrows():
                    try:
                        entry_dt = pd.to_datetime(f"{row['date'][:10]} {row['entry_time']}").tz_localize(IST)
                        time_left = ((entry_dt + timedelta(hours=row['duration'])) - datetime.now(IST)).total_seconds() / 60.0
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
                    st.markdown("**⏳ Add More Time**")
                    ext = st.number_input("Extra Hrs", 0.5, 5.0, 0.5)
                    if st.button("➕ Extend Session", use_container_width=True):
                        conn.table("sales").update({"total": row['total'] + get_price(SYSTEMS[row['system']], ext, 0), "duration": row['duration'] + ext}).eq("id", row['id']).execute()
                        st.rerun()
                with cb:
                    st.markdown("**💳 Smart Checkout**")
                    try:
                        entry_dt = pd.to_datetime(f"{row['date'][:10]} {row['entry_time']}").tz_localize(IST)
                        played_mins = int((datetime.now(IST) - entry_dt).total_seconds() / 60.0)
                    except: played_mins = 0
                    
                    st.caption(f"⏱️ Actual Time Played: **{played_mins} mins**")
                    
                    # 40-Minute Rule Logic
                    rec_dur = float(row['duration'])
                    if played_mins <= 40 and row['duration'] >= 1.0: 
                        rec_dur = 0.5
                    elif played_mins > 40 and played_mins <= 60 and row['duration'] > 1.0: 
                        rec_dur = 1.0
                    
                    chk_1, chk_2 = st.columns(2)
                    f_dur = chk_1.number_input("Billed Hrs", 0.5, 12.0, rec_dur, 0.5)
                    f_total = chk_2.number_input("Final Bill (₹)", 0, 10000, int(row['total']), 10)
                    
                    pay = st.radio("Pay Method", ["Cash", "UPI"], horizontal=True, label_visibility="collapsed")
                    if st.button("🛑 Confirm & Close", type="primary", use_container_width=True):
                        conn.table("sales").update({"status": "Completed", "method": pay, "duration": f_dur, "total": f_total}).eq("id", row['id']).execute()
                        st.balloons(); st.rerun()
            else: st.info("Floor is clear.")
        except: st.write("Loading floor...")

    with col_queue:
        st.subheader("📥 Expected Today")
        try:
            today_str = datetime.now(IST).strftime('%Y-%m-%d')
            q_res = conn.table("sales").select("*").eq("status", "Booked").eq("scheduled_date", today_str).execute()
            q_df = pd.DataFrame(q_res.data)
            if not q_df.empty:
                for _, q in q_df.iterrows():
                    st.markdown(f"<div style='background:#2B2B40; padding:15px; border-radius:8px; margin-bottom:10px;'><b>{q['entry_time']}</b><br>{q['customer']} ({q['system']})<br>{q['duration']} Hrs</div>", unsafe_allow_html=True)
                    if st.button(f"Check-In {q['system']}", key=f"chk_{q['id']}"):
                        now_time = datetime.now(IST).strftime("%I:%M %p")
                        conn.table("sales").update({"status": "Active", "entry_time": now_time}).eq("id", q['id']).execute()
                        st.success("Checked In!"); st.rerun()
            else: st.info("No bookings pending.")
        except: st.write("Loading queue...")

# --- TAB 2: BOOKINGS, CART & SCHEDULE ---
with t2:
    col_form, col_cart = st.columns([1.2, 1], gap="large")
    
    with col_form:
        st.subheader("1. Lead & Booking Details")
        with st.container(border=True):
            name = st.text_input("Gamer / Group Name", key="f_name")
            phone = st.text_input("Phone Number (Optional)", key="f_phone")
            st.write("---")
            
            st.session_state.b_type = st.radio("Booking Type", ["🏃‍♂️ Walk-in (Play Now)", "📅 Advance Booking"], horizontal=True, index=0 if "Walk-in" in st.session_state.b_type else 1)
            
            if "Walk-in" in st.session_state.b_type:
                sch_date = datetime.now(IST).strftime('%Y-%m-%d')
                st.session_state.b_time = st.time_input("Entry Time (HH:MM)", value=st.session_state.b_time, step=60)
                time_str = st.session_state.b_time.strftime("%I:%M %p")
                final_status = "Active"
                btn_txt = "🚀 Start Session Now"
            else:
                st.session_state.b_date = st.date_input("Select Future Date", value=st.session_state.b_date, min_value=datetime.now(IST).date())
                sch_date = st.session_state.b_date.strftime('%Y-%m-%d')
                st.session_state.b_time = st.time_input("Booking Time (HH:MM)", value=st.session_state.b_time, step=60)
                time_str = st.session_state.b_time.strftime("%I:%M %p")
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
                for i, item in enumerate(st.session_state.cart):
                    c_info, c_price, c_del = st.columns([3, 1.5, 1])
                    c_info.write(f"🎮 **{item['system']}** ({item['duration']}h)")
                    c_price.write(f"₹{item['price']}")
                    if c_del.button("❌", key=f"del_{i}"):
                        st.session_state.cart.pop(i)
                        st.rerun()
                
                st.divider()
                total_val = sum(item['price'] for item in st.session_state.cart)
                st.markdown(f"### Total: ₹{total_val}")
                
                if st.button(btn_txt, type="primary", use_container_width=True):
                    if not st.session_state.f_name: 
                        st.error("Please provide a Name first.")
                    else:
                        try:
                            conflict = False
                            conflict_msg = ""
                            res = conn.table("sales").select("system, entry_time, duration").eq("scheduled_date", sch_date).in_("status", ["Active", "Booked"]).execute()
                            db_df = pd.DataFrame(res.data)

                            if not db_df.empty:
                                for item in st.session_state.cart:
                                    sys_df = db_df[db_df['system'] == item['system']]
                                    if not sys_df.empty:
                                        new_start = datetime.strptime(f"{sch_date} {time_str}", "%Y-%m-%d %I:%M %p")
                                        new_end = new_start + timedelta(hours=item['duration'])
                                        for _, row in sys_df.iterrows():
                                            db_start = datetime.strptime(f"{sch_date} {row['entry_time']}", "%Y-%m-%d %I:%M %p")
                                            db_end = db_start + timedelta(hours=row['duration'])
                                            
                                            if new_start < db_end and new_end > db_start:
                                                conflict = True
                                                conflict_msg = f"⚠️ Double Booking! {item['system']} is already reserved from {row['entry_time']} for {row['duration']}h."
                                                break
                                    if conflict: break

                            if conflict: st.error(conflict_msg)
                            else:
                                for item in st.session_state.cart:
                                    conn.table("sales").insert({
                                        "customer": st.session_state.f_name, "phone": st.session_state.f_phone, "system": item['system'], "duration": item['duration'], 
                                        "total": item['price'], "method": "Pending", 
                                        "entry_time": time_str, "status": final_status, "scheduled_date": sch_date
                                    }).execute()
                                
                                st.session_state.cart = []
                                st.session_state.f_name = ""
                                st.session_state.f_phone = ""
                                st.session_state.b_type = "🏃‍♂️ Walk-in (Play Now)"
                                st.session_state.b_date = datetime.now(IST).date()
                                st.session_state.b_time = datetime.now(IST).time()
                                st.success("Processed successfully!")
                                st.rerun()
                        except Exception as e: st.error(f"Error: {e}")
            else: st.info("Cart is empty.")
        
        st.subheader(f"📅 All Upcoming Bookings")
        try:
            today_str_cal = datetime.now(IST).strftime('%Y-%m-%d')
            up_res = conn.table("sales").select("id, scheduled_date, entry_time, customer, system, duration").eq("status", "Booked").gte("scheduled_date", today_str_cal).execute()
            up_df = pd.DataFrame(up_res.data)
            
            if not up_df.empty:
                display_df = up_df.copy()
                display_df = display_df.sort_values(by=["scheduled_date", "entry_time"])
                display_df.rename(columns={"scheduled_date": "Date", "entry_time": "Time", "customer": "Name", "system": "System", "duration": "Hrs"}, inplace=True)
                st.dataframe(display_df[['Date', 'Time', 'Name', 'System', 'Hrs']], hide_index=True, use_container_width=True)
                
                st.write("---")
                st.write("✏️ **Edit or Cancel a Booking**")
                up_df['lbl'] = up_df['scheduled_date'] + " " + up_df['entry_time'] + " | " + up_df['customer'] + " (" + up_df['system'] + ")"
                sel_edit = st.selectbox("Select Booking", up_df['lbl'].tolist(), label_visibility="collapsed")
                e_row = up_df[up_df['lbl'] == sel_edit].iloc[0]
                
                with st.container(border=True):
                    e_c1, e_c2, e_c3 = st.columns(3)
                    new_date = e_c1.date_input("New Date", datetime.strptime(e_row['scheduled_date'], '%Y-%m-%d').date(), key="e_date")
                    
                    try: e_time_obj = datetime.strptime(e_row['entry_time'], "%I:%M %p").time()
                    except: e_time_obj = datetime.now(IST).time()
                    new_time = e_c2.time_input("New Time", value=e_time_obj, step=60, key="e_time")
                    
                    sys_idx = list(SYSTEMS.keys()).index(e_row['system']) if e_row['system'] in SYSTEMS else 0
                    new_sys = e_c3.selectbox("System", list(SYSTEMS.keys()), index=sys_idx, key="e_sys")
                    
                    new_dur = e_c1.number_input("Hrs", 0.5, 12.0, float(e_row['duration']), 0.5, key="e_dur")
                    new_name = e_c2.text_input("Name", e_row['customer'], key="e_name")
                    new_ctrl = e_c3.number_input("Extra Ctrl", 0, 3, 0, key="e_ctrl") if "PS" in new_sys else 0
                    
                    e_btn1, e_btn2 = st.columns(2)
                    if e_btn1.button("💾 Save", use_container_width=True):
                        conn.table("sales").update({
                            "scheduled_date": new_date.strftime('%Y-%m-%d'), "entry_time": new_time.strftime("%I:%M %p"),
                            "system": new_sys, "duration": new_dur, "customer": new_name,
                            "total": get_price(SYSTEMS[new_sys], new_dur, new_ctrl)
                        }).eq("id", int(e_row['id'])).execute()
                        st.success("Updated!"); st.rerun()
                    if e_btn2.button("🗑️ Delete", type="primary", use_container_width=True):
                        conn.table("sales").delete().eq("id", int(e_row['id'])).execute()
                        st.warning("Deleted!"); st.rerun()

            else: st.caption("No upcoming bookings found.")
        except Exception as e: st.caption(f"Loading schedule... {e}")

# --- TAB 3: DAILY SUMMARY ---
with t3:
    st.subheader("📊 Today's Snapshot")
    try:
        raw = conn.table("sales").select("*").execute()
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
    except: st.error("Error loading summary.")

# --- TAB 4: REPORTS ---
with t4:
    st.subheader("📅 Deep Filter Reports")
    d_range = st.date_input("Date Range", [datetime.now(IST).date(), datetime.now(IST).date()])
    try:
        if len(d_range) == 2:
            s_dt, e_dt = [d.strftime('%Y-%m-%d') for d in d_range]
            raw_e = conn.table("sales").select("*").execute()
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
            raw_v = conn.table("sales").select("*").execute()
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
        except: st.error("Vault processing error.")

import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import datetime, timedelta

# --- PAGE CONFIG & STYLING ---
st.set_page_config(page_title="Gamerarena OS", page_icon="🎮", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    .stButton>button {
        background: linear-gradient(135deg, #6e8efb, #a777e3);
        color: white; border-radius: 8px; border: none;
        padding: 10px 20px; font-weight: bold; transition: 0.3s;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.3); }
    .active-card { background-color: #2b2b3d; padding: 20px; border-radius: 10px; border-left: 5px solid #00ff88; margin-bottom: 15px; }
    .vault-card { background-color: #1a1a2e; padding: 20px; border-radius: 10px; border: 1px solid #e94560; }
    .metric-box { background-color: #2b2b3d; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #444; }
</style>
""", unsafe_allow_html=True)

# --- SECURE LOGIN (STAFF LEVEL) ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    if not st.session_state["password_correct"]:
        st.title("🔒 Gamerarena Secure Access")
        pwd = st.text_input("Staff Password", type="password")
        if st.button("Login"):
            if pwd == "Admin@2026": 
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ Incorrect Password.")
        return False
    return True

if not check_password():
    st.stop()

# --- MAIN SETUP ---
st.title("🎮 Gamerarena Central OS")
st.caption("Palghar's Premier Gaming Destination | Admin Mode")
conn = st.connection("supabase", type=SupabaseConnection)

# --- STRICT PRICING LOGIC ---
PRICES_1HR = {"PC Gaming": 100, "PS5 Gaming": 150, "Racing Sim": 250}
PRICES_30MIN = {"PC Gaming": 70, "PS5 Gaming": 100, "Racing Sim": 150}
SYSTEMS = {
    "PS1": "PS5 Gaming", "PS2": "PS5 Gaming", "PS3": "PS5 Gaming", 
    "PC1": "PC Gaming", "PC2": "PC Gaming", "SIM1": "Racing Sim"
}

def calculate_price(category, duration, extra_ctrl=0):
    full_hours = int(duration)
    is_half_hour = (duration % 1) != 0 
    
    cost = (full_hours * PRICES_1HR[category])
    if is_half_hour: cost += PRICES_30MIN[category]
    if "PS5" in category: cost += (extra_ctrl * 100)
    return cost

# --- TABS ---
tab_book, tab_active, tab_data, tab_reports, tab_analytics = st.tabs([
    "📝 New Session", "🕹️ Active Sessions", "📊 Live Analytics", "📅 Daily Reports", "🧠 Deep Analytics"
])

# --- TAB 1: NEW SESSION ---
with tab_book:
    with st.container(border=True):
        col1, col2 = st.columns(2, gap="large")
        with col1:
            st.subheader("👤 Player Profile")
            cust_name = st.text_input("Gamer Name")
            cust_phone = st.text_input("Contact Number")
            cust_insta = st.text_input("Instagram ID")
            
        with col2:
            st.subheader("🕹️ Session Details")
            selected_systems = st.multiselect("Select Systems", list(SYSTEMS.keys()))
            
            st.write("Time In:")
            now = datetime.now()
            t1, t2, t3 = st.columns(3)
            sel_h = t1.selectbox("Hour", [f"{i:02d}" for i in range(1, 13)], index=int(now.strftime("%I"))-1)
            sel_m = t2.selectbox("Minute", [f"{i:02d}" for i in range(60)], index=int(now.strftime("%M")))
            sel_a = t3.selectbox("AM/PM", ["AM", "PM"], index=0 if now.strftime("%p") == "AM" else 1)
            
            duration = st.number_input("Duration (Hours)", min_value=0.5, max_value=12.0, step=0.5, value=1.0)
            
            has_ps5 = any("PS" in sys for sys in selected_systems)
            extra_ctrl = st.number_input("Extra Controllers (₹100 each)", 0, 3, 0) if has_ps5 else 0
            
    if st.button("🚀 Confirm & Deploy Session", use_container_width=True):
        if not cust_name or not selected_systems:
            st.error("⚠️ Please provide a Name and select a system.")
        else:
            try:
                with st.spinner("Starting Session..."):
                    for sys in selected_systems:
                        cat = SYSTEMS[sys]
                        total = calculate_price(cat, duration, extra_ctrl)
                        ftime = f"{sel_h}:{sel_m} {sel_a}"
                        
                        conn.table("sales").insert({
                            "customer": cust_name, "phone": cust_phone, "instagram": cust_insta,
                            "system": sys, "duration": duration, "total": total, 
                            "method": "Pending", "entry_time": ftime, "status": "Active" 
                        }).execute()
                st.success(f"✅ Session Started! Bill currently stands at ₹{total}.")
            except Exception as e:
                st.error(f"❌ Error: {e}")

# --- TAB 2: ACTIVE SESSIONS ---
with tab_active:
    st.subheader("🕹️ Live Operations Control")
    try:
        resp = conn.table("sales").select("*").eq("status", "Active").execute()
        active_df = pd.DataFrame(resp.data)
        
        if not active_df.empty:
            active_df['display_name'] = active_df['customer'] + " | " + active_df['system'] + " | Current Bill: ₹" + active_df['total'].astype(str)
            selected_session = st.selectbox("Select Player to Manage:", active_df['display_name'].tolist())
            
            target_row = active_df[active_df['display_name'] == selected_session].iloc[0]
            session_id = int(target_row['id'])
            current_total = float(target_row['total'])
            current_duration = float(target_row.get('duration', 0.0))
            sys_type = target_row['system']
            
            st.markdown(f"<div class='active-card'><b>Player:</b> {target_row['customer']} <br><b>System:</b> {sys_type} <br><b>Time In:</b> {target_row.get('entry_time', 'N/A')} <br><b>Total Hours:</b> {current_duration} <br><b>Current Bill:</b> ₹{current_total}</div>", unsafe_allow_html=True)
            
            action = st.radio("What would you like to do?", ["➕ Add Extra Time", "🛑 End Session & Collect Payment"])
            
            if action == "➕ Add Extra Time":
                extra_time = st.number_input("Additional Hours to Add", min_value=0.5, max_value=5.0, step=0.5, value=0.5)
                category = SYSTEMS[sys_type]
                extra_cost = calculate_price(category, extra_time, 0)
                
                new_total = current_total + extra_cost
                new_duration = current_duration + extra_time
                
                st.info(f"Adding {extra_time} hours adds ₹{extra_cost}. New Total: ₹{new_total}")
                
                if st.button("Update Session Bill", type="primary"):
                    conn.table("sales").update({"total": new_total, "duration": new_duration}).eq("id", session_id).execute()
                    st.success(f"✅ Updated! New Total is ₹{new_total}.")
                    st.rerun()
                    
            elif action == "🛑 End Session & Collect Payment":
                final_pay_mode = st.radio("How is the customer paying right now?", ["Cash", "Online / UPI"], horizontal=True)
                if st.button(f"Collect ₹{current_total} & End Session", type="primary"):
                    conn.table("sales").update({"status": "Completed", "method": final_pay_mode}).eq("id", session_id).execute()
                    st.balloons()
                    st.success("✅ Payment received. Session closed.")
                    st.rerun()
        else:
            st.info("No active sessions right now. The floor is clear!")
    except Exception as e:
        st.warning("Loading active sessions...")

# --- TAB 3: LIVE ANALYTICS ---
with tab_data:
    st.subheader("📈 Today's Performance")
    try:
        response = conn.table("sales").select("*").execute()
        data = pd.DataFrame(response.data)
        if not data.empty:
            data['date'] = pd.to_datetime(data['date'])
            today_data = data[data['date'].dt.date == datetime.now().date()]
            completed_data = today_data[today_data['status'] == 'Completed']
            active_data = today_data[today_data['status'] == 'Active']
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("💰 Total Collected", f"₹{completed_data['total'].sum():,.2f}")
            m2.metric("💵 Cash in Till", f"₹{completed_data[completed_data['method'] == 'Cash']['total'].sum():,.2f}")
            m3.metric("📱 Online / UPI", f"₹{completed_data[completed_data['method'] == 'Online / UPI']['total'].sum():,.2f}")
            m4.metric("⏳ Expected (On Floor)", f"₹{active_data['total'].sum():,.2f}")
            
            st.divider()
            cols = ['date', 'entry_time', 'duration', 'customer', 'system', 'total', 'method', 'status', 'phone', 'instagram']
            df_disp = data[[c for c in cols if c in data.columns]].copy()
            df_disp.sort_values(by="date", ascending=False, inplace=True)
            st.dataframe(df_disp, use_container_width=True, hide_index=True)
        else:
            st.info("No data yet.")
    except Exception as e:
        st.warning("Loading data...")

# --- TAB 4: DAILY REPORTS ---
with tab_reports:
    st.subheader("📥 Daily Export Center")
    try:
        response = conn.table("sales").select("*").execute()
        report_data = pd.DataFrame(response.data)
        if not report_data.empty:
            report_data['date'] = pd.to_datetime(report_data['date'])
            now_date = datetime.now()
            selected_date = st.date_input("Select a Date to Export", value=now_date.date())
            export_data = report_data[report_data['date'].dt.date == selected_date]
            
            export_cols = ['id', 'date', 'entry_time', 'duration', 'customer', 'phone', 'instagram', 'system', 'total', 'method', 'status']
            clean_export = export_data[[c for c in export_cols if c in export_data.columns]]
            
            if not export_data.empty:
                csv = clean_export.to_csv(index=False).encode('utf-8')
                st.download_button(label=f"Download Data for {selected_date}", data=csv, file_name=f"Gamerarena_Export_{selected_date}.csv", mime="text/csv", use_container_width=True)
            else:
                st.warning(f"No sessions were recorded on {selected_date}.")
    except Exception as e:
        st.warning("Loading reports...")

# --- TAB 5: DEEP ANALYTICS (OWNER ONLY) ---
with tab_analytics:
    st.subheader("🔐 The Owner's Vault")
    owner_pwd = st.text_input("Enter Master Passcode to view Deep Analytics", type="password", key="owner_pwd")
    
    if owner_pwd == "Shreenad@0511":
        st.markdown("<div class='vault-card'>🔓 Access Granted. Welcome to Gamerarena Intelligence.</div>", unsafe_allow_html=True)
        st.write("")
        
        try:
            response = conn.table("sales").select("*").execute()
            df = pd.DataFrame(response.data)
            
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                comp_df = df[df['status'] == 'Completed'].copy()
                
                # --- DATE LOGIC ---
                today = datetime.now().date()
                
                # Weekly Boundaries
                start_of_this_week = today - timedelta(days=today.weekday()) # Monday
                end_of_last_week = start_of_this_week - timedelta(days=1)    # Sunday
                start_of_last_week = start_of_this_week - timedelta(days=7)  # Previous Monday
                
                # Monthly Boundaries
                start_of_this_month = today.replace(day=1)                   # 1st of current month
                end_of_last_month = start_of_this_month - timedelta(days=1)  # Last day of previous month
                start_of_last_month = end_of_last_month.replace(day=1)       # 1st of previous month
                
                # Data Slicing
                wtd_data = comp_df[comp_df['date'].dt.date >= start_of_this_week]
                last_week_data = comp_df[(comp_df['date'].dt.date >= start_of_last_week) & (comp_df['date'].dt.date <= end_of_last_week)]
                
                mtd_data = comp_df[comp_df['date'].dt.date >= start_of_this_month]
                last_month_data = comp_df[(comp_df['date'].dt.date >= start_of_last_month) & (comp_df['date'].dt.date <= end_of_last_month)]
                
                # --- SECTION 1: CALENDAR PERFORMANCE ---
                st.markdown("### 📅 Business Performance Tracker")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"<div class='metric-box'><h4>Week-to-Date (WTD)</h4><h2>₹{wtd_data['total'].sum():,.2f}</h2><p>{len(wtd_data)} Sessions | {wtd_data['duration'].sum()} Hrs</p></div>", unsafe_allow_html=True

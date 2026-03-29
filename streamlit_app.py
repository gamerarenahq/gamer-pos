import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import datetime, timedelta
import pytz

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

# --- SECURE LOGIN ---
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

# Timezone for Palghar
IST = pytz.timezone('Asia/Kolkata')

# --- PRICING & HARDWARE ---
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
            now = datetime.now(IST)
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
                for sys in selected_systems:
                    cat = SYSTEMS[sys]
                    total = calculate_price(cat, duration, extra_ctrl)
                    ftime = f"{sel_h}:{sel_m} {sel_a}"
                    conn.table("sales").insert({
                        "customer": cust_name, "phone": cust_phone, "instagram": cust_insta,
                        "system": sys, "duration": duration, "total": total, 
                        "method": "Pending", "entry_time": ftime, "status": "Active" 
                    }).execute()
                st.success(f"✅ Session Started for {cust_name}!")
            except Exception as e:
                st.error(f"❌ Error: {e}")

# --- TAB 2: ACTIVE SESSIONS ---
with tab_active:
    st.subheader("🕹️ Live Operations Control")
    try:
        resp = conn.table("sales").select("*").eq("status", "Active").execute()
        active_df = pd.DataFrame(resp.data)
        if not active_df.empty:
            active_df['display_name'] = active_df['customer'] + " | " + active_df['system'] + " | Bill: ₹" + active_df['total'].astype(str)
            selected_session = st.selectbox("Select Player:", active_df['display_name'].tolist())
            target_row = active_df[active_df['display_name'] == selected_session].iloc[0]
            session_id, current_total, current_duration = int(target_row['id']), float(target_row['total']), float(target_row.get('duration', 0.0))
            sys_type = target_row['system']
            st.markdown(f"<div class='active-card'><b>Player:</b> {target_row['customer']} <br><b>Hardware:</b> {sys_type} <br><b>Time In:</b> {target_row.get('entry_time', 'N/A')} <br><b>Hours:</b> {current_duration} <br><b>Current Bill:</b> ₹{current_total}</div>", unsafe_allow_html=True)
            action = st.radio("Action:", ["➕ Add Extra Time", "🛑 End Session & Pay"])
            if action == "➕ Add Extra Time":
                extra_time = st.number_input("Add Hours", 0.5, 5.0, 0.5)
                extra_cost = calculate_price(SYSTEMS[sys_type], extra_time, 0)
                if st.button("Update Bill"):
                    conn.table("sales").update({"total": current_total + extra_cost, "duration": current_duration + extra_time}).eq("id", session_id).execute()
                    st.rerun()
            elif action == "🛑 End Session & Pay":
                pay_mode = st.radio("Payment:", ["Cash", "Online / UPI"], horizontal=True)
                if st.button("Collect & Close"):
                    conn.table("sales").update({"status": "Completed", "method": pay_mode}).eq("id", session_id).execute()
                    st.balloons()
                    st.rerun()
        else:
            st.info("No active sessions right now.")
    except Exception as e:
        st.warning(f"Connection wait... {e}")

# --- TAB 3: LIVE ANALYTICS ---
with tab_data:
    st.subheader("📈 Today's Performance")
    try:
        response = conn.table("sales").select("*").execute()
        data = pd.DataFrame(response.data)
        if not data.empty:
            data['date'] = pd.to_datetime(data['date']).dt.tz_convert('Asia/Kolkata')
            today_date = datetime.now(IST).date()
            today_data = data[data['date'].dt.date == today_date]
            completed_data, active_data = today_data[today_data['status'] == 'Completed'], today_data[today_data['status'] == 'Active']
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("💰 Collected", f"₹{completed_data['total'].sum():,.2f}")
            m2.metric("💵 Cash", f"₹{completed_data[completed_data['method'] == 'Cash']['total'].sum():,.2f}")
            m3.metric("📱 UPI", f"₹{completed_data[completed_data['method'] == 'Online / UPI']['total'].sum():,.2f}")
            m4.metric("⏳ Pending", f"₹{active_data['total'].sum():,.2f}")
            st.divider()
            st.dataframe(data.sort_values(by='date', ascending=False), use_container_width=True, hide_index=True)
    except:
        st.info("No data yet.")

# --- TAB 4: DAILY REPORTS ---
with tab_reports:
    st.subheader("📥 Export Center")
    try:
        response = conn.table("sales").select("*").execute()
        report_data = pd.DataFrame(response.data)
        if not report_data.empty:
            report_data['date'] = pd.to_datetime(report_data['date']).dt.tz_convert('Asia/Kolkata')
            selected_date = st.date_input("Export Date", value=datetime.now(IST).date())
            export_df = report_data[report_data['date'].dt.date == selected_date]
            if not export_df.empty:
                csv = export_df.to_csv(index=False).encode('utf-8')
                st.download_button("Download CSV", csv, f"Export_{selected_date}.csv", "text/csv")
            else:
                st.warning("No data for this date.")
    except:
        st.info("No data available.")

# --- TAB 5: DEEP ANALYTICS ---
with tab_analytics:
    st.subheader("🔐 The Owner's Vault")
    owner_pwd = st.text_input("Master Passcode", type="password")
    if owner_pwd == "Shreenad@0511":
        st.markdown("<div class='vault-card'>🔓 Access Granted.</div>", unsafe_allow_html=True)
        try:
            response = conn.table("sales").select("*").execute()
            df = pd.DataFrame(response.data)
            if not df.empty:
                df['date'] = pd.to_datetime(df['date']).dt.tz_convert('Asia/Kolkata').dt.tz_localize(None)
                comp_df = df[df['status'] == 'Completed'].copy()
                today = datetime.now(IST).date()
                s_w, s_m = today - timedelta(days=today.weekday()), today.replace(day=1)
                l_w_s, l_w_e = s_w - timedelta(days=7), s_w - timedelta(days=1)
                l_m_e = s_m - timedelta(days=1)
                l_m_s = l_m_e.replace(day=1)
                
                # Metrics
                wtd = comp_df[comp_df['date'].dt.date >= s_w]
                mtd = comp_df[comp_df['date'].dt.date >= s_m]
                lw = comp_df[(comp_df['date'].dt.date >= l_w_s) & (comp_df['date'].dt.date <= l_w_e)]
                lm = comp_df[(comp_df['date'].dt.date >= l_m_s) & (comp_df['date'].dt.date <= l_m_e)]
                
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"<div class='metric-box'><h4>WTD (Mon-Sun)</h4><h2>₹{wtd['total'].sum():,.2f}</h2></div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='metric-box'><h4>MTD ({today.strftime('%B')})</h4><h2>₹{mtd['total'].sum():,.2f}</h2></div>", unsafe_allow_html=True)
                with c2:
                    st.markdown(f"<div class='metric-box'><h4>Last Week</h4><h2>₹{lw['total'].sum():,.2f}</h2></div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='metric-box'><h4>Last Month</h4><h2>₹{lm['total'].sum():,.2f}</h2></div>", unsafe_allow_html=True)
                
                st.divider()
                st.subheader("🖥️ Hardware Performance")
                h_map = {"PC1": "PC", "PC2": "PC", "PS1": "Playstation 5", "PS2": "Playstation 5", "PS3": "Playstation 5", "SIM1": "Racing Simulator"}
                comp_df['display_sys'] = comp_df['system'].map(h_map).fillna(comp_df['system'])
                hw_stats = comp_df.groupby('display_sys').agg(Rev=('total', 'sum'), Hrs=('duration', 'sum')).reset_index()
                ca, cb = st.columns([1, 1.5])
                ca.dataframe(hw_stats, hide_index=True)
                cb.bar_chart(hw_stats.set_index('display_sys')['Rev'])
        except Exception as e:
            st.error(f"Error: {e}")

import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import datetime

# --- PAGE CONFIG & STYLING ---
st.set_page_config(page_title="Gamerarena OS", page_icon="🎮", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    .stButton>button {
        background: linear-gradient(135deg, #6e8efb, #a777e3);
        color: white; border-radius: 10px; border: none;
        padding: 12px 24px; font-weight: 700; font-size: 16px; transition: 0.3s ease;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 8px 15px rgba(0,0,0,0.2); }
</style>
""", unsafe_allow_html=True)

# --- SECURE LOGIN ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.title("🔒 Gamerarena Secure Access")
        pwd = st.text_input("Admin Password", type="password")
        if st.button("Login"):
            if pwd == "Admin@2026": 
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ Incorrect Password. Access Denied.")
        return False
    return True

if not check_password():
    st.stop()

# --- MAIN DASHBOARD SETUP ---
st.title("🎮 Gamerarena Central OS")
st.caption("Palghar's Premier Gaming Destination | Admin Mode")

conn = st.connection("supabase", type=SupabaseConnection)

# --- SMART PRICING LOGIC ---
PRICES_1HR = {"PC Gaming": 100, "PS5 Gaming": 150, "Racing Sim": 250}
PRICES_30MIN = {"PC Gaming": 70, "PS5 Gaming": 100, "Racing Sim": 150}

SYSTEMS = {
    "PS1": "PS5 Gaming", "PS2": "PS5 Gaming", "PS3": "PS5 Gaming", 
    "PC1": "PC Gaming", "PC2": "PC Gaming", "SIM1": "Racing Sim"
}

def calculate_price(category, duration, extra_ctrl=0):
    full_hours = int(duration)
    is_half_hour = (duration % 1) == 0.5
    
    cost = (full_hours * PRICES_1HR[category])
    if is_half_hour: cost += PRICES_30MIN[category]
    if "PS5" in category: cost += (extra_ctrl * 100)
        
    return cost

# --- TABS ---
tab_book, tab_extend, tab_data = st.tabs(["📝 New Session", "⏳ Extend Time", "📊 Analytics & Downloads"])

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
            entry_time = st.time_input("Time In", value="now")
            duration = st.number_input("Duration (Hours)", min_value=0.5, max_value=12.0, step=0.5, value=1.0)
            
            has_ps5 = any("PS" in sys for sys in selected_systems)
            extra_ctrl = st.number_input("Extra Controllers (₹100 each)", 0, 3, 0) if has_ps5 else 0
            pay_mode = st.radio("Payment Gateway", ["Cash", "Online / UPI"], horizontal=True)
            
    if st.button("🚀 Confirm & Deploy Session", use_container_width=True):
        if not cust_name or not selected_systems:
            st.error("⚠️ Please provide a Name and select a system.")
        else:
            try:
                with st.spinner("Syncing..."):
                    for sys in selected_systems:
                        cat = SYSTEMS[sys]
                        total = calculate_price(cat, duration, extra_ctrl)
                        ftime = entry_time.strftime("%I:%M %p")
                        
                        conn.table("sales").insert({
                            "customer": cust_name, "phone": cust_phone, "instagram": cust_insta,
                            "system": sys, "total": total, "method": pay_mode, "entry_time": ftime
                        }).execute()
                st.success(f"✅ Logged! Collect: ₹{total} per system.")
            except Exception as e:
                st.error(f"❌ Error: {e}")

# --- TAB 2: EXTEND TIME (NEW FEATURE) ---
with tab_extend:
    st.subheader("⏳ Add time to an active session")
    try:
        # Fetch today's sessions to extend
        resp = conn.table("sales").select("*").execute()
        df_ext = pd.DataFrame(resp.data)
        
        if not df_ext.empty:
            df_ext['date'] = pd.to_datetime(df_ext['date'])
            today_ext = df_ext[df_ext['date'].dt.date == datetime.now().date()].copy()
            
            if not today_ext.empty:
                # Create a readable dropdown menu
                today_ext['display_name'] = today_ext['customer'] + " | " + today_ext['system'] + " | Current Bill: ₹" + today_ext['total'].astype(str)
                
                selected_session = st.selectbox("Select Active Player", today_ext['display_name'].tolist())
                extra_time = st.number_input("Additional Hours", min_value=0.5, max_value=5.0, step=0.5, value=0.5)
                
                if st.button("➕ Update & Add Time", type="primary"):
                    # Find the exact row in the database
                    target_row = today_ext[today_ext['display_name'] == selected_session].iloc[0]
                    session_id = int(target_row['id'])
                    current_total = float(target_row['total'])
                    sys_type = target_row['system']
                    
                    # Calculate ONLY the cost of the extra time (no extra controllers charged again)
                    category = SYSTEMS[sys_type]
                    extra_cost = calculate_price(category, extra_time, 0)
                    new_total = current_total + extra_cost
                    
                    # Update the Database
                    conn.table("sales").update({"total": new_total}).eq("id", session_id).execute()
                    
                    st.balloons()
                    st.success(f"✅ Success! Added ₹{extra_cost} to the bill. New Total to collect is ₹{new_total}.")
            else:
                st.info("No active sessions logged today yet.")
    except Exception as e:
        st.warning("Loading database...")

# --- TAB 3: ANALYTICS ---
with tab_data:
    st.subheader("📈 Real-Time Cafe Metrics")
    try:
        response = conn.table("sales").select("*").execute()
        data = pd.DataFrame(response.data)
        
        if not data.empty:
            data['date'] = pd.to_datetime(data['date'])
            today_data = data[data['date'].dt.date == datetime.now().date()]
            
            m1, m2, m3 = st.columns(3)
            m1.metric("💰 Today's Collection", f"₹{today_data['total'].sum():,.2f}")
            m2.metric("💵 Cash Collected", f"₹{today_data[today_data['method'] == 'Cash']['total'].sum():,.2f}")
            m3.metric("📱 Online / UPI", f"₹{today_data[today_data['method'] == 'Online / UPI']['total'].sum():,.2f}")
            
            st.divider()
            
            if not today_data.empty:
                csv = today_data.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Today's Summary (CSV/Excel)",
                    data=csv, file_name=f"Gamerarena_Summary_{datetime.now().date()}.csv", mime="text/csv", use_container_width=True
                )
            
            cols = ['date', 'entry_time', 'customer', 'system', 'total', 'method', 'phone', 'instagram']
            display_cols = [c for c in cols if c in data.columns]
            
            df_disp = data[display_cols].copy()
            df_disp.sort_values(by="date", ascending=False, inplace=True)
            st.dataframe(df_disp, use_container_width=True, hide_index=True)
        else:
            st.info("No data yet.")
    except Exception as e:
        st.warning("Loading data...")

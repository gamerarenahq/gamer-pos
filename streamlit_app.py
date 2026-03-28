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
                st.success(f"✅ Session Started! Bill currently stands

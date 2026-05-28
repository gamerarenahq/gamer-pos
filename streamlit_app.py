import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import datetime, timedelta
import pytz
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIG & UI THEME ---
st.set_page_config(page_title="Gamerarena Master ERP", page_icon="🎮", layout="wide")
st_autorefresh(interval=60000, limit=None, key="crm_refresh")
IST = pytz.timezone('Asia/Kolkata')

st.markdown("""
<style>
    .stApp { background-color: #0B0E14; color: #FFFFFF; }
    h1, h2, h3, h4, p, span, label, div { color: #FFFFFF !important; }
    .stButton>button { background: linear-gradient(135deg, #00D0FF 0%, #0080FF 100%); color: #FFFFFF !important; border-radius: 8px; font-weight: 700; border: none; }
    .metric-box { background-color: #121824; padding: 20px; border-radius: 12px; border-top: 3px solid #00D0FF; }
    .panel-box { background: #121824; padding: 20px; border-radius: 16px; border: 1px solid #1E293B; }
</style>
""", unsafe_allow_html=True)

# --- 2. AUTH ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🔒 Gamerarena Central Login")
    if st.text_input("Enter Passcode", type="password") == "Admin@2026":
        st.session_state.auth = True; st.rerun()
    st.stop()

# --- 3. DATABASE SETUP ---
try: 
    conn = st.connection("supabase", type=SupabaseConnection, ttl=0)
except Exception as e: st.error(f"DB Error: {e}"); st.stop()

SYSTEMS = {"PS1":"PS5", "PS2":"PS5", "PS3":"PS5", "PC1":"PC", "PC2":"PC", "SIM1":"Racing Sim"}

# --- TABS ---
t1, t2, t3, t4 = st.tabs(["🕹️ Live Floor", "🍔 Cafe & Stock", "📅 Bookings", "🧠 Master Vault"])

# ==========================================
# TAB 1: LIVE FLOOR
# ==========================================
with t1:
    # Fetch data
    active_res = conn.table("sales").select("*").in_("status", ["Active", "Booked"]).order('id', desc=True).execute()
    db_df = pd.DataFrame(active_res.data) if active_res.data else pd.DataFrame()
    
    # Calculate Pending on Floor
    pending_floor = 0.0
    if not db_df.empty:
        pending_floor = pd.to_numeric(db_df[db_df['status']=='Active']['total'], errors='coerce').fillna(0.0).sum()
    
    st.markdown(f"<div class='metric-box'>Pending on Floor: <h2>₹{pending_floor:,.0f}</h2></div>", unsafe_allow_html=True)
    
    col_floor, col_op = st.columns([2.5, 1], gap="large")
    with col_floor:
        st.subheader("Active Sessions")
        active_gamers = db_df[db_df['status'] == 'Active']
        if active_gamers.empty: st.info("Floor is clear.")
        else:
            for _, row in active_gamers.iterrows():
                st.write(f"🎮 {row['system']} | {row['customer']} | Total: ₹{row['total']}")
    
    with col_op:
        st.markdown("<div class='panel-box'>", unsafe_allow_html=True)
        st.subheader("Operator")
        if not active_gamers.empty:
            sel = st.selectbox("Select Gamer", active_gamers['customer'].tolist())
            if st.button("Collect & Close"):
                st.write("Processing Checkout...")
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# TAB 4: MASTER VAULT (OWNER VIEW)
# ==========================================
with t4:
    st.subheader("🔐 Master Intelligence Vault")
    if st.text_input("Master Key", type="password", key="t5_pwd") == "Su22101992@":
        st.success("Vault Unlocked")
        # Simplified display for stability
        vdf = pd.DataFrame(conn.table("sales").select("*").order('id', desc=True).limit(500).execute().data)
        st.dataframe(vdf)

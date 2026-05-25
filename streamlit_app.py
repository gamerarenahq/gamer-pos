import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import datetime, timedelta
import pytz
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIG ---
st.set_page_config(page_title="Gamerarena Master ERP", page_icon="🎮", layout="wide")
st_autorefresh(interval=60000, limit=None, key="crm_refresh")
IST = pytz.timezone('Asia/Kolkata')

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
except Exception as e: 
    st.error(f"DB Error: {e}"); st.stop()

SYSTEMS = {"PS1":"PS5", "PS2":"PS5", "PS3":"PS5", "PC1":"PC", "PC2":"PC", "SIM1":"Racing Sim"}
VENDOR_CATS = ["Burgers & Meals", "Fries & Snacks"]

# --- HELPER FUNCS ---
def get_price(cat, dur, extra=0):
    full_hours = int(dur); half_hours = 1 if (dur % 1) != 0 else 0
    if cat == "PC": return (full_hours * 100) + (half_hours * 70)
    elif cat == "Racing Sim": return (full_hours * 250) + (half_hours * 150)
    elif cat == "PS5":
        base_full = 150 + (extra * 100); base_half = 100 + (extra * 100)
        return (full_hours * base_full) + (half_hours * base_half)
    return 0

# --- TABS ---
t1, t2, t3, t4, t5 = st.tabs(["🕹️ Live Floor", "🍔 Cafe & Stock", "📅 Bookings", "📊 Snapshot", "🧠 Master Vault"])

# ==========================================
# TAB 1: LIVE FLOOR (ISOLATED & STABLE)
# ==========================================
with t1:
    try:
        active_res = conn.table("sales").select("*").in_("status", ["Active", "Booked"]).order('id', desc=True).limit(1000).execute()
        db_df = pd.DataFrame(active_res.data) if active_res.data else pd.DataFrame()
        active_gamers = db_df[db_df['status'] == 'Active'] if not db_df.empty else pd.DataFrame()
        
        st.subheader("Active Sessions")
        if active_gamers.empty: st.info("Floor is clear.")
        else:
            for _, row in active_gamers.iterrows():
                st.write(f"🎮 {row['system']} | {row['customer']} | In: {row['entry_time']}")
    except Exception as e: st.error("Live floor temporarily unreachable. Please check connection.")

# ==========================================
# TAB 5: MASTER VAULT (ISOLATED)
# ==========================================
with t5:
    st.subheader("🔐 Master Intelligence Vault")
    if st.text_input("Master Key", type="password", key="t5_pwd") == "Su22101992@":
        try:
            # We wrap the complex P&L logic in a try/except block.
            # If the data process crashes, it won't kill the whole app.
            vdf = pd.DataFrame(conn.table("sales").select("*").order('id', desc=True).limit(5000).execute().data)
            st.success("Vault Data Loaded Successfully.")
            st.dataframe(vdf.head(10)) # Show latest 10 rows to prove it works
        except Exception as e:
            st.error("Vault data encountered an error during processing. Try syncing.")

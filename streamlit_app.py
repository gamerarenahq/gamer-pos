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
    .block-container { padding-top: 1.5rem; font-family: 'Inter', sans-serif; }
    .stApp { background-color: #0B0E14; color: white; }
    h1, h2, h3, h4, p, span, label { color: white !important; }
    
    .stButton>button { background: #4F46E5; color: white; border-radius: 8px; width: 100%; font-weight: 600; border: none; transition: 0.2s; }
    .stButton>button:hover { background: #4338CA; box-shadow: 0 4px 10px rgba(79, 70, 229, 0.4); transform: translateY(-2px); }
    
    .crm-card { background-color: #1A1F2B; padding: 20px; border-radius: 12px; border-left: 4px solid #98DED9; margin-bottom: 12px; }
    .warning-card { background-color: #1A1F2B; padding: 20px; border-radius: 12px; border-left: 4px solid #FF754C; margin-bottom: 12px; }
    .overdue-card { background-color: #2D1E1E; padding: 20px; border-radius: 12px; border-left: 4px solid #EF4444; margin-bottom: 12px; }
    
    .metric-box { background-color: #1A1F2B; padding: 20px; border-radius: 12px; text-align: center; border-top: 3px solid #98DED9; }
    .panel-box { background: #1A1F2B; padding: 20px; border-radius: 16px; border: 1px solid #2D3446; }
    
    /* Custom Menu Buttons */
    .menu-btn>button { background: #161922; border: 1px solid #2D3446; height: 70px; border-radius: 10px; }
    .menu-btn>button:hover { border-color: #98DED9; color: #98DED9 !important; }
</style>
""", unsafe_allow_html=True)

# --- 2. STATE & AUTH ---
if "auth" not in st.session_state: st.session_state.auth = False
if "cart" not in st.session_state: st.session_state.cart = []
if "fnb_cart" not in st.session_state: st.session_state.fnb_cart = []
if "form_reset" not in st.session_state: st.session_state.form_reset = 0

if not st.session_state.auth:
    st.title("🔒 Gamerarena Central Login")
    if st.text_input("Enter Passcode", type="password") == "Admin@2026":
        st.session_state.auth = True; st.rerun()
    st.stop()

# --- 3. DATABASE & PRICING ---
try: conn = st.connection("supabase", type=SupabaseConnection)
except: st.error("Database Connection Error."); st.stop()

SYSTEMS = {"PS1":"PS5", "PS2":"PS5", "PS3":"PS5", "PC1":"PC", "PC2":"PC", "SIM1":"Racing Sim"}

def get_price(cat, dur, extra=0):
    if cat == "PS5": return (int(dur) * (150 + (extra * 100))) + ((1 if (dur % 1) != 0 else 0) * (100 + (extra * 100)))
    elif cat == "PC": return (int(dur) * 100) + ((1 if (dur % 1) != 0 else 0) * 70)
    elif cat == "Racing Sim": return (int(dur) * 250) + ((1 if (dur % 1) != 0 else 0) * 150)
    return 0

# Fetch global data
try:
    inv_res = conn.table("inventory").select("*").order('item_name').execute()
    inv_df = pd.DataFrame(inv_res.data) if inv_res.data else pd.DataFrame()
    active_res = conn.table("sales").select("*").in_("status", ["Active", "Booked"]).execute()
    db_df = pd.DataFrame(active_res.data) if active_res.data else pd.DataFrame()
except: st.error("Syncing Database..."); st.stop()

# --- 4. APP LAYOUT ---
t1, t2, t3, t4, t5 = st.tabs(["🕹️ Live Floor", "🍔 Cafe & Stock", "📅 Bookings & Queue", "📊 Daily Snapshot", "🧠 Master Vault"])

# ==========================================
# TAB 1: LIVE FLOOR & CHECKOUT
# ==========================================
with t1:
    col_floor, col_op = st.columns([2.5, 1], gap="large")
    active_gamers = db_df[db_df['status'] == 'Active'] if not db_df.empty else pd.DataFrame()
    
    with col_floor:
        st.subheader("Active Sessions")
        if active_gamers.empty: st.info("Floor is clear.")
        else:
            grid = st.columns(3)
            for i, (_, row) in enumerate(active_gamers.iterrows()):
                try:
                    entry_dt = pd.to_datetime(f"{row['date'][:10]} {row['entry_time']}").tz_localize(IST)
                    time_left = ((entry_dt + timedelta(hours=row['duration'])) - datetime.now(IST)).total_seconds() / 60.0
                except: time_left = 999 

                if time_left < 0: cc, txt = "overdue-card", f"🚨 {abs(int(time_left))}m OVERDUE"
                elif time_left <= 10: cc, txt = "warning-card", f"⚠️ {int(time_left)}m LEFT"
                else: cc, txt = "crm-card", f"⏳ {int(time_left)}m left"
                
                fnb_val = row.get('fnb_total') or 0
                fnb_str = f" | F&B: ₹{fnb_val:.0f}" if fnb_val > 0 else ""

                with grid[i % 3]:
                    st.markdown(f"<div class='{cc}'><h4 style='color:#98DED9; margin:0;'>{row['system']}</h4><b>{row['customer']}</b><br><span style='font-size:12px; color:#9CA3AF;'>Game: ₹{row['total']:.0f}{fnb_str}</span><h3 style='margin:5px 0;'>{txt}</h3></div>", unsafe_allow_html=True)

    with col_op:
        st.markdown("<div class='panel-box'>", unsafe_allow_html=True)
        st.subheader("Operator Panel")
        if not active_gamers.empty:
            active_gamers['lbl'] = active_gamers['customer'] + " | " + active_gamers['system']
            sel = st.selectbox("Select Gamer", active_gamers['lbl'].tolist(), label_visibility="collapsed")
            row = active_gamers[active_gamers['lbl'] == sel].iloc[0]
            
            op_mode = st.radio("Action", ["Smart Checkout", "Add Time"], horizontal=True)
            
            if op_mode == "Smart Checkout":
                try: played_mins = int((datetime.now(IST) - pd.to_datetime(f"{row['date'][:10]} {row['entry_time']}").tz_localize(IST)).total_seconds() / 60.0)
                except: played_mins = 0
                st.caption(f"⏱️ Actual Time Played: **{played_mins} mins**")
                
                rec_dur = float(row['duration'])
                if played_mins <= 40 and row['duration'] >= 1.0: rec_dur = 0.5
                elif played_mins > 40 and played_mins <= 60 and row['duration'] > 1.0: rec_dur = 1.0
                
                f_dur = st.number_input("Billed Hrs", 0.5, 12.0, float(rec_dur), 0.5)
                
                game_bill = float(row['total'])
                food_bill = float(row.get('fnb_total') or 0)
                grand_total = game_bill + food_bill
                
                st.markdown(f"<div style='background:#161922; padding:10px; border-radius:8px;'><small>Gaming: ₹{game_bill:.0f}<br>F&B Tab: ₹{food_bill:.0f}</small><h3 style='color:#98DED9; margin:0;'>Total: ₹{grand_total:.0f}</h3></div><br>", unsafe_allow_html=True)
                
                pay = st.radio("Pay Method", ["Cash", "UPI"], horizontal=True)
                if st.button("🛑 Collect & Close", type="primary"):
                    conn.table("sales").update({"status": "Completed", "method": pay, "duration": float(f_dur), "total": float(grand_total)}).eq("id", int(row['id'])).execute()
                    st.balloons(); st.rerun()
                    
            elif op_mode == "Add Time":
                ext = st.number_input("Extra Hrs", 0.5, 5.0, 0.5)
                if st.button("➕ Extend Session"):
                    new_dur = float(row['duration']) + float(ext)
                    new_total = float(row['total']) + float(get_price(SYSTEMS[row['system']], ext, 0))
                    conn.table("sales").update({"total": new_total, "duration": new_dur}).eq("id", int(row['id'])).execute()
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# TAB 2: CAFE POS & INVENTORY MANAGER
# ==========================================
with t2:
    pos_tab, inv_tab = st.tabs(["🛒 F&B Point of Sale", "📦 Stock & Inventory Manager"])
    
    with pos_tab:
        col_menu, col_cart = st.columns([2.5, 1], gap="large")
        with col_menu:
            if inv_df.empty: st.warning("Inventory is empty. Go to the Stock tab to add items.")
            else:
                # Grouped Dropdowns (Expanders) for clean UI
                categories

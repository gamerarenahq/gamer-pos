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
IST = pytz.timezone('Asia/Kolkata')
now_ist = datetime.now(IST)

if "auth" not in st.session_state: st.session_state.auth = False
if "cart" not in st.session_state: st.session_state.cart = []

# Memory Locks to prevent UI resets
if "b_type" not in st.session_state: st.session_state.b_type = "🏃‍♂️ Walk-in (Play Now)"
if "b_date" not in st.session_state: st.session_state.b_date = now_ist.date()
if "b_time" not in st.session_state: st.session_state.b_time = now_ist.time()

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
    col_form, col_cart = st.columns([1.2, 1], gap="large")
    
    with col_form:
        st.subheader("1. Lead & Booking Details")
        with st.container(border=True):
            name = st

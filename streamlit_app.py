import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import datetime, timedelta
import pytz

# --- 1. CONFIG & STYLE ---
st.set_page_config(page_title="Gamerarena OS", page_icon="🎮", layout="wide")

st.markdown("""
<style>
    .stButton>button { background: linear-gradient(135deg, #6e8efb, #a777e3); color: white; border-radius: 8px; width: 100%; font-weight: bold; }
    .active-card { background-color: #1e1e2f; padding: 20px; border-radius: 10px; border-left: 5px solid #00ff88; margin-bottom: 15px; }
    .metric-box { background-color: #1e1e2f; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #444; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 2. AUTHENTICATION ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔒 Gamerarena Access")
    pwd = st.text_input("Enter Passcode", type="password")
    if st.button("Login"):
        if pwd == "Admin@2026":
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Invalid Code")
    st.stop()

# --- 3. DATABASE CONNECTION ---
try:
    conn = st.connection("supabase", type=SupabaseConnection)
except:
    st.error("Database Connection Error. Check Secrets.")
    st.stop()

IST = pytz.timezone('Asia/Kolkata')
SYSTEMS = {"PS1":"PS5 Gaming", "PS2":"PS5 Gaming", "PS3":"PS5 Gaming", "PC1":"PC Gaming", "PC2":"PC Gaming", "SIM1":"Racing Sim"}
PRICES_1H = {"PC Gaming": 100, "PS5 Gaming": 150, "Racing Sim": 250}
PRICES_30M = {"PC Gaming": 70, "PS5 Gaming": 100, "Racing Sim": 150}

def get_price(cat, dur, extra=0):
    cost = int(dur) * PRICES_1H.get(cat, 0)
    if (dur % 1) != 0: cost += PRICES_30M.get(cat, 0)
    if "PS5" in cat: cost += (extra * 100)
    return cost

# --- 4. NAVIGATION ---
t1, t2, t3, t4, t5 = st.tabs(["📝 Entry", "🕹️ Floor", "📊 Today", "📅 Export", "🧠 Vault"])

# TAB 1: NEW ENTRY
with t1:
    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Gamer Name")
            phone = st.text_input("Phone")
        with c2:
            sys_list = st.multiselect("Systems", list(SYSTEMS.keys()))
            now = datetime.now(IST)
            h_col, m_col, a_col = st.columns(3)
            sh = h_col.selectbox("HH", [f"{i:02d}" for i in range(1, 13)], index=int(now.strftime("%I"))-1)
            sm = m_col.selectbox("MM", [f"{i:02d}" for i in range(60)], index=int(now.strftime("%M")))
            sa = a_col.selectbox("AM/PM", ["AM", "PM"], index=0 if now.strftime("%p")=="AM" else 1)
            dur = st.number_input("Hours", 0.5, 12.0, 1.0, 0.5)
            ctrl = st.number_input("Extra Controllers", 0, 3, 0) if any("PS" in s for s in sys_list) else 0

    if st.button("Start Session"):
        if name and sys_list:
            for s in sys_list:
                bill = get_price(SYSTEMS[s], dur, ctrl)
                conn.table("sales").insert({
                    "customer": name, "phone": phone, "system": s, "duration": dur, 
                    "total": bill, "method": "Pending", "entry_time": f"{sh}:{sm} {sa}", "status": "Active"
                }).execute()
            st.success("Session Active!")
            st.rerun()

# TAB 2: FLOOR
with t2:
    try:
        res = conn.table("sales").select("*").eq("status", "Active").execute()
        active_df = pd.DataFrame(res.data)
        if not active_df.empty:
            active_df['label'] = active_df['customer'] + " | " + active_df['system']
            sel = st.selectbox("Select Player", active_df['label'].tolist())
            row = active_df[active_df['label'] == sel].iloc[0]
            st.markdown(f"<div class='active-card'><b>{row['customer']}</b> on {row['system']}<br>Bill: ₹{row['total']}</div>", unsafe_allow_html=True)
            
            op = st.radio("Action", ["Add Time", "End & Pay"])
            if op == "Add Time":
                ext = st.number_input("Extra Hrs", 0.5, 5.0, 0.5)
                if st.button("Add"):
                    extra_cost = get_price(SYSTEMS[row['system']], ext, 0)
                    conn.table("sales").update({"total": row['total'] + extra_cost, "duration": row['duration'] + ext}).eq("id", row['id']).execute()
                    st.rerun()
            else:
                pay = st.radio("Method", ["Cash", "Online / UPI"], horizontal=True)
                if st.button("Close"):
                    conn.table("sales").update({"status": "Completed", "method": pay}).eq("id", row['id']).execute()
                    st.rerun()
        else:
            st.info("Floor Empty.")
    except: st.write("Syncing Floor...")

# TAB 3: TODAY'S STATS
with t3:
    try:
        raw = conn.table("sales").select("*").execute()
        df = pd.DataFrame(raw.data)
        if not df.empty:
            # Date Handling
            df['date_dt'] = pd.to_datetime(df['date']).dt.tz_convert('Asia/Kolkata')
            today = datetime.now(IST).date()
            t_df = df[df['date_dt'].dt.date == today]
            
            comp = t_df[t_df['status'] == 'Completed']
            act = t_df[t_df['status'] == 'Active']
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Today's Cash", f"₹{comp[comp['method']=='Cash']['total'].sum():,.0f}")
            m2.metric("Today's UPI", f"₹{comp[comp['method']!='Cash']['total'].sum():,.0f}")
            m3.metric("Running Total", f"₹{act['total'].sum():,.0f}")
            
            st.divider()
            st.write("### Today's Log")
            st.dataframe(t

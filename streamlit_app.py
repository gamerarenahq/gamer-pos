import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import datetime, timedelta
import pytz

# --- 1. SETTINGS & STYLE ---
st.set_page_config(page_title="Gamerarena OS", page_icon="🎮", layout="wide")

st.markdown("""
<style>
    .stButton>button { background: linear-gradient(135deg, #6e8efb, #a777e3); color: white; border-radius: 8px; width: 100%; font-weight: bold; }
    .active-card { background-color: #1e1e2f; padding: 20px; border-radius: 10px; border-left: 5px solid #00ff88; margin-bottom: 15px; }
    .metric-box { background-color: #1e1e2f; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #444; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 2. LOGIN ---
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

# --- 3. DATABASE ---
try:
    conn = st.connection("supabase", type=SupabaseConnection)
except:
    st.error("Database Error. Check your Streamlit Secrets.")
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

# --- 4. TABS ---
t1, t2, t3, t4, t5 = st.tabs(["📝 Entry", "🕹️ Floor", "📊 Today", "📅 Export", "🧠 Vault"])

# --- TAB 1: ENTRY ---
with t1:
    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Gamer Name")
            phone = st.text_input("Phone")
        with c2:
            sys_list = st.multiselect("Systems", list(SYSTEMS.keys()))
            now = datetime.now(IST)
            h, m, ap = st.columns(3)
            sh = h.selectbox("HH", [f"{i:02d}" for i in range(1, 13)], index=int(now.strftime("%I"))-1)
            sm = m.selectbox("MM", [f"{i:02d}" for i in range(60)], index=int(now.strftime("%M")))
            sa = ap.selectbox("AM/PM", ["AM", "PM"], index=0 if now.strftime("%p")=="AM" else 1)
            dur = st.number_input("Hours", 0.5, 12.0, 1.0, 0.5)
            ctrl = st.number_input("Extra Controllers", 0, 3, 0) if any("PS" in s for s in sys_list) else 0

    if st.button("🚀 Start Session"):
        if name and sys_list:
            for s in sys_list:
                bill = get_price(SYSTEMS[s], dur, ctrl)
                conn.table("sales").insert({
                    "customer": name, "phone": phone, "system": s, "duration": dur, 
                    "total": bill, "method": "Pending", "entry_time": f"{sh}:{sm} {sa}", "status": "Active"
                }).execute()
            st.success("Session Deployed!")
            st.rerun()

# --- TAB 2: FLOOR ---
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
                if st.button("Confirm Add"):
                    extra_cost = get_price(SYSTEMS[row['system']], ext, 0)
                    conn.table("sales").update({"total": row['total'] + extra_cost, "duration": row['duration'] + ext}).eq("id", row['id']).execute()
                    st.rerun()
            else:
                pay = st.radio("Method", ["Cash", "Online / UPI"], horizontal=True)
                if st.button("Collect & Close"):
                    conn.table("sales").update({"status": "Completed", "method": pay}).eq("id", row['id']).execute()
                    st.balloons()
                    st.rerun()
        else:
            st.info("Floor is clear.")
    except: st.write("Syncing...")

# --- TAB 3: TODAY ---
with t3:
    try:
        raw = conn.table("sales").select("*").execute()
        df = pd.DataFrame(raw.data)
        if not df.empty:
            df['dt'] = pd.to_datetime(df['date']).dt.tz_convert('Asia/Kolkata')
            today = datetime.now(IST).date()
            t_df = df[df['dt'].dt.date == today]
            comp = t_df[t_df['status'] == 'Completed']
            m1, m2, m3 = st.columns(3)
            m1.metric("Cash Today", f"₹{comp[comp['method']=='Cash']['total'].sum():,.0f}")
            m2.metric("UPI Today", f"₹{comp[comp['method']!='Cash']['total'].sum():,.0f}")
            m3.metric("Running Bill", f"₹{t_df[t_df['status']=='Active']['total'].sum():,.0f}")
            st.dataframe(t_df.sort_values('dt', ascending=False), use_container_width=True, hide_index=True)
    except: st.info("No logs for today yet.")

# --- TAB 4: EXPORT (FIXED) ---
with t4:
    st.subheader("📊 Export Records")
    day_sel = st.date_input("Pick a Date", datetime.now(IST).date())
    
    # We fetch data directly here to avoid the "NoneType" error
    raw_export = conn.table("sales").select("*").execute()
    edf = pd.DataFrame(raw_export.data)
    
    if not edf.empty:
        edf['d'] = pd.to_datetime(edf['date']).dt.tz_convert('Asia/Kolkata').dt.date
        final_edf = edf[edf['d'] == day_sel]
        
        if not final_edf.empty:
            # NO NESTED BUTTONS - Download is ready instantly
            csv_data = final_edf.to_csv(index=False).encode('utf-8')
            st.download_button(
                label=f"💾 Download CSV for {day_sel}",
                data=csv_data,
                file_name=f"Gamerarena_{day_sel}.csv",
                mime="text/csv",
                use_container_width=True
            )
            st.dataframe(final_edf, hide_index=True)
        else:
            st.warning(f"No records found for {day_sel}.")

# --- TAB 5: VAULT ---
with t5:
    st.subheader("🔐 Owner Vault")
    if st.text_input("Master Passcode", type="password") == "Shreenad@0511":
        try:
            raw_v = conn.table("sales").select("*").execute()
            vdf = pd.DataFrame(raw_v.data)
            if not vdf.empty:
                vdf['dt'] = pd.to_datetime(vdf['date']).dt.tz_convert('Asia/Kolkata').dt.tz_localize(None)
                pdf = vdf[vdf['status'] == 'Completed'].copy()
                now = datetime.now(IST).replace(tzinfo=None)
                s_tw = (now - timedelta(days=now.weekday())).date()
                s_tm = now.date().replace(day=1)
                
                wtd = pdf[pdf['dt'].dt.date >= s_tw]
                mtd = pdf[pdf['dt'].dt.date >= s_tm]
                
                c1, c2 = st.columns(2)
                c1.markdown(f"<div class='metric-box'><h4>WTD (Mon-Sun)</h4><h2>₹{wtd['total'].sum():,.0f}</h2></div>", unsafe_allow_html=True)
                c2.markdown(f"<div class='metric-box'><h4>MTD ({now.strftime('%B')})</h4><h2>₹{mtd['total'].sum():,.0f}</h2></div>", unsafe_allow_html=True)
                
                st.divider()
                st.subheader("Hardware Performance")
                h_map = {"PC1":"PC","PC2":"PC","PS1":"Playstation 5","PS2":"Playstation 5","PS3":"Playstation 5","SIM1":"Racing Simulator"}
                pdf['Hardware'] = pdf['system'].map(h_map).fillna(pdf['system'])
                st.bar_chart(pdf.groupby('Hardware')['total'].sum())
        except: st.error("Data processing error.")

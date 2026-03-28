import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import datetime, timedelta
import pytz

# --- 1. PAGE CONFIG & STYLING ---
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

# --- 2. SECURE LOGIN ---
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

# --- 3. CORE LOGIC & PRICING ---
conn = st.connection("supabase", type=SupabaseConnection)
IST = pytz.timezone('Asia/Kolkata')

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

# --- 4. TABS ---
t1, t2, t3, t4, t5 = st.tabs(["📝 New Session", "🕹️ Active Floor", "📊 Live Stats", "📅 Daily Reports", "🧠 Owner Vault"])

# --- TAB 1: NEW ENTRY ---
with t1:
    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("👤 Gamer Profile")
            name = st.text_input("Name")
            phone = st.text_input("Phone")
            insta = st.text_input("Instagram")
        with c2:
            st.subheader("🕹️ Session Setup")
            selected = st.multiselect("Select Systems", list(SYSTEMS.keys()))
            st.write("Entry Time:")
            now = datetime.now(IST)
            h_col, m_col, a_col = st.columns(3)
            sh = h_col.selectbox("HH", [f"{i:02d}" for i in range(1, 13)], index=int(now.strftime("%I"))-1)
            sm = m_col.selectbox("MM", [f"{i:02d}" for i in range(60)], index=int(now.strftime("%M")))
            sa = a_col.selectbox("AM/PM", ["AM", "PM"], index=0 if now.strftime("%p")=="AM" else 1)
            dur = st.number_input("Duration (Hrs)", 0.5, 12.0, 1.0, 0.5)
            has_ps5 = any("PS" in s for s in selected)
            ctrl = st.number_input("Extra Controllers", 0, 3, 0) if has_ps5 else 0

    if st.button("🚀 Start Session", use_container_width=True):
        if not name or not selected:
            st.error("Missing Name or System Selection")
        else:
            try:
                for s in selected:
                    cat = SYSTEMS[s]
                    bill = calculate_price(cat, dur, ctrl)
                    t_str = f"{sh}:{sm} {sa}"
                    conn.table("sales").insert({
                        "customer": name, "phone": phone, "instagram": insta,
                        "system": s, "duration": dur, "total": bill, 
                        "method": "Pending", "entry_time": t_str, "status": "Active" 
                    }).execute()
                st.success(f"Deployed! Expected: ₹{bill}")
            except Exception as e:
                st.error(f"Error: {e}")

# --- TAB 2: ACTIVE FLOOR ---
with t2:
    st.subheader("🕹️ Live Operations")
    try:
        res = conn.table("sales").select("*").eq("status", "Active").execute()
        active = pd.DataFrame(res.data)
        if not active.empty:
            active['label'] = active['customer'] + " | " + active['system']
            sel = st.selectbox("Select Active Player", active['label'].tolist())
            row = active[active['label'] == sel].iloc[0]
            st.markdown(f"<div class='active-card'><b>{row['customer']}</b> on {row['system']}<br>Bill: ₹{row['total']} | Time: {row['entry_time']}</div>", unsafe_allow_html=True)
            
            mode = st.radio("Action", ["Extend Time", "Collect & End"])
            if mode == "Extend Time":
                ext = st.number_input("Add Hours", 0.5, 5.0, 0.5)
                if st.button("Update Bill"):
                    extra = calculate_price(SYSTEMS[row['system']], ext, 0)
                    conn.table("sales").update({"total": row['total'] + extra, "duration": row['duration'] + ext}).eq("id", row['id']).execute()
                    st.rerun()
            else:
                pay = st.radio("Payment", ["Cash", "Online / UPI"], horizontal=True)
                if st.button("Finish Session"):
                    conn.table("sales").update({"status": "Completed", "method": pay}).eq("id", row['id']).execute()
                    st.balloons()
                    st.rerun()
        else:
            st.info("No active sessions.")
    except:
        st.write("Connecting...")

# --- TAB 3: LIVE STATS ---
with t3:
    st.subheader("📈 Today's Performance")
    try:
        raw = conn.table("sales").select("*").execute()
        df = pd.DataFrame(raw.data)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date']).dt.tz_convert('Asia/Kolkata')
            today = datetime.now(IST).date()
            t_df = df[df['date'].dt.date == today]
            comp = t_df[t_df['status'] == 'Completed']
            act = t_df[t_df['status'] == 'Active']
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Collected", f"₹{comp['total'].sum():,.0f}")
            m2.metric("Cash", f"₹{comp[comp['method']=='Cash']['total'].sum():,.0f}")
            m3.metric("UPI", f"₹{comp[comp['method']!='Cash']['total'].sum():,.0f}")
            m4.metric("On Floor", f"₹{act['total'].sum():,.0f}")
            st.dataframe(t_df.sort_values('date', ascending=False), use_container_width=True, hide_index=True)
    except:
        st.write("Awaiting Data...")

# --- TAB 4: DAILY REPORTS ---
with t4:
    st.subheader("📅 Export Records")
    try:
        raw = conn.table("sales").select("*").execute()
        rdf = pd.DataFrame(raw.data)
        if not rdf.empty:
            day = st.date_input("Select Date", datetime.now(IST).date())
            rdf['date_only'] = pd.to_datetime(rdf['date']).dt.date
            edf = rdf[rdf['date_only'] == day]
            if not edf.empty:
                st.download_button("Download CSV", edf.to_csv(index=False).encode('utf-8'), f"Report_{day}.csv", "text/csv")
                st.dataframe(edf, hide_index=True)
    except:
        st.write("No data.")

# --- TAB 5: OWNER VAULT ---
with t5:
    st.subheader("🔐 Gamerarena Intelligence")
    if st.text_input("Master Key", type="password") == "Shreenad@0511":
        try:
            raw = conn.table("sales").select("*").execute()
            df = pd.DataFrame(raw.data)
            if not df.empty:
                df['date'] = pd.to_datetime(df['date']).dt.tz_convert('Asia/Kolkata').dt.tz_localize(None)
                pdf = df[df['status'] == 'Completed'].copy()
                now = datetime.now(IST).replace(tzinfo=None)
                
                # Logic
                s_tw = (now - timedelta(days=now.weekday())).date() # Mon
                s_lw, e_lw = s_tw - timedelta(days=7), s_tw - timedelta(days=1)
                s_tm, s_lm = now.date().replace(day=1), (now.date().replace(day=1) - timedelta(days=1)).replace(day=1)
                e_lm = now.date().replace(day=1) - timedelta(days=1)

                wtd = pdf[pdf['date'].dt.date >= s_tw]
                lw = pdf[(pdf['date'].dt.date >= s_lw) & (pdf['date'].dt.date <= e_lw)]
                mtd = pdf[pdf['date'].dt.date >= s_tm]
                lm = pdf[(pdf['date'].dt.date >= s_lm) & (pdf['date'].dt.date <= e_lm)]

                st.markdown("### 📊 Performance Metrics")
                a, b = st.columns(2)
                a.markdown(f"<div class='metric-box'><h4>WTD (Mon-Sun)</h4><h2>₹{wtd['total'].sum():,.0f}</h2></div>", unsafe_allow_html=True)
                a.markdown(f"<div class='metric-box'><h4>MTD ({now.strftime('%B')})</h4><h2>₹{mtd['total'].sum():,.0f}</h2></div>", unsafe_allow_html=True)
                b.markdown(f"<div class='metric-box'><h4>Last Week</h4><h2>₹{lw['total'].sum():,.0f}</h2></div>", unsafe_allow_html=True)
                b.markdown(f"<div class='metric-box'><h4>Last Month</h4><h2>₹{lm['total'].sum():,.0f}</h2></div>", unsafe_allow_html=True)

                st.divider()
                st.subheader("🖥️ Hardware Performance")
                h_map = {"PC1":"PC","PC2":"PC","PS1":"Playstation 5","PS2":"Playstation 5","PS3":"Playstation 5","SIM1":"Racing Simulator"}
                pdf['Sys_Name'] = pdf['system'].map(h_map).fillna(pdf['system'])
                hw = pdf.groupby('Sys_Name').agg(Revenue=('total','sum'), Hours=('duration','sum')).reset_index()
                st.bar_chart(hw.set_index('Sys_Name')['Revenue'])
                st.dataframe(hw, hide_index=True)
        except Exception as e:
            st.error(f"Error: {e}")

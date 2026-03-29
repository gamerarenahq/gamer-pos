# Staging App Setup
import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import datetime, timedelta
import pytz
from streamlit_autorefresh import st_autorefresh

# --- 1. CRM STYLE & CONFIG ---
st.set_page_config(page_title="Gamerarena CRM (Staging)", page_icon="🎮", layout="wide")

# Autorefresh the page every 60 seconds (60000 milliseconds) for live timers
st_autorefresh(interval=60000, limit=None, key="crm_refresh")

st.markdown("""
<style>
    /* Zoho-style clean dark CRM aesthetic */
    .block-container { padding-top: 1.5rem; }
    .stButton>button { background: #4F46E5; color: white; border-radius: 6px; width: 100%; font-weight: 600; border: none; }
    .stButton>button:hover { background: #4338CA; box-shadow: 0 4px 6px rgba(0,0,0,0.2); }
    .crm-card { background-color: #1E1E2D; padding: 20px; border-radius: 8px; border-left: 4px solid #4F46E5; margin-bottom: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .warning-card { background-color: #2D1E1E; padding: 20px; border-radius: 8px; border-left: 4px solid #EF4444; margin-bottom: 12px; animation: pulse 2s infinite; }
    .overdue-card { background-color: #2D1E1E; padding: 20px; border-radius: 8px; border-left: 4px solid #B91C1C; margin-bottom: 12px; border: 1px solid #EF4444; }
    .metric-box { background-color: #1E1E2D; padding: 20px; border-radius: 8px; text-align: center; border: 1px solid #2B2B40; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); } 70% { box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); } 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); } }
</style>
""", unsafe_allow_html=True)

# --- 2. AUTHENTICATION ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔒 Gamerarena Staging Login")
    pwd = st.text_input("Enter Passcode", type="password")
    if st.button("Login"):
        if pwd == "Admin@2026":
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Invalid Code")
    st.stop()

# --- 3. DATABASE (STAGING ONLY) ---
try:
    conn = st.connection("supabase", type=SupabaseConnection)
except:
    st.error("Connection Error.")
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
t1, t2, t3, t4, t5 = st.tabs(["🕹️ Active Floor", "📝 New Session", "📊 Daily Summary", "📅 Reports Range", "🧠 Intelligence Vault"])

# --- TAB 1: ACTIVE FLOOR (WITH REAL-TIME TIMERS) ---
with t1:
    st.subheader("🕹️ Live Operations Monitor")
    try:
        # POINTING TO SALES_STAGING
        res = conn.table("sales_staging").select("*").eq("status", "Active").execute()
        active_df = pd.DataFrame(res.data)
        
        if not active_df.empty:
            now_ist = datetime.now(IST)
            
            for index, row in active_df.iterrows():
                # Timer Math Logic
                db_date = pd.to_datetime(row['date']).tz_convert(IST).strftime('%Y-%m-%d')
                entry_dt_str = f"{db_date} {row['entry_time']}"
                try:
                    entry_dt = IST.localize(datetime.strptime(entry_dt_str, '%Y-%m-%d %I:%M %p'))
                    end_dt = entry_dt + timedelta(hours=row['duration'])
                    time_left = (end_dt - now_ist).total_seconds() / 60.0 # in minutes
                except:
                    time_left = 999 # Fallback if time format is broken

                # Card Styling based on time remaining
                if time_left < 0:
                    card_class = "overdue-card"
                    status_text = f"🚨 OVERDUE BY {abs(int(time_left))} MINS"
                elif time_left <= 5:
                    card_class = "warning-card"
                    status_text = f"⚠️ TIME ALMOST UP ({int(time_left)} mins left)"
                    st.toast(f"Time almost up for {row['customer']} on {row['system']}!", icon="⚠️")
                else:
                    card_class = "crm-card"
                    status_text = f"⏳ {int(time_left)} mins remaining"

                st.markdown(f"""
                <div class='{card_class}'>
                    <h4 style='margin:0; color:#E0E7FF;'>{row['system']} | {row['customer']}</h4>
                    <p style='margin:5px 0 0 0; color:#9CA3AF;'>
                        Time In: {row['entry_time']} | Hours: {row['duration']} | Bill: ₹{row['total']}<br>
                        <b style='color:#FCD34D;'>{status_text}</b>
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
            st.divider()
            st.write("### Manage Floor")
            active_df['label'] = active_df['customer'] + " | " + active_df['system']
            sel = st.selectbox("Select Player to Manage", active_df['label'].tolist())
            row = active_df[active_df['label'] == sel].iloc[0]
            
            col_a, col_b = st.columns(2)
            with col_a:
                ext = st.number_input("Add Extra Hours", 0.5, 5.0, 0.5)
                if st.button("➕ Extend Time"):
                    extra_cost = get_price(SYSTEMS[row['system']], ext, 0)
                    conn.table("sales_staging").update({"total": row['total'] + extra_cost, "duration": row['duration'] + ext}).eq("id", row['id']).execute()
                    st.rerun()
            with col_b:
                pay = st.radio("Payment Method", ["Cash", "Online / UPI"], horizontal=True)
                if st.button("🛑 Collect & Close Session"):
                    conn.table("sales_staging").update({"status": "Completed", "method": pay}).eq("id", row['id']).execute()
                    st.balloons(); st.rerun()
        else:
            st.info("Floor is completely clear. Ready for players.")
    except Exception as e: 
        st.write(f"Connecting to staging... {e}")

# --- TAB 2: NEW ENTRY ---
with t2:
    with st.container(border=True):
        st.subheader("📝 Open New Session")
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Gamer Name")
            phone = st.text_input("Phone (Optional)")
            insta = st.text_input("Instagram (Optional)")
        with c2:
            sys_list = st.multiselect("Assign Hardware", list(SYSTEMS.keys()))
            now = datetime.now(IST)
            h, m, ap = st.columns(3)
            sh = h.selectbox("HH", [f"{i:02d}" for i in range(1, 13)], index=int(now.strftime("%I"))-1)
            sm = m.selectbox("MM", [f"{i:02d}" for i in range(60)], index=int(now.strftime("%M")))
            sa = ap.selectbox("AM/PM", ["AM", "PM"], index=0 if now.strftime("%p")=="AM" else 1)
            dur = st.number_input("Duration (Hours)", 0.5, 12.0, 1.0, 0.5)
            ctrl = st.number_input("Extra Controllers", 0, 3, 0) if any("PS" in s for s in sys_list) else 0

    if st.button("🚀 Deploy Session(s)"):
        if name and sys_list:
            try:
                for s in sys_list:
                    bill = get_price(SYSTEMS[s], dur, ctrl)
                    conn.table("sales_staging").insert({
                        "customer": name, "phone": phone, "instagram": insta, "system": s, 
                        "duration": dur, "total": bill, "method": "Pending", 
                        "entry_time": f"{sh}:{sm} {sa}", "status": "Active"
                    }).execute()
                st.success("Session pushed to Floor successfully!")
            except Exception as e:
                st.error(f"Save Error: {e}")

# --- TAB 3: DAILY SUMMARY ---
with t3:
    st.subheader("📊 Today's Snapshot")
    try:
        raw = conn.table("sales_staging").select("*").execute()
        df = pd.DataFrame(raw.data)
        if not df.empty:
            df['date_dt'] = pd.to_datetime(df['date'], utc=True).dt.tz_convert('Asia/Kolkata')
            today_date = datetime.now(IST).date()
            t_df = df[df['date_dt'].dt.date == today_date]
            
            comp = t_df[t_df['status'] == 'Completed']
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Cash Collected", f"₹{comp[comp['method']=='Cash']['total'].sum():,.0f}")
            m2.metric("UPI Collected", f"₹{comp[comp['method']!='Cash']['total'].sum():,.0f}")
            m3.metric("Total Revenue", f"₹{comp['total'].sum():,.0f}")
            m4.metric("Pending on Floor", f"₹{t_df[t_df['status']=='Active']['total'].sum():,.0f}")
            st.divider()
            st.dataframe(t_df.sort_values('date_dt', ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("No staging data for today.")
    except: st.error("Awaiting staging data.")

# --- TAB 4: REPORTS & EXPORTS (DATE RANGE) ---
with t4:
    st.subheader("📅 Deep Filter Reports")
    date_range = st.date_input("Select Date Range (Start - End)", [datetime.now(IST).date(), datetime.now(IST).date()])
    
    try:
        if len(date_range) == 2:
            start_date, end_date = date_range
            raw_e = conn.table("sales_staging").select("*").execute()
            edf = pd.DataFrame(raw_e.data)
            
            if not edf.empty:
                edf['d_str'] = pd.to_datetime(edf['date']).dt.tz_convert('Asia/Kolkata').dt.date
                final_edf = edf[(edf['d_str'] >= start_date) & (edf['d_str'] <= end_date)]
                
                if not final_edf.empty:
                    st.success(f"Found {len(final_edf)} sessions between {start_date} and {end_date}.")
                    st.download_button("📥 Export Range to CSV", final_edf.to_csv(index=False).encode('utf-8'), f"Gamerarena_{start_date}_to_{end_date}.csv", "text/csv")
                    st.dataframe(final_edf, hide_index=True)
                else:
                    st.warning("No records in this range.")
    except: st.info("Select a valid start and end date.")

# --- TAB 5: VAULT ---
with t5:
    st.subheader("🔐 Intelligence Vault")
    if st.text_input("Master Key", type="password") == "Shreenad@0511":
        try:
            raw_v = conn.table("sales_staging").select("*").execute()
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
                c1.markdown(f"<div class='metric-box'><h4>WTD Revenue</h4><h2 style='color:#34D399;'>₹{wtd['total'].sum():,.0f}</h2></div>", unsafe_allow_html=True)
                c2.markdown(f"<div class='metric-box'><h4>MTD Revenue</h4><h2 style='color:#34D399;'>₹{mtd['total'].sum():,.0f}</h2></div>", unsafe_allow_html=True)
                
                st.divider()
                st.write("### Lifetime Hardware Utilization")
                h_map = {"PC1":"PC","PC2":"PC","PS1":"Playstation 5","PS2":"Playstation 5","PS3":"Playstation 5","SIM1":"Racing Simulator"}
                pdf['Hardware'] = pdf['system'].map(h_map).fillna(pdf['system'])
                st.bar_chart(pdf.groupby('Hardware')['total'].sum(), color="#4F46E5")
        except: st.error("Vault processing error.")

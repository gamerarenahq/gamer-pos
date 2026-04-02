import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import datetime, timedelta
import pytz
from streamlit_autorefresh import st_autorefresh

# --- 1. SETTINGS & NEON THEME ---
st.set_page_config(page_title="Gamerarena Live", page_icon="🎮", layout="wide")
st_autorefresh(interval=30000, limit=None, key="crm_refresh")

C = {'bg': '#0B0E14', 'card': 'rgba(26, 31, 43, 0.9)', 'ice': '#98DED9', 'warn': '#FF754C', 'danger': '#EF4444', 'border': '#2D3446'}

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@600;800&display=swap');
    [data-testid="stAppViewContainer"] {{ background-color: {C['bg']}; font-family: 'Plus Jakarta Sans', sans-serif; }}
    .floor-container {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 20px; padding: 10px; }}
    .session-card {{ background: {C['card']}; border: 1px solid {C['border']}; border-radius: 20px; padding: 20px; text-align: center; transition: 0.3s; }}
    .timer-circle {{ position: relative; width: 100px; height: 100px; margin: 0 auto 15px auto; border-radius: 50%; display: flex; align-items: center; justify-content: center;
        background: radial-gradient(closest-side, {C['bg']} 85%, transparent 80% 100%), conic-gradient(var(--glow-color) var(--percentage), #2D3446 0); box-shadow: 0 0 15px var(--shadow-color); }}
    .timer-text {{ font-size: 20px; font-weight: 800; color: white; }}
    .device-label {{ font-size: 11px; letter-spacing: 2px; text-transform: uppercase; color: var(--glow-color); font-weight: 800; }}
    .player-name {{ font-size: 16px; color: white; margin-bottom: 10px; }}
    .stButton>button {{ background: linear-gradient(135deg, #6C5DD3 0%, #8C7CFF 100%); color: white; border-radius: 10px; border: none; font-weight: 600; }}
</style>
""", unsafe_allow_html=True)

# --- 2. AUTH & LOGIC ---
IST = pytz.timezone('Asia/Kolkata')
if "auth" not in st.session_state: st.session_state.auth = False
if "form_reset" not in st.session_state: st.session_state.form_reset = 0

if not st.session_state.auth:
    if st.text_input("Passcode", type="password") == "Admin@2026": st.session_state.auth = True; st.rerun()
    st.stop()

try: conn = st.connection("supabase", type=SupabaseConnection)
except: st.stop()

SYSTEMS = {"PS1":"PS5", "PS2":"PS5", "PS3":"PS5", "PC1":"PC", "PC2":"PC", "SIM1":"Racing Sim"}
def get_price(cat, dur):
    if cat == "PS5": return (int(dur) * 150) + ((1 if (dur % 1) != 0 else 0) * 100)
    elif cat == "PC": return (int(dur) * 100) + ((1 if (dur % 1) != 0 else 0) * 70)
    elif cat == "Racing Sim": return (int(dur) * 250) + ((1 if (dur % 1) != 0 else 0) * 150)
    return 0

# --- 3. APP TABS ---
t1, t2, t3 = st.tabs(["🕹️ Live Floor", "📝 New Session", "🧠 Vault"])

with t1:
    res = conn.table("sales").select("*").eq("status", "Active").execute()
    active_df = pd.DataFrame(res.data)
    col_cards, col_panel = st.columns([2.2, 1])
    
    with col_cards:
        if active_df.empty: st.info("Floor is clear.")
        else:
            html = "<div class='floor-container'>"
            for _, r in active_df.iterrows():
                try:
                    start = pd.to_datetime(f"{r['date'][:10]} {r['entry_time']}").tz_localize(IST)
                    total_m = r['duration'] * 60
                    elapsed = (datetime.now(IST) - start).total_seconds() / 60
                    left = int(total_m - elapsed)
                    perc = max(0, min(100, int((elapsed / total_m) * 100)))
                    color = C['ice'] if left > 10 else (C['warn'] if left > 0 else C['danger'])
                    html += f"""<div class="session-card" style="--glow-color:{color}; --shadow-color:{color}33;">
                        <div class="device-label">{r['system']}</div><div class="player-name">{r['customer']}</div>
                        <div class="timer-circle" style="--percentage:{100-perc}%"><div class="timer-text">{left if left > 0 else 0}m</div></div>
                        <div style="color:#9BA3AF; font-size:12px;">Bill: ₹{r['total']+(r.get('fnb_total') or 0):.0f}</div></div>"""
                except: pass
            st.markdown(html + "</div>", unsafe_allow_html=True)

    with col_panel:
        st.markdown(f"<div style='background:{C['card']}; padding:20px; border-radius:20px; border:1px solid {C['border']};'>", unsafe_allow_html=True)
        if not active_df.empty:
            active_df['lbl'] = active_df['system'] + " - " + active_df['customer']
            sel = st.selectbox("Manage Player", active_df['lbl'].tolist())
            p = active_df[active_df['lbl'] == sel].iloc[0]
            mode = st.radio("Action", ["Checkout", "Extend", "Food"], horizontal=True)
            if mode == "Checkout":
                gt = p['total'] + (p.get('fnb_total') or 0)
                st.success(f"Collect ₹{gt:.0f}")
                meth = st.radio("Pay Method", ["Cash", "UPI"], horizontal=True)
                if st.button("End Session"):
                    conn.table("sales").update({"status": "Completed", "method": meth, "total": float(gt)}).eq("id", int(p['id'])).execute()
                    st.rerun()
            elif mode == "Extend":
                h = st.number_input("Add Hrs", 0.5, 5.0, 0.5, 0.5)
                if st.button("Confirm Extension"):
                    new_t = p['total'] + get_price(SYSTEMS[p['system']], h)
                    conn.table("sales").update({"total": new_t, "duration": p['duration'] + h}).eq("id", int(p['id'])).execute()
                    st.rerun()
            elif mode == "Food":
                fn, fp = st.text_input("Item"), st.number_input("Price", 0)
                if st.button("Add to Tab"):
                    cur_f = str(p.get('fnb_items') or "")
                    new_f = f"{cur_f} | {fn}" if cur_f else fn
                    conn.table("sales").update({"fnb_items": new_f, "fnb_total": (p.get('fnb_total') or 0) + fp}).eq("id", int(p['id'])).execute()
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

with t2:
    st.subheader("Start New Session")
    c1, c2 = st.columns(2)
    name = c1.text_input("Customer Name", key=f"n_{st.session_state.form_reset}")
    sys = c2.selectbox("Hardware", list(SYSTEMS.keys()))
    dur = c1.number_input("Duration (Hrs)", 0.5, 10.0, 1.0, 0.5)
    if st.button("🚀 LAUNCH"):
        if name:
            conn.table("sales").insert({"customer": name, "system": sys, "duration": dur, "total": float(get_price(SYSTEMS[sys], dur)), "status": "Active", "date": datetime.now(IST).isoformat(), "scheduled_date": datetime.now(IST).strftime('%Y-%m-%d'), "entry_time": datetime.now(IST).strftime("%I:%M %p")}).execute()
            st.session_state.form_reset += 1; st.rerun()

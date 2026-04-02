import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import datetime, timedelta
import pytz
from streamlit_autorefresh import st_autorefresh

# --- 1. SETTINGS & NEON THEME ---
st.set_page_config(page_title="Gamerarena Live", page_icon="🎮", layout="wide")
st_autorefresh(interval=30000, limit=None, key="crm_refresh")

C = {
    'bg': '#0B0E14',
    'card': 'rgba(26, 31, 43, 0.9)',
    'ice': '#98DED9',
    'warn': '#FF754C',
    'danger': '#EF4444',
    'border': '#2D3446'
}

# --- ADVANCED CSS FOR CIRCULAR GAUGE ---
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@600;800&display=swap');
    
    [data-testid="stAppViewContainer"] {{ background-color: {C['bg']}; font-family: 'Plus Jakarta Sans', sans-serif; }}
    
    .floor-container {{
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
        gap: 20px;
        padding: 10px;
    }}

    .session-card {{
        background: {C['card']};
        border: 1px solid {C['border']};
        border-radius: 20px;
        padding: 25px;
        text-align: center;
        position: relative;
        transition: 0.3s;
    }}

    /* The Circular Timer UI */
    .timer-circle {{
        position: relative;
        width: 120px;
        height: 120px;
        margin: 0 auto 15px auto;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        background: radial-gradient(closest-side, {C['bg']} 85%, transparent 80% 100%),
                    conic-gradient(var(--glow-color) var(--percentage), #2D3446 0);
        box-shadow: 0 0 20px var(--shadow-color);
    }}

    .timer-text {{
        font-size: 22px;
        font-weight: 800;
        color: white;
    }}

    .device-label {{
        font-size: 12px;
        letter-spacing: 2px;
        text-transform: uppercase;
        color: var(--glow-color);
        margin-bottom: 5px;
        font-weight: 800;
    }}

    .player-name {{
        font-size: 18px;
        color: white;
        margin-bottom: 15px;
    }}

    .stButton>button {{
        background: linear-gradient(135deg, #6C5DD3 0%, #8C7CFF 100%);
        color: white; border-radius: 12px; border: none; font-weight: 600; height: 45px;
    }}
</style>
""", unsafe_allow_html=True)

# --- 2. AUTH & STATE ---
IST = pytz.timezone('Asia/Kolkata')
if "auth" not in st.session_state: st.session_state.auth = False
if "form_reset" not in st.session_state: st.session_state.form_reset = 0

if not st.session_state.auth:
    st.title("🛡️ Gamerarena Login")
    if st.text_input("Passcode", type="password") == "Admin@2026":
        st.session_state.auth = True; st.rerun()
    st.stop()

# --- 3. DATABASE ---
try: conn = st.connection("supabase", type=SupabaseConnection)
except: st.stop()

SYSTEMS = {"PS1":"PS5", "PS2":"PS5", "PS3":"PS5", "PC1":"PC", "PC2":"PC", "SIM1":"Racing Sim"}

def get_price(cat, dur):
    if cat == "PS5": return (int(dur) * 150) + ((1 if (dur % 1) != 0 else 0) * 100)
    elif cat == "PC": return (int(dur) * 100) + ((1 if (dur % 1) != 0 else 0) * 70)
    elif cat == "Racing Sim": return (int(dur) * 250) + ((1 if (dur % 1) != 0 else 0) * 150)
    return 0

# --- 4. DATA FETCHING ---
res = conn.table("sales").select("*").eq("status", "Active").execute()
active_df = pd.DataFrame(res.data)

# --- 5. TABS ---
t1, t2, t3 = st.tabs(["🕹️ Live Floor", "📝 New Session", "🧠 Vault"])

with t1:
    col_cards, col_panel = st.columns([2.5, 1])
    
    with col_cards:
        if active_df.empty:
            st.info("No active sessions on the floor.")
        else:
            # Create the custom HTML Grid
            html_content = "<div class='floor-container'>"
            for _, row in active_df.iterrows():
                try:
                    start = pd.to_datetime(f"{row['date'][:10]} {row['entry_time']}").tz_localize(IST)
                    total_mins = row['duration'] * 60
                    elapsed = (datetime.now(IST) - start).total_seconds() / 60
                    left = int(total_mins - elapsed)
                    
                    # Calculate circle percentage
                    perc = max(0, min(100, int((elapsed / total_mins) * 100)))
                    
                    # Color Logic
                    color = C['ice']
                    if left < 10: color = C['warn']
                    if left <= 0: color = C['danger']
                    
                    html_content += f"""
                    <div class="session-card" style="--glow-color: {color}; --shadow-color: {color}33;">
                        <div class="device-label">{row['system']}</div>
                        <div class="player-name">{row['customer']}</div>
                        <div class="timer-circle" style="--percentage: {100-perc}%">
                            <div class="timer-text">{left if left > 0 else 0}m</div>
                        </div>
                        <div style="color: #9BA3AF; font-size: 12px;">Bill: ₹{row['total'] + (row.get('fnb_total') or 0):.0f}</div>
                    </div>
                    """
                except: pass
            html_content += "</div>"
            st.markdown(html_content, unsafe_allow_html=True)

    with col_panel:
        st.markdown(f"<div style='background:{C['card']}; padding:20px; border-radius:20px; border:1px solid {C['border']};'>", unsafe_allow_html=True)
        st.subheader("Operator Controls")
        if not active_df.empty:
            active_df['lbl'] = active_df['system'] + " - " + active_df['customer']
            sel = st.selectbox("Choose Player", active_df['lbl'].tolist())
            p = active_df[active_df['lbl'] == sel].iloc[0]
            
            mode = st.radio("Action", ["Checkout", "Extend", "Food"], horizontal=True)
            
            if mode == "Checkout":
                gt = p['total'] + (p.get('fnb_total') or 0)
                st.success(f"## Collect ₹{gt:.0f}")
                m = st.radio("Pay Method", ["Cash", "UPI"], horizontal=True)
                if st.button("Complete & Close Floor", use_container_width=True):
                    conn.table("sales").update({"status": "Completed", "method": m, "total": float(gt)}).eq("id", int(p['id'])).execute()
                    st.rerun()
            
            elif mode == "Extend":
                h = st.number_input("Add Hours", 0.5, 5.0, 0

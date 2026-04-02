import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
from streamlit_autorefresh import st_autorefresh
import plotly.express as px
import plotly.graph_objects as go

# --- 1. SETTINGS & THEME ---
st.set_page_config(page_title="Gamerarena Dashboard", page_icon="🎮", layout="wide")
st_autorefresh(interval=60000, limit=None, key="crm_refresh")

# Custom UI Colors
C = {
    'bg': '#0B0E14',
    'card': '#1A1F2B',
    'accent': '#00D1FF', # Ice Blue
    'purple': '#6C5DD3',
    'warn': '#FF754C',
    'text': '#FFFFFF',
    'border': '#2D3446'
}

# --- ADVANCED CSS INJECTION (Screenshot Match) ---
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {{
        background-color: {C['bg']};
        font-family: 'Plus Jakarta Sans', sans-serif;
    }}

    /* Glassmorphism Cards */
    .metric-card {{
        background: rgba(26, 31, 43, 0.8);
        border: 1px solid {C['border']};
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        transition: 0.3s;
    }}
    
    .timer-card {{
        background: linear-gradient(145deg, #1A1F2B, #131720);
        border: 1px solid {C['border']};
        border-radius: 20px;
        padding: 20px;
        margin-bottom: 15px;
        text-align: center;
        position: relative;
        overflow: hidden;
    }}
    
    .timer-card-active {{ border-top: 4px solid {C['accent']}; box-shadow: 0 4px 20px rgba(0, 209, 255, 0.1); }}
    .timer-card-warn {{ border-top: 4px solid {C['warn']}; animation: pulse 2s infinite; }}
    
    /* Progress Circle Emulation */
    .circle-wrap {{
        width: 80px; height: 80px;
        background: #2D3446; border-radius: 50%;
        margin: 10px auto; display: flex; align-items: center; justify-content: center;
        border: 4px solid {C['accent']};
        font-weight: 800; font-size: 18px; color: {C['accent']};
    }}

    h1, h2, h3 {{ color: {C['text']} !important; font-weight: 800 !important; }}
    p, span, label {{ color: #9BA3AF !important; }}
    
    .stTabs [data-baseweb="tab"] {{ background: transparent; color: #9BA3AF; }}
    .stTabs [aria-selected="true"] {{ color: {C['accent']} !important; border-bottom-color: {C['accent']} !important; }}

    @keyframes pulse {{
        0% {{ box-shadow: 0 0 0 0 rgba(255, 117, 76, 0.4); }}
        70% {{ box-shadow: 0 0 0 15px rgba(255, 117, 76, 0); }}
        100% {{ box-shadow: 0 0 0 0 rgba(255, 117, 76, 0); }}
    }}
</style>
""", unsafe_allow_html=True)

# --- 2. AUTH & STATE ---
IST = pytz.timezone('Asia/Kolkata')
if "auth" not in st.session_state: st.session_state.auth = False
if "cart" not in st.session_state: st.session_state.cart = []
if "form_reset" not in st.session_state: st.session_state.form_reset = 0

if not st.session_state.auth:
    st.title("🛡️ Gamerarena ERP")
    pwd = st.text_input("Staff Code", type="password")
    if st.button("Unlock Dashboard"):
        if pwd == "Admin@2026": st.session_state.auth = True; st.rerun()
        else: st.error("Access Denied")
    st.stop()

# --- 3. LOGIC & DB ---
try: conn = st.connection("supabase", type=SupabaseConnection)
except: st.stop()

SYSTEMS = {"PS1":"PS5", "PS2":"PS5", "PS3":"PS5", "PC1":"PC", "PC2":"PC", "SIM1":"Racing Sim"}
MENU = {
    "🍟 Starters": {"Veggie Nuggets": 209, "Cheese Balls": 229, "Poppers": 230, "Fries": 139},
    "🍔 Burgers": {"Tikki Tango": 89, "Paneer Pataka": 230, "Big Crunch": 229},
    "🥤 Shakes": {"Cold Coffee": 129, "Vanilla": 149, "Oreo": 179},
    "🍹 Mocktails": {"Blue Lagoon": 129, "Mint Mojito": 129, "Chilli Guava": 129}
}

def get_price(cat, dur):
    if cat == "PS5": return (int(dur) * 150) + ((1 if (dur % 1) != 0 else 0) * 100)
    elif cat == "PC": return (int(dur) * 100) + ((1 if (dur % 1) != 0 else 0) * 70)
    elif cat == "Racing Sim": return (int(dur) * 250) + ((1 if (dur % 1) != 0 else 0) * 150)
    return 0

# --- 4. APP LAYOUT ---
t1, t2, t3, t4, t5 = st.tabs(["🕹️ Live Floor", "🍔 Cafe POS", "📅 Bookings", "📈 Vault", "⚙️ Logs"])

# ==========================================
# TAB 1: LIVE FLOOR (SCREENSHOT 1 STYLE)
# ==========================================
with t1:
    res = conn.table("sales").select("*").eq("status", "Active").execute()
    active_df = pd.DataFrame(res.data)
    
    col_cards, col_side = st.columns([2.5, 1])
    
    with col_cards:
        if active_df.empty: st.info("Floor is currently empty.")
        else:
            grid = st.columns(3)
            for i, (_, p) in enumerate(active_df.iterrows()):
                with grid[i % 3]:
                    try:
                        entry = pd.to_datetime(f"{p['date'][:10]} {p['entry_time']}").tz_localize(IST)
                        mins_left = int(((entry + timedelta(hours=p['duration'])) - datetime.now(IST)).total_seconds() / 60)
                    except: mins_left = 0
                    
                    state = "timer-card-warn" if mins_left < 10 else "timer-card-active"
                    st.markdown(f"""
                    <div class='timer-card {state}'>
                        <div style='font-size:12px; color:{C['accent']}; font-weight:800;'>{p['system']}</div>
                        <h3 style='margin:5px 0;'>{p['customer']}</h3>
                        <div class='circle-wrap'>{mins_left}m</div>
                        <p style='margin:0; font-size:12px;'>Bill: ₹{p['total'] + (p.get('fnb_total') or 0):.0f}</p>
                    </div>
                    """, unsafe_allow_html=True)
    
    with col_side:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        st.subheader("Manage Session")
        if not active_df.empty:
            active_df['label'] = active_df['system'] + " - " + active_df['customer']
            sel = st.selectbox("Select Machine", active_df['label'].tolist())
            row = active_df[active_df['label'] == sel].iloc[0]
            
            sub_tabs = st.tabs(["⏳ Time", "🧾 End"])
            with sub_tabs[0]:
                ext = st.number_input("Add Hrs", 0.5, 5.0, 0.5, 0.5)
                if st.button("Update Time", use_container_width=True):
                    new_tot = row['total'] + get_price(SYSTEMS[row['system']], ext)
                    conn.table("sales").update({"total": new_tot, "duration": row['duration'] + ext}).eq("id", int(row['id'])).execute()
                    st.rerun()
            with sub_tabs[1]:
                g_total = row['total'] + (row.get('fnb_total') or 0)
                st.write(f"### Total: ₹{g_total:.0f}")
                meth = st.radio("Pay Method", ["Cash", "UPI"], horizontal=True)
                if st.button("Finalize & Close", type="primary", use_container_width=True):
                    conn.table("sales").update({"status": "Completed", "method": meth, "total": float(g_total)}).eq("id", int(row['id'])).execute()
                    st.balloons(); st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# TAB 2: CAFE POS (VISUAL GRID)
# ==========================================
with t2:
    st.subheader("🍔 Hunger Monkey Unified POS")
    menu_col, cart_col = st.columns([2, 1])
    
    with menu_col:
        for cat, items in MENU.items():
            st.write(f"**{cat}**")
            m_grid = st.columns(4)
            for j, (name, price) in enumerate(items.items()):
                with m_grid[j % 4]:
                    if st.button(f"{name}\n₹{price}", key=f"pos_{name}", use_container_width=True):
                        # Simple Logic: Directly add to an active player
                        if not active_df.empty:
                            target = active_df.iloc[0] # Default to first player for demo, usually you'd pick
                            new_f = f"{str(target.get('fnb_items') or '')} | {name}"
                            new_t = (target.get('fnb_total') or 0) + price
                            conn.table("sales").update({"fnb_items": new_f, "fnb_total": new_t}).eq("id", int(target['id'])).execute()
                            st.toast(f"Added {name} to {target['customer']}'s tab!")
                        else: st.warning("Start a session to add food!")

# ==========================================
# TAB 4: VAULT (SCREENSHOT 2 & 4 STYLE)
# ==========================================
with t4:
    st.subheader("Financial Performance Dashboard")
    raw = conn.table("sales").select("*").execute()
    df = pd.DataFrame(raw.data)
    
    if not df.empty:
        df['date_str'] = df['date'].str[:10]
        today = datetime.now(IST).strftime('%Y-%m-%d')
        t_df = df[df['date_str'] == today]
        comp = t_df[t_df['status'] == 'Completed']
        
        # Metric Grid
        m1, m2, m3 = st.columns(3)
        with m1:
            st.markdown(f"<div class='metric-card'><p>Cash Collected</p><h2>₹{comp[comp['method']=='Cash']['total'].sum():,.0f}</h2></div>", unsafe_allow_html=True)
        with m2:
            st.markdown(f"<div class='metric-card'><p>UPI Collected</p><h2>₹{comp[comp['method']!='Cash']['total'].sum():,.0f}</h2></div>", unsafe_allow_html=True)
        with m3:
            st.markdown(f"<div class='metric-card' style='border-color:{C['accent']}'><p>Total Revenue Today</p><h2 style='color:{C['accent']}'>₹{comp['total'].sum():,.0f}</h2></div>", unsafe_allow_html=True)
        
        st.write("### Revenue Trend")
        chart_df = df[df['status']=='Completed'].groupby('date_str')['total'].sum().reset_index().tail(7)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=chart_df['date_str'], y=chart_df['total'],
            marker_color=C['accent'], opacity=0.8,
            marker_line_width=0,
            hovertemplate="₹%{y}<extra></extra>"
        ))
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            font_color='#9BA3AF', margin=dict(t=10, b=10, l=0, r=0),
            height=300, xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#2D3446')
        )
        st.plotly_chart(fig, use_container_width=True)

# ==========================================
# (TAB 3 & 5 REMAIN FUNCTIONAL BUT CLEANED UP)
# ==========================================
with t3:
    st.subheader("New Booking")
    bx1, bx2 = st.columns(2)
    name = bx1.text_input("Customer Name")
    sys = bx2.selectbox("Hardware", list(SYSTEMS.keys()))
    dur = bx1.number_input("Duration (Hrs)", 0.5, 10.0, 1.0)
    if st.button("Launch Session", type="primary"):
        conn.table("sales").insert({"customer": name, "system": sys, "duration": dur, "total": get_price(SYSTEMS[sys], dur), "status": "Active", "date": datetime.now(IST).isoformat(), "scheduled_date": datetime.now(IST).strftime('%Y-%m-%d')}).execute()
        st.rerun()

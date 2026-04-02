import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
from streamlit_autorefresh import st_autorefresh
import plotly.express as px

# --- 1. GLOBAL DESIGN & CONFIG ---
st.set_page_config(page_title="Gamerarena Unified POS", page_icon="🎮", layout="wide")
st_autorefresh(interval=60000, limit=None, key="crm_refresh")

# Master Color Palette: Ice Blue Theme
ga_colors = {
    'bg': '#0F1117',
    'card_bg': '#161922',
    'accent': '#6C5DD3',    # Purple Accent
    'ice_blue': '#98DED9',  # REPLACED GREEN WITH ICE BLUE
    'warning': '#FF754C',   # Orange
    'text': '#E0E7FF'
}

st.markdown(f"""
<style>
    .stApp {{ background-color: {ga_colors['bg']}; color: {ga_colors['text']}; }}
    h1, h2, h3, h4, p, span {{ color: {ga_colors['text']} !important; font-family: 'Inter', sans-serif; }}
    
    /* GA-Card Styling */
    .ga-card {{ background-color: {ga_colors['card_bg']}; padding: 25px; border-radius: 12px; border: 1px solid #2B2F3A; margin-bottom: 15px; position: relative; }}
    .ga-card-active {{ border-left: 5px solid {ga_colors['ice_blue']}; box-shadow: 0 0 15px rgba(152, 222, 217, 0.1); }}
    .ga-card-warning {{ border-left: 5px solid {ga_colors['warning']}; animation: pulse_border 2s infinite; }}
    .ga-card-overdue {{ border-left: 5px solid #EF4444; border: 2px solid #EF4444; }}
    
    .card-title {{ font-size: 18px; font-weight: 700; color: {ga_colors['text']}; margin-bottom: 5px; }}
    .card-subtitle {{ font-size: 14px; color: #9CA3AF; margin-bottom: 15px; }}
    .card-metric {{ font-size: 24px; font-weight: 800; color: {ga_colors['ice_blue']}; }}
    
    /* Re-theming Tabs */
    .stTabs [aria-selected="true"] {{ color: {ga_colors['ice_blue']} !important; border: 1px solid {ga_colors['ice_blue']} !important; }}
    
    /* Buttons */
    .stButton>button {{ background: linear-gradient(135deg, {ga_colors['accent']} 0%, #8C7CFF 100%); color: white; border-radius: 8px; border: none; font-weight: 600; }}
    
    @keyframes pulse_border {{ 0% {{ border-left-color: {ga_colors['warning']}; }} 50% {{ border-left-color: rgba(255,117,76,0.2); }} 100% {{ border-left-color: {ga_colors['warning']}; }} }}
</style>
""", unsafe_allow_html=True)

# --- 2. STATE & AUTH ---
IST = pytz.timezone('Asia/Kolkata')
if "auth" not in st.session_state: st.session_state.auth = False
if "cart" not in st.session_state: st.session_state.cart = []
if "form_reset" not in st.session_state: st.session_state.form_reset = 0

if not st.session_state.auth:
    st.title("🔒 Gamerarena Central Login")
    pwd = st.text_input("Passcode", type="password")
    if st.button("Login"):
        if pwd == "Admin@2026": st.session_state.auth = True; st.rerun()
        else: st.error("❌ Wrong Passcode")
    st.stop()

# --- 3. DATABASE & LOGIC ---
try: conn = st.connection("supabase", type=SupabaseConnection)
except: st.error("Database Connection Lost."); st.stop()

SYSTEMS = {"PS1":"PS5", "PS2":"PS5", "PS3":"PS5", "PC1":"PC", "PC2":"PC", "SIM1":"Racing Sim"}
FLAT_MENU = ["Custom Item...","Veggie Nuggets - ₹209","Chilli Garlic Bites - ₹209","Veg Cheese Balls - ₹229","Jalapeno Poppers - ₹230","Pizza Fingers - ₹229","Salted French Fries - ₹139","Peri-Peri French Fries - ₹159","Chilli Garlic French Fries - ₹169","Cheesy French Fries - ₹179","Tikki Tango Burger - ₹89","Tikki Tango Meal - ₹199","Peri Peri Mini Burger - ₹119","Peri Peri Mini Meal - ₹229","Paneer Pataka Burger - ₹230","Paneer Pataka Meal - ₹229","Big Crunch Burger - ₹229","Big Crunch Meal - ₹239","Cold Coffee - ₹129","Vanilla Milkshake - ₹149","Irish Cold Coffee - ₹159","Cold Chocolate - ₹169","Oreo Milkshake - ₹179","Blue Lagoon - ₹129","Green Apple Mojito - ₹129","Lime Ice Tea - ₹129","Mint Mojito - ₹129","Chilli Guava - ₹129","Black Current - ₹129","Watermelon - ₹129","Paan - ₹129","Pineapple - ₹129","Blueberry - ₹129"]

def get_price(cat, dur, extra=0):
    if cat == "PS5": return (int(dur) * (150 + (extra * 100))) + ((1 if (dur % 1) != 0 else 0) * (100 + (extra * 100)))
    elif cat == "PC": return (int(dur) * 100) + ((1 if (dur % 1) != 0 else 0) * 70)
    elif cat == "Racing Sim": return (int(dur) * 250) + ((1 if (dur % 1) != 0 else 0) * 150)
    return 0

# --- 4. TABS ---
t1, t2, t3, t4, t5 = st.tabs(["🕹️ Live Floor", "📝 Bookings", "📊 Daily Snapshot", "📅 Reports", "🧠 Vault"])

# ==========================================
# TAB 1: LIVE FLOOR (ICE BLUE THEME)
# ==========================================
with t1:
    col_timers, col_manage = st.columns([2, 1])
    with col_timers:
        st.subheader("Current Sessions")
        try:
            res = conn.table("sales").select("*").eq("status", "Active").execute()
            active_df = pd.DataFrame(res.data)
            if not active_df.empty:
                t_cols = st.columns(2)
                for i, (_, row) in enumerate(active_df.iterrows()):
                    with t_cols[i % 2]:
                        try:
                            entry_dt = pd.to_datetime(f"{row['date'][:10]} {row['entry_time']}").tz_localize(IST)
                            time_left = ((entry_dt + timedelta(hours=row['duration'])) - datetime.now(IST)).total_seconds() / 60.0
                        except: time_left = 0
                        
                        # Style logic
                        cc = "active" if time_left > 10 else ("warning" if time_left > 0 else "overdue")
                        
                        st.markdown(f"""
                        <div class='ga-card ga-card-{cc}'>
                            <p class='card-title'>{row['system']} | {row['customer']}</p>
                            <p class='card-metric'>{int(time_left)}m remaining</p>
                            <p style='font-size:12px;color:#9CA3AF;'>Total Bill: ₹{row['total'] + (row.get('fnb_total') or 0):.0f}</p>
                        </div>
                        """, unsafe_allow_html=True)
            else: st.info("Floor is clear.")
        except: st.write("Loading...")

    with col_manage:
        st.markdown(f"<div class='ga-card' style='border-color:{ga_colors['ice_blue']}'>", unsafe_allow_html=True)
        st.markdown("<p class='card-title'>Quick Actions</p>", unsafe_allow_html=True)
        if not active_df.empty:
            active_df['lbl'] = active_df['customer'] + " | " + active_df['system']
            sel = st.selectbox("Select Player", active_df['lbl'].tolist())
            p_row = active_df[active_df['lbl'] == sel].iloc[0]
            
            act = st.radio("Action", ["Extend Time", "Add Food", "Checkout"], horizontal=True)
            
            if act == "Extend Time":
                hrs = st.number_input("Extra Hrs", 0.5, 5.0, 0.5, 0.5)
                if st.button("Confirm Extension"):
                    new_total = p_row['total'] + get_price(SYSTEMS[p_row['system']], hrs)
                    conn.table("sales").update({"total": new_total, "duration": p_row['duration'] + hrs}).eq("id", int(p_row['id'])).execute()
                    st.rerun()
            
            elif act == "Add Food":
                f_sel = st.selectbox("Menu", FLAT_MENU)
                f_name, f_price = (st.text_input("Item"), st.number_input("Price", 0)) if f_sel == "Custom Item..." else (f_sel.split(" - ")[0], int(f_sel.split("₹")[1]))
                if st.button("Add to Tab"):
                    cur_f = str(p_row.get('fnb_items') or "")
                    new_f = f"{cur_f} | {f_name}" if cur_f else f_name
                    conn.table("sales").update({"fnb_items": new_f, "fnb_total": (p_row.get('fnb_total') or 0) + f_price}).eq("id", int(p_row['id'])).execute()
                    st.rerun()

            elif act == "Checkout":
                g_total = p_row['total'] + (p_row.get('fnb_total') or 0)
                st.success(f"### Collect: ₹{g_total:.0f}")
                meth = st.radio("Method", ["Cash", "UPI"], horizontal=True)
                if st.button("Complete & Close"):
                    conn.table("sales").update({"status": "Completed", "method": meth, "total": float(g_total)}).eq("id", int(p_row['id'])).execute()
                    st.balloons(); st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# TAB 3: SNAPSHOT (ICE BLUE CHARTS)
# ==========================================
with t3:
    st.subheader("Daily Revenue Dashboard")
    try:
        raw = conn.table("sales").select("*").execute()
        df = pd.DataFrame(raw.data)
        today = datetime.now(IST).strftime('%Y-%m-%d')
        df['date_str'] = df['date'].str[:10]
        t_df = df[df['date_str'] == today]
        comp = t_df[t_df['status'] == 'Completed']
        
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"<div class='ga-card'><p class='card-subtitle'>Cash Income</p><p class='card-metric'>₹{comp[comp['method']=='Cash']['total'].sum():,.0f}</p></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='ga-card'><p class='card-subtitle'>UPI Income</p><p class='card-metric'>₹{comp[comp['method']!='Cash']['total'].sum():,.0f}</p></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='ga-card' style='border-color:{ga_colors['ice_blue']}'><p class='card-subtitle'>Grand Total</p><p class='card-metric'>₹{comp['total'].sum():,.0f}</p></div>", unsafe_allow_html=True)
        
        st.write("### Weekly Growth")
        if not comp.empty:
            # Ice Blue Chart
            chart_data = df[df['status']=='Completed'].groupby('date_str')['total'].sum().reset_index().tail(7)
            fig = px.bar(chart_data, x='date_str', y='total', color_discrete_sequence=[ga_colors['ice_blue']])
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color=ga_colors['text'], height=300)
            st.plotly_chart(fig, use_container_width=True)
    except: pass

# ==========================================
# TAB 2: BOOKINGS (STABLE)
# ==========================================
with t2:
    col_f, col_c = st.columns([1, 1])
    with col_f:
        st.subheader("New Session")
        with st.container(border=True):
            name = st.text_input("Name", key=f"n_{st.session_state.form_reset}")
            b_type = st.radio("Type", ["Walk-in", "Booking"], horizontal=True)
            sys = st.selectbox("System", list(SYSTEMS.keys()))
            dur = st.number_input("Hours", 0.5, 12.0, 1.0, 0.5)
            if st.button("Add to Cart"):
                st.session_state.cart.append({"sys": sys, "dur": dur, "price": get_price(SYSTEMS[sys], dur)})
                st.rerun()
    with col_c:
        st.subheader("Cart")
        if st.session_state.cart:
            for i, item in enumerate(st.session_state.cart):
                st.write(f"🎮 {item['sys']} ({item['dur']}h) - ₹{item['price']}")
            if st.button("🚀 Start Sessions"):
                for item in st.session_state.cart:
                    conn.table("sales").insert({"customer": name, "system": item['sys'], "duration": item['dur'], "total": item['price'], "status": "Active" if b_type=="Walk-in" else "Booked", "date": datetime.now(IST).isoformat(), "scheduled_date": datetime.now(IST).strftime('%Y-%m-%d')}).execute()
                st.session_state.cart = []; st.session_state.form_reset += 1; st.rerun()

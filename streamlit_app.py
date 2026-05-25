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
    .stApp, .stApp > header { background-color: #0B0E14; color: #FFFFFF; }
    h1, h2, h3, h4, p, span, label, div { color: #FFFFFF !important; }
    .stButton>button { 
        background: linear-gradient(135deg, #00D0FF 0%, #0080FF 100%); 
        color: #FFFFFF !important; border-radius: 8px; width: 100%; font-weight: 700; border: none; transition: 0.3s; 
        box-shadow: 0 4px 15px rgba(0, 208, 255, 0.25);
    }
    .stButton>button:hover { background: linear-gradient(135deg, #00BFFF 0%, #0066CC 100%); transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0, 208, 255, 0.4); }
    .metric-box { background-color: #121824; padding: 20px; border-radius: 12px; text-align: center; border-top: 3px solid #00D0FF; margin-bottom: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }
    .panel-box { background: #121824; padding: 20px; border-radius: 16px; border: 1px solid #1E293B; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }
    .menu-btn>button { background: #1A2235; border: 1px solid #2D3748; height: 70px; border-radius: 10px; color: #E2E8F0 !important; transition: 0.2s; }
    .menu-btn>button:hover { border-color: #00D0FF; color: #00D0FF !important; box-shadow: 0 0 12px rgba(0, 208, 255, 0.2); }
    input, select, .stSelectbox > div > div { background-color: #1A2235 !important; color: white !important; border: 1px solid #2D3748 !important; }
</style>
""", unsafe_allow_html=True)

# --- 2. AUTH ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🔒 Gamerarena Central Login")
    if st.text_input("Enter Passcode", type="password") == "Admin@2026":
        st.session_state.auth = True; st.rerun()
    st.stop()

# --- SYSTEM SIDEBAR ---
with st.sidebar:
    st.write("### ⚙️ System Controls")
    if st.button("🔄 Force Sync Data", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()
    if st.button("🔒 Lock Screen", use_container_width=True):
        st.session_state.auth = False
        st.rerun()

# --- 3. DATABASE SETUP ---
try: conn = st.connection("supabase", type=SupabaseConnection, ttl=0)
except Exception as e: st.error(f"DB Error: {e}"); st.stop()

# --- TABS ---
t1, t2, t3, t4, t5 = st.tabs(["🕹️ Live Floor", "🍔 Cafe & Stock", "📅 Bookings", "📊 Snapshot", "🧠 Master Vault"])

# ==========================================
# TAB 5: MASTER VAULT (OWNER P&L VIEW)
# ==========================================
with t5:
    st.subheader("🔐 Master Intelligence Vault")
    if st.text_input("Master Key", type="password", key="t5_pwd") == "Su22101992@":
        
        # Fetch Data
        today_str = datetime.now(IST).strftime('%Y-%m-%d')
        vdf = pd.DataFrame(conn.table("sales").select("*").order('id', desc=True).limit(50000).execute().data)
        cafe_all = pd.DataFrame(conn.table("cafe_orders").select("*").order('id', desc=True).limit(50000).execute().data)
        exp_df = pd.DataFrame(conn.table("expenses").select("*").order('id', desc=True).limit(50000).execute().data)
        
        if not vdf.empty and not cafe_all.empty:
            vdf['date_obj'] = pd.to_datetime(vdf['date'].str[:10])
            cafe_all['date_obj'] = pd.to_datetime(cafe_all['date'].str[:10])
            exp_df['date_obj'] = pd.to_datetime(exp_df['expense_date'])
            
            daily_game = vdf.groupby('date_obj').apply(lambda x: (x['total'] - x['fnb_total']).sum()).rename('pure_game')
            daily_cafe = cafe_all.groupby('date_obj').agg({'total_revenue': 'sum', 'profit': 'sum'})
            daily_exp = exp_df.groupby('date_obj')['amount'].sum().rename('daily_expenses')
            
            pnl = pd.concat([daily_game, daily_cafe, daily_exp], axis=1).fillna(0)
            pnl['Net Revenue'] = pnl['pure_game'] + pnl['profit']
            pnl['Net Profit'] = pnl['Net Revenue'] - pnl['daily_expenses']
            
            # --- THE FIX: FORCED DATETIME CONVERSION ---
            pnl.index = pd.to_datetime(pnl.index)
            
            # KPI Metrics
            now = datetime.now(IST).replace(hour=0, minute=0, second=0, microsecond=0)
            start_tm = now.replace(day=1)
            start_lm = (start_tm - timedelta(days=1)).replace(day=1)
            start_tw = now - timedelta(days=now.weekday())
            start_lw = start_tw - timedelta(days=7)
            
            def get_stats(df, mask):
                return df.loc[mask, 'Net Profit'].sum()

            prof_life = pnl['Net Profit'].sum()
            prof_mtd = get_stats(pnl, pnl.index >= start_tm)
            prof_lm = get_stats(pnl, (pnl.index >= start_lm) & (pnl.index < start_tm))
            prof_wtd = get_stats(pnl, pnl.index >= start_tw)
            prof_lw = get_stats(pnl, (pnl.index >= start_lw) & (pnl.index < start_tw))
            prof_today = get_stats(pnl, pnl.index == now)
            prof_last_week_day = get_stats(pnl, pnl.index == (now - timedelta(days=7)))

            def fmt_delta(curr, prev):
                pct = ((curr - prev) / abs(prev) * 100) if prev != 0 else (100 if curr > 0 else 0)
                return f"{pct:+.1f}%"

            st.write("### 🚀 Executive Profit Growth (KPIs)")
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Lifetime Net Profit", f"₹{prof_life:,.0f}")
            k2.metric("MTD Profit", f"₹{prof_mtd:,.0f}", fmt_delta(prof_mtd, prof_lm))
            k3.metric("WTD Profit", f"₹{prof_wtd:,.0f}", fmt_delta(prof_wtd, prof_lw))
            k4.metric("Today vs Same Day Last Wk", f"₹{prof_today:,.0f}", fmt_delta(prof_today, prof_last_week_day))

            st.divider()
            st.write("### 🧮 Detailed Financial Matrix")
            disp = pnl[['Net Revenue', 'daily_expenses', 'Net Profit']].copy().sort_index(ascending=False)
            disp.columns = ['Net Revenue (Gross Profit)', 'Expenses', 'Net Profit']
            st.dataframe(disp.style.format("₹{:,.0f}"), use_container_width=True)

import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import datetime

# --- PAGE CONFIG & CUSTOM STYLING ---
st.set_page_config(page_title="Gamerarena OS", page_icon="🎮", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    .stButton>button {
        background: linear-gradient(135deg, #6e8efb, #a777e3);
        color: white; border-radius: 10px; border: none;
        padding: 12px 24px; font-weight: 700; font-size: 16px; transition: 0.3s ease;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 8px 15px rgba(0,0,0,0.2); }
    div[data-testid="metric-container"] {
        background-color: #1e1e2f; border: 1px solid #2d2d44;
        padding: 15px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# --- 1. SECURE LOGIN SYSTEM ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.title("🔒 Gamerarena Secure Access")
        st.write("Please enter the admin passcode to access the POS.")
        
        pwd = st.text_input("Password", type="password")
        if st.button("Login"):
            # CHANGE YOUR PASSWORD HERE IF YOU WANT
            if pwd == "Admin@2026": 
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ Incorrect Password. Access Denied.")
        return False
    return True

# Stop the rest of the app from loading if not logged in
if not check_password():
    st.stop()

# --- 2. MAIN DASHBOARD ---
st.title("🎮 Gamerarena Central OS")
st.caption("Palghar's Premier Gaming Destination | Admin Mode")

conn = st.connection("supabase", type=SupabaseConnection)

# --- SMART PRICING LOGIC ---
PRICES_1HR = {"PC Gaming": 100, "PS5 Gaming": 150, "Racing Sim": 250}
PRICES_30MIN = {"PC Gaming": 70, "PS5 Gaming": 100, "Racing Sim": 150}

SYSTEMS = {
    "PS1": "PS5 Gaming", "PS2": "PS5 Gaming", "PS3": "PS5 Gaming", 
    "PC1": "PC Gaming", "PC2": "PC Gaming", 
    "SIM1": "Racing Sim"
}

def calculate_price(category, duration, extra_ctrl=0):
    full_hours = int(duration)
    is_half_hour = (duration % 1) == 0.5
    
    # Calculate base time cost
    cost = (full_hours * PRICES_1HR[category])
    if is_half_hour:
        cost += PRICES_30MIN[category]
        
    # Add controller cost (₹100 per extra controller)
    if "PS5" in category:
        cost += (extra_ctrl * 100)
        
    return cost

# --- TABS ---
tab_book, tab_data = st.tabs(["📝 New Session Entry", "📊 Live Analytics & Downloads"])

# --- TAB 1: BOOKING ---
with tab_book:
    with st.container(border=True):
        col1, col2 = st.columns(2, gap="large")
        
        with col1:
            st.subheader("👤 Player Profile")
            cust_name = st.text_input("Gamer Name", placeholder="e.g., Rohan")
            cust_phone = st.text_input("Contact Number")
            cust_insta = st.text_input("Instagram ID")
            
        with col2:
            st.subheader("🕹️ Session Details")
            selected_systems = st.multiselect("Select Systems", list(SYSTEMS.keys()))
            
            # Entry Time Picker
            entry_time = st.time_input("Time In", value="now")
            duration = st.number_input("Duration (Hours)", min_value=0.5, max_value=12.0, step=0.5, value=1.0)
            
            has_ps5 = any("PS" in sys for sys in selected_systems)
            extra_ctrl = st.number_input("Extra Controllers (₹100 each)", min_value=0, max_value=3, step=1) if has_ps5 else 0
                
            pay_mode = st.radio("Payment Gateway", ["Cash", "Online / UPI"], horizontal=True)
            
    st.write("") 
    submitted = st.button("🚀 Confirm & Deploy Session", use_container_width=True)

    if submitted:
        if not cust_name or not selected_systems:
            st.error("⚠️ Please provide a Gamer Name and select at least one system.")
        else:
            try:
                with st.spinner("Syncing to Cloud..."):
                    for sys in selected_systems:
                        category = SYSTEMS[sys]
                        total_price = calculate_price(category, duration, extra_ctrl)
                        formatted_time = entry_time.strftime("%I:%M %p") # Format like "02:30 PM"
                        
                        conn.table("sales").insert({
                            "customer": cust_name, "phone": cust_phone, "instagram": cust_insta,
                            "system": sys, "total": total_price, "method": pay_mode,
                            "entry_time": formatted_time
                        }).execute()
                
                st.balloons()
                st.success(f"✅ Logged! Total to collect: ₹{total_price} per system.")
            except Exception as e:
                st.error(f"❌ Error: {e}")

# --- TAB 2: ANALYTICS & DOWNLOAD ---
with tab_data:
    st.subheader("📈 Real-Time Cafe Metrics")
    try:
        response = conn.table("sales").select("*").execute()
        data = pd.DataFrame(response.data)
        
        if not data.empty:
            data['date'] = pd.to_datetime(data['date'])
            today = datetime.now().date()
            today_data = data[data['date'].dt.date == today]
            
            m1, m2, m3 = st.columns(3)
            m1.metric("💰 Today's Collection", f"₹{today_data['total'].sum():,.2f}")
            m2.metric("💵 Cash Collected", f"₹{today_data[today_data['method'] == 'Cash']['total'].sum():,.2f}")
            m3.metric("📱 Online / UPI", f"₹{today_data[today_data['method'] == 'Online / UPI']['total'].sum():,.2f}")
            
            st.divider()
            
            # --- DOWNLOAD BUTTON ---
            if not today_data.empty:
                csv = today_data.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Today's Summary (CSV/Excel)",
                    data=csv,
                    file_name=f"Gamerarena_Daily_Summary_{today}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            st.markdown("### 🗄️ Main Ledger")
            # Use 'entry_time' if it exists in the data, otherwise ignore
            cols_to_show = ['date', 'entry_time', 'customer', 'system', 'total', 'method', 'phone', 'instagram']
            display_cols = [c for c in cols_to_show if c in data.columns]
            
            display_df = data[display_cols].copy()
            display_df.sort_values(by="date", ascending=False, inplace=True)
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("No data yet.")
    except Exception as e:
        st.warning(f"Waiting for data structure to update... {e}")

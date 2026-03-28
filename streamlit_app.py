import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import datetime

# --- PAGE CONFIG & CUSTOM STYLING (The "2026 UI" look) ---
st.set_page_config(page_title="Gamerarena OS", page_icon="🎮", layout="wide")

st.markdown("""
<style>
    /* Sleek modern font and spacing */
    .block-container { padding-top: 2rem; }
    /* Customizing the main button */
    .stButton>button {
        background: linear-gradient(135deg, #6e8efb, #a777e3);
        color: white;
        border-radius: 10px;
        border: none;
        padding: 12px 24px;
        font-weight: 700;
        font-size: 16px;
        transition: 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 15px rgba(0,0,0,0.2);
    }
    /* Metric styling */
    div[data-testid="metric-container"] {
        background-color: #1e1e2f;
        border: 1px solid #2d2d44;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

st.title("🎮 Gamerarena Central OS")
st.caption("Palghar's Premier Gaming Destination | Active Node")

# --- DATABASE CONNECTION ---
conn = st.connection("supabase", type=SupabaseConnection)

# --- PRICING & LOGIC ---
PRICES = {"PC Gaming": 99, "PS5 Gaming": 149, "Racing Sim": 249}
SYSTEMS = {
    "PS1": "PS5 Gaming", "PS2": "PS5 Gaming", "PS3": "PS5 Gaming", 
    "PC1": "PC Gaming", "PC2": "PC Gaming", 
    "SIM1": "Racing Sim"
}

# --- MAIN DASHBOARD TABS ---
tab_book, tab_data = st.tabs(["📝 New Session Entry", "📊 Live Analytics"])

# ----------------------------------------
# TAB 1: BOOKING UI
# ----------------------------------------
with tab_book:
    with st.container(border=True):
        col1, col2 = st.columns(2, gap="large")
        
        with col1:
            st.subheader("👤 Player Profile")
            cust_name = st.text_input("Gamer Tag / Name", placeholder="e.g., Rohan Sharma")
            cust_phone = st.text_input("Contact Number", placeholder="10-digit mobile number")
            cust_insta = st.text_input("Instagram ID", placeholder="@username")
            
        with col2:
            st.subheader("🕹️ Hardware Assignment")
            selected_systems = st.multiselect("Select Systems", list(SYSTEMS.keys()))
            duration = st.slider("Duration (Hours)", min_value=0.5, max_value=5.0, step=0.5, value=1.0)
            
            # Smart Controller Input (Only shows up if a PS5 is selected)
            has_ps5 = any("PS" in sys for sys in selected_systems)
            if has_ps5:
                extra_ctrl = st.number_input("Extra Controllers (₹100 each)", min_value=0, max_value=3, step=1)
            else:
                extra_ctrl = 0
                
            pay_mode = st.radio("Payment Gateway", ["Cash", "Online / UPI"], horizontal=True)
            
    st.write("") # Spacer
    submitted = st.button("🚀 Confirm & Deploy Session", use_container_width=True)

    if submitted:
        if not cust_name or not selected_systems:
            st.error("⚠️ System Override: Please provide a Gamer Name and select at least one rig.")
        else:
            try:
                with st.spinner("Encrypting and syncing to Supabase..."):
                    for sys in selected_systems:
                        category = SYSTEMS[sys]
                        added_cost = (extra_ctrl * 100) if "PS" in sys else 0
                        total_price = (PRICES[category] * duration) + added_cost
                        
                        # Sending to Supabase Database
                        conn.table("sales").insert({
                            "customer": cust_name, 
                            "phone": cust_phone, 
                            "instagram": cust_insta,
                            "system": sys, 
                            "total": total_price, 
                            "method": pay_mode
                        }).execute()
                
                st.balloons()
                st.success(f"✅ Securely logged {len(selected_systems)} stations for {cust_name}!")
            except Exception as e:
                st.error(f"❌ Server communication failed: {e}")

# ----------------------------------------
# TAB 2: ANALYTICS UI
# ----------------------------------------
with tab_data:
    st.subheader("📈 Real-Time Cafe Metrics")
    try:
        # Pull data live from Supabase
        response = conn.table("sales").select("*").execute()
        data = pd.DataFrame(response.data)
        
        if not data.empty:
            # Handle timestamps properly
            data['date'] = pd.to_datetime(data['date'])
            today = datetime.now().date()
            today_data = data[data['date'].dt.date == today]
            
            # Top row metrics
            m1, m2, m3 = st.columns(3)
            m1.metric("💰 Today's Collection", f"₹{today_data['total'].sum():,.2f}")
            m2.metric("👥 Active Sessions Today", len(today_data))
            m3.metric("🏆 All-Time Revenue", f"₹{data['total'].sum():,.2f}")
            
            st.divider()
            
            # Clean data table
            st.markdown("### 🗄️ Main Ledger")
            # Reorder columns for better reading
            display_df = data[['date', 'customer', 'system', 'total', 'method', 'phone', 'instagram']].copy()
            display_df.sort_values(by="date", ascending=False, inplace=True)
            
            # Hide the index numbers for a cleaner look
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("The database is clean. Awaiting your first official customer entry.")
    except Exception as e:
        st.warning("Database syncing... waiting for initial data structure.")

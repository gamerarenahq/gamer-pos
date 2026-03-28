import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CONFIG ---
st.set_page_config(page_title="Gamerarena POS", layout="wide")
st.title("🎮 Gamerarena Central POS")

# This is the correct way to connect in the code
conn = st.connection("gsheets", type=GSheetsConnection)

# Pricing Logic
PRICES = {"PC Gaming": 99, "PS5 Gaming": 149, "Racing Sim": 249}
SYSTEMS = {
    "PS1": "PS5 Gaming", "PS2": "PS5 Gaming", "PS3": "PS5 Gaming", 
    "PC1": "PC Gaming", "PC2": "PC Gaming", 
    "SIM1": "Racing Sim"
}

# --- INPUT SECTION ---
with st.sidebar.form("entry_form"):
    st.header("Customer Info")
    cust_name = st.text_input("Customer Name")
    cust_phone = st.text_input("Contact Number")
    cust_insta = st.text_input("Instagram ID")
    
    st.divider()
    st.header("Booking Details")
    selected_systems = st.multiselect("Select Systems", list(SYSTEMS.keys()))
    duration = st.number_input("Duration (Hours)", min_value=0.5, max_value=5.0, step=0.5)
    extra_ctrl = st.number_input("Extra Controllers (per PS5)", 0, 3)
    pay_mode = st.radio("Payment Method", ["Cash", "Online"])
    
    submitted = st.form_submit_button("Confirm & Log Booking")

if submitted:
    if not selected_systems or not cust_name:
        st.error("Please enter a Name and select a System.")
    else:
        try:
            existing_data = conn.read(ttl=0)
        except:
            existing_data = pd.DataFrame(columns=["Date", "Customer", "Phone", "Instagram", "System", "Total", "Method"])

        new_entries = []
        for sys in selected_systems:
            category = SYSTEMS[sys]
            total_price = (PRICES[category] * duration) + ((extra_ctrl * 100) if "PS" in sys else 0)
            
            new_entries.append({
                "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Customer": cust_name, "Phone": cust_phone, "Instagram": cust_insta,
                "System": sys, "Total": total_price, "Method": pay_mode
            })
        
        updated_df = pd.concat([existing_data, pd.DataFrame(new_entries)], ignore_index=True)
        conn.update(data=updated_df)
        st.success(f"✅ Logged for {cust_name}!")

# --- DASHBOARD ---
try:
    data = conn.read(ttl="1m")
    if not data.empty:
        st.divider()
        st.subheader("Today's Revenue: ₹" + str(data['Total'].sum()))
        st.dataframe(data.sort_index(ascending=False), use_container_width=True)
except:
    st.info("Log your first entry to see the table.")

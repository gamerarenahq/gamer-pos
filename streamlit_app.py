import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Gamerarena POS", layout="wide")
st.title("🎮 Gamerarena Central POS")

# Connect to Supabase
conn = st.connection("supabase", type=SupabaseConnection)

# Pricing Logic
PRICES = {"PC Gaming": 99, "PS5 Gaming": 149, "Racing Sim": 249}
SYSTEMS = {"PS1": "PS5 Gaming", "PS2": "PS5 Gaming", "PS3": "PS5 Gaming", "PC1": "PC Gaming", "PC2": "PC Gaming", "SIM1": "Racing Sim"}

with st.sidebar.form("entry_form"):
    st.header("Booking")
    cust_name = st.text_input("Customer Name")
    cust_phone = st.text_input("Phone")
    cust_insta = st.text_input("Instagram")
    selected_systems = st.multiselect("Systems", list(SYSTEMS.keys()))
    duration = st.number_input("Hours", 0.5, 5.0, step=0.5)
    extra_ctrl = st.number_input("Extra Controllers", 0, 3)
    pay_mode = st.radio("Payment", ["Cash", "Online"])
    submitted = st.form_submit_button("Log Sale")

if submitted:
    for sys in selected_systems:
        total = (PRICES[SYSTEMS[sys]] * duration) + ((extra_ctrl * 100) if "PS" in sys else 0)
        
        # Save to Supabase
        conn.table("sales").insert({
            "customer": cust_name, "phone": cust_phone, "instagram": cust_insta,
            "system": sys, "total": total, "method": pay_mode
        }).execute()
    st.success("✅ Saved to Cloud!")

# Dashboard
try:
    response = conn.table("sales").select("*").execute()
    data = pd.DataFrame(response.data)
    if not data.empty:
        st.metric("Total Revenue", f"₹{data['total'].sum()}")
        st.dataframe(data.sort_index(ascending=False), use_container_width=True)
except:
    st.info("Ready for first entry.")

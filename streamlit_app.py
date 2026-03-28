import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Gamerarena Debug POS", layout="wide")

# --- DEBUG CONNECTION CHECK ---
st.write("### 🔍 Connection Status")
try:
    # Checking if secrets exist
    if "connections" not in st.secrets:
        st.error("❌ I can't find the [connections.supabase] section in your Secrets!")
    else:
        st.success("✅ Found the Secrets section!")
        
    # Attempting to connect
    conn = st.connection("supabase", type=SupabaseConnection)
    st.success("✅ Connected to Supabase successfully!")
    
except Exception as e:
    st.error(f"❌ Connection Failed! Error message: {e}")
    st.info("Check your Secrets tab again. Make sure 'url' and 'key' are spelled exactly like that.")
    st.stop() # Stops the app here so we can fix the error

# --- REST OF YOUR APP (Only runs if connection works) ---
st.title("🎮 Gamerarena Central POS")

PRICES = {"PC Gaming": 99, "PS5 Gaming": 149, "Racing Sim": 249}
SYSTEMS = {"PS1": "PS5 Gaming", "PS2": "PS5 Gaming", "PS3": "PS5 Gaming", "PC1": "PC Gaming", "PC2": "PC Gaming", "SIM1": "Racing Sim"}

with st.sidebar.form("entry_form"):
    st.header("New Entry")
    cust_name = st.text_input("Name")
    cust_phone = st.text_input("Phone")
    selected_systems = st.multiselect("Systems", list(SYSTEMS.keys()))
    duration = st.number_input("Hours", 0.5, 5.0, step=0.5)
    pay_mode = st.radio("Payment", ["Cash", "Online"])
    submitted = st.form_submit_button("Log Sale")

if submitted:
    for sys in selected_systems:
        total = (PRICES[SYSTEMS[sys]] * duration)
        conn.table("sales").insert({
            "customer": cust_name, "phone": cust_phone,
            "system": sys, "total": total, "method": pay_mode
        }).execute()
    st.balloons()
    st.success("Saved!")

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CONFIG ---
st.set_page_config(page_title="Gamerarena Online POS", layout="wide")
st.title("🎮 Gamerarena Cloud POS")

# Create connection to Google Sheets
# Note: You will set the URL in the Streamlit Cloud "Secrets" later
conn = [connections.gsheets]
spreadsheet = "https://docs.google.com/spreadsheets/d/1yP9bwWNfpSLq4apjtF7qphnbgCzJdYjQOrSQnWRjVB0/"

# Pricing Logic
PRICES = {"PC Gaming": 99, "PS5 Gaming": 149, "Racing Sim": 249}
SYSTEMS = {"PS1": "PS5 Gaming", "PS2": "PS5 Gaming", "PS3": "PS5 Gaming", "PC1": "PC Gaming", "PC2": "PC Gaming", "SIM1": "Racing Sim"}

# --- INPUT SECTION ---
with st.sidebar.form("entry_form"):
    cust_name = st.text_input("Customer Name")
    selected_sys = st.selectbox("System", list(SYSTEMS.keys()))
    duration = st.selectbox("Duration (Hrs)", [0.5, 1, 2, 3,4,5])
    extra_ctrl = st.number_input("Extra Controllers", 0, 3) if "PS" in selected_sys else 0
    pay_mode = st.radio("Payment", ["Cash", "Online"])
    submitted = st.form_submit_button("Log Sale")

if submitted:
    # Calculate Total
    total = (PRICES[SYSTEMS[selected_sys]] * duration) + (extra_ctrl * 100)
    
    # Get existing data to append
    existing_data = conn.read(ttl=0)
    new_row = pd.DataFrame([{
        "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "Customer": cust_name,
        "System": selected_sys,
        "Total": total,
        "Method": pay_mode
    }])
    
    updated_df = pd.concat([existing_data, new_row], ignore_index=True)
    
    # Save back to Google Sheets
    conn.update(data=updated_df)
    st.success(f"Saved! Total: ₹{total}")

# --- DASHBOARD ---
data = conn.read(ttl="1m") # Refresh every minute
if not data.empty:
    st.metric("Today's Revenue", f"₹{data['Total'].sum()}")
    st.dataframe(data.sort_index(ascending=False))

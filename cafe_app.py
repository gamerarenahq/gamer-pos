import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import datetime
import pytz

# --- 1. CONFIG & THEME ---
st.set_page_config(page_title="Hunger Monkey Pro", layout="wide")
IST = pytz.timezone('Asia/Kolkata')

try: conn = st.connection("supabase", type=SupabaseConnection)
except: st.error("Database Connection Failed."); st.stop()

# Clean Corporate UI
st.markdown("""
<style>
    .stApp { background-color: #0B0E14; }
    h1, h2, h3, h4, p, span, label { color: #FFFFFF !important; font-family: 'Inter', sans-serif; }
    .metric-box { background: #1A1F2B; padding: 20px; border-radius: 12px; border-top: 4px solid #98DED9; text-align: center; }
    .stButton>button { background: #161922; border: 1px solid #2D3446; color: white; height: 90px; border-radius: 12px; transition: 0.2s; }
    .stButton>button:hover { border-color: #98DED9; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATA LOAD ---
inv_res = conn.table("inventory").select("*").order('item_name').execute()
inv_df = pd.DataFrame(inv_res.data)

# --- 3. APP TABS ---
t_pos, t_stock, t_vault = st.tabs(["🛒 Quick Billing POS", "📦 Inventory Control", "🧠 Executive Vault"])

# ==========================================
# TAB 1: POS (STAFF VIEW)
# ==========================================
with t_pos:
    if inv_df.empty: 
        st.warning("Please run the SQL Seed script to load the menu.")
    else:
        st.subheader("Hunger Monkey POS")
        col_menu, col_checkout = st.columns([2.5, 1])
        
        with col_menu:
            # Create a horizontal filter for categories
            cat_filter = st.radio("Select Category", inv_df['category'].unique(), horizontal=True, label_visibility="collapsed")
            items = inv_df[inv_df['category'] == cat_filter]
            
            grid = st.columns(4)
            for i, (_, row) in enumerate(items.iterrows()):
                # Clean label showing item, price, and remaining stock
                label = f"{row['item_name']}\n₹{row['selling_price']:.0f}\n[Stock: {row['stock_level']}]"
                if grid[i % 4].button(label, key=f"pos_{row['id']}", disabled=row['stock_level'] <= 0, use_container_width=True):
                    
                    # 1. Deduct Stock
                    conn.table("inventory").update({"stock_level": row['stock_level'] - 1}).eq("id", row['id']).execute()
                    
                    # 2. Log Sale for Vendor Payouts
                    conn.table("cafe_orders").insert({
                        "date": datetime.now(IST).strftime('%Y-%m-%d'),
                        "items": row['item_name'],
                        "total_revenue": float(row['selling_price']),
                        "total_cost": float(row['cost_price']),
                        "profit": float(row['selling_price'] - row['cost_price']),
                        "method": "Direct"
                    }).execute()
                    
                    st.toast(f"✅ Billed: 1x {row['item_name']}")
                    st.rerun()

# ==========================================
# TAB 2: INVENTORY (MANAGEMENT VIEW)
# ==========================================
with t_stock:
    st.subheader("Inventory Health & Restocking")
    
    # Low Stock Alerts
    if not inv_df.empty:
        low_stock = inv_df[inv_df['stock_level'] <= 5]
        if not low_stock.empty:
            st.error(f"🚨 ACTION REQUIRED: {len(low_stock)} items are critically low on stock!")
            st.dataframe(low_stock[['item_name', 'stock_level']], hide_index=True)
    
    st.divider()
    
    col_refill, col_new = st.columns(2, gap="large")
    with col_refill:
        st.markdown("<div class='metric-box' style='border-top-color:#FF754C'>", unsafe_allow_html=True)
        st.write("### 📥 Receive New Stock")
        if not inv_df.empty:
            target = st.selectbox("Select Item", inv_df['item_name'].tolist())
            qty = st.number_input("Quantity Arrived", 1, 500, 10)
            if st.button("Update Inventory Levels", use_container_width=True):
                cur = inv_df[inv_df['item_name'] == target]['stock_level'].values[0]
                conn.table("inventory").update({"stock_level": int(cur + qty)}).eq("item_name", target).execute()
                st.success(f"Added {qty} to {target}. New Stock: {cur + qty}"); st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
            
    with col_new:
        st.markdown("<div class='metric-box'>", unsafe_allow_html=True)
        st.write("### ➕ Add Custom Item")
        with st.form("custom_item"):
            name = st.text_input("New Item Name")
            cat = st.selectbox("Category", ["Beverages", "Mocktails", "Fries & Snacks", "Burgers & Meals", "Chips", "Sandwiches", "Other"])
            c_cost = st.number_input("Cost Price (₹)", 0)
            c_sell = st.number_input("Selling Price (₹)", 0)
            c_stock = st.number_input("Initial Stock", 0)
            if st.form_submit_button("Add to Database", use_container_width=True):
                conn.table("inventory").insert({
                    "item_name": name, "category": cat, "cost_price": c_cost, 
                    "selling_price": c_sell, "stock_level": c_stock
                }).execute()
                st.success("Item added successfully."); st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# TAB 3: EXECUTIVE VAULT (CORPORATE COCKPIT)
# ==========================================
with t_vault:
    st.subheader("F&B Financial Dashboard")
    sales_res = conn.table("cafe_orders").select("*").execute()
    sdf = pd.DataFrame(sales_res.data)
    
    if not sdf.empty:
        # Key Metrics
        rev = sdf['total_revenue'].sum()
        cost = sdf['total_cost'].sum()
        prof = rev - cost
        
        m1, m2, m3 = st.columns(3)
        m1.markdown(f"<div class='metric-box'><small>Gross Revenue</small><h2 style='color:#98DED9'>₹{rev:,.0f}</h2></div>", unsafe_allow_html=True)
        m2.markdown(f"<div class='metric-box'><small>Vendor Owed (Cost)</small><h2 style='color:#FF754C'>₹{cost:,.0f}</h2></div>", unsafe_allow_html=True)
        m3.markdown(f"<div class='metric-box' style='border-top-color:#6C5DD3'><small>Net Cafe Profit</small><h2 style='color:#6C5DD3'>₹{prof:,.0f}</h2></div>", unsafe_allow_html=True)
        
        st.write("---")
        st.write("### Lifetime Item Performance")
        
        # Calculate exactly which items are making the most money
        item_stats = sdf.groupby('items').agg(
            Qty_Sold=('id', 'count'),
            Total_Revenue=('total_revenue', 'sum'),
            Net_Profit=('profit', 'sum')
        ).sort_values('Net_Profit', ascending=False).reset_index()
        
        st.dataframe(item_stats, use_container_width=True, hide_index=True)

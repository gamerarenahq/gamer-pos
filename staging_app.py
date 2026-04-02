import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
from st_supabase_connection import st_supabase_connection
import json
import math

# Initialize session state at the VERY TOP to prevent unhashable dict errors
if 'cart' not in st.session_state:
    st.session_state.cart = []
if 'cafe_cart' not in st.session_state:
    st.session_state.cafe_cart = []
if 'form_reset' not in st.session_state:
    st.session_state.form_reset = 0
if 'active_sales' not in st.session_state:
    st.session_state.active_sales = pd.DataFrame()
if 'bookings' not in st.session_state:
    st.session_state.bookings = []

# Timezone setup - STRICTLY Asia/Kolkata
IST = pytz.timezone('Asia/Kolkata')
now = datetime.now(IST)

# Exact Pricing Rules - DO NOT DEVIATE
GAMING_PRICES = {
    'PS1': {'1h': 150, '0.5h': 100},
    'PS2': {'1h': 150, '0.5h': 100},
    'PS3': {'1h': 150, '0.5h': 100},
    'PC1': {'1h': 100, '0.5h': 70},
    'PC2': {'1h': 100, '0.5h': 70},
    'SIM1': {'1h': 250, '0.5h': 150}
}

CAFE_MENU = {
    "Fries & Snacks": {
        "Veggie Nuggets": {"sell": 209, "cost": 160}, 
        "Veg Cheese Balls": {"sell": 229, "cost": 180},
        "Salted French Fries": {"sell": 139, "cost": 100}, 
        "Cheesy French Fries": {"sell": 179, "cost": 140}
    },
    "Burgers & Meals": {
        "Tikki Tango Burger": {"sell": 89, "cost": 50}, 
        "Tikki Tango Meal": {"sell": 199, "cost": 149},
        "Paneer Pataka Meal": {"sell": 229, "cost": 169}, 
        "Big Crunch Burger": {"sell": 229, "cost": 99}
    },
    "Beverages": {
        "Cold Coffee": {"sell": 129, "cost": 99}, 
        "Oreo Milkshake": {"sell": 179, "cost": 150},
        "Blue Lagoon Mocktail": {"sell": 129, "cost": 99}
    }
}

# Initialize Supabase connection
@st.cache_resource
def init_connection():
    return st_supabase_connection("supabase", type="sql")

conn = init_connection()

def sanitize_for_supabase(value):
    """CRITICAL: Prevent NaN crashes in Supabase API"""
    if pd.isna(value) or value is None:
        return 0.0 if isinstance(value, (int, float)) else ""
    return value

def get_today_date():
    return now.strftime("%Y-%m-%d")

def get_now_datetime():
    return now.strftime("%Y-%m-%d %H:%M:%S+05:30")

def get_time_12hr():
    return now.strftime("%I:%M %p")

def calculate_remaining_time(entry_time_str, duration_hours):
    """Calculate live remaining time for active sessions"""
    try:
        # Parse entry time (HH:MM AM/PM format)
        entry_dt = datetime.strptime(entry_time_str, "%I:%M %p").replace(
            year=now.year, month=now.month, day=now.day
        )
        entry_dt = IST.localize(entry_dt)
        end_time = entry_dt + timedelta(hours=duration_hours)
        remaining = max(0, (end_time - now).total_seconds() / 3600)
        return remaining
    except:
        return 0

def is_system_available(system, booked_date, start_time, duration_hours):
    """Double booking prevention logic"""
    query = """
    SELECT id FROM sales 
    WHERE system = %s AND scheduled_date = %s 
    AND status IN ('Active', 'Booked')
    AND (
        (%s BETWEEN entry_time AND DATE_ADD(entry_time, INTERVAL %s HOUR)) OR
        (%s BETWEEN entry_time AND DATE_ADD(entry_time, INTERVAL %s HOUR))
    )
    """
    # Simplified availability check - fetch active/booked for that system/date
    df = conn.query_df(f"""
        SELECT * FROM sales 
        WHERE system = '{system}' AND scheduled_date = '{booked_date}' 
        AND status IN ('Active', 'Booked')
    """)
    return len(df) == 0

def calculate_gaming_price(system, hours):
    """Exact gaming pricing logic"""
    if hours >= 1:
        return GAMING_PRICES.get(system, {}).get('1h', 0)
    else:
        return GAMING_PRICES.get(system, {}).get('0.5h', 0)

# === MAIN APP ===
st.set_page_config(page_title="Gaming Cafe POS & ERP", layout="wide")
st.title("🎮 Gaming Cafe POS & ERP System")
st.markdown("---")

# Sidebar for quick stats
with st.sidebar:
    st.metric("Live Active Sessions", 0)
    st.metric("Today's Gaming Revenue", "₹0")
    st.metric("Pending F&B Tabs", "₹0")

tab1, tab2, tab3, tab4 = st.tabs(["🖥️ Active Floor & Checkout", "📅 Bookings & Groups", "🍔 Cafe POS", "💰 Master Vault"])

# === TAB 1: Active Floor & Unified Checkout ===
with tab1:
    # Fetch active sales
    active_df = conn.query_df("SELECT * FROM sales WHERE status = 'Active'")
    st.session_state.active_sales = active_df
    
    if not active_df.empty:
        col1, col2, col3, col4 = st.columns(4)
        
        for idx, row in active_df.iterrows():
            remaining_hrs = calculate_remaining_time(
                sanitize_for_supabase(row['entry_time']), 
                row['duration']
            )
            
            color = "inverse" if remaining_hrs <= 0 else "normal"
            with col1:
                st.metric(f"**{row['customer']}**", f"{row['system']}", delta=f"{remaining_hrs:.1f}h")
            with col2:
                st.metric("Gaming", f"₹{row['total']:.0f}")
            with col3:
                st.metric("F&B Tab", f"₹{sanitize_for_supabase(row['fnb_total']):.0f}")
            with col4:
                if st.button(f"Checkout {row['customer']}", key=f"checkout_{row['id']}_{st.session_state.form_reset}", 
                           type="primary", use_container_width=True):
                    # Unified Checkout Logic
                    with st.container():
                        st.subheader(f"🛒 Checkout: {row['customer']}")
                        
                        col_a, col_b = st.columns([1, 2])
                        with col_a:
                            final_hours = st.number_input("Final Billed Hours", 
                                                        min_value=0.0, value=row['duration'],
                                                        key=f"hours_{row['id']}_{st.session_state.form_reset}")
                            gaming_total = calculate_gaming_price(row['system'], final_hours)
                        
                        with col_b:
                            fnb_total = sanitize_for_supabase(row['fnb_total'])
                            grand_total = gaming_total + fnb_total
                            st.metric("Grand Total", f"₹{grand_total:.0f}")
                        
                        payment_method = st.selectbox("Payment Method", 
                                                    ['Cash', 'UPI', 'Pending'],
                                                    key=f"method_{row['id']}_{st.session_state.form_reset}")
                        
                        if st.button("✅ Complete Checkout", key=f"complete_{row['id']}_{st.session_state.form_reset}"):
                            # Update sales table
                            conn.query(f"""
                                UPDATE sales SET 
                                duration = {final_hours},
                                total = {gaming_total},
                                method = '{payment_method}',
                                status = 'Completed'
                                WHERE id = {row['id']}
                            """)
                            st.session_state.form_reset += 1
                            st.success("✅ Checkout completed!")
                            st.rerun()
    else:
        st.info("🎉 No active sessions!")

# === TAB 2: Bookings & Group Cart ===
with tab2:
    st.subheader("New Booking / Group Session")
    
    with st.form("booking_form", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1: customer = st.text_input("Customer Name", key=f"cust_{st.session_state.form_reset}")
        with col2: phone = st.text_input("Phone", key=f"phone_{st.session_state.form_reset}")
        with col3: date = st.date_input("Date", value=now.date(), key=f"date_{st.session_state.form_reset}")
        with col4: time = st.time_input("Start Time", value=now.time(), key=f"time_{st.session_state.form_reset}")
        
        st.subheader("🛒 Group Cart")
        systems_list = list(GAMING_PRICES.keys())
        
        # Add to cart
        selected_system = st.selectbox("Add System", systems_list, key=f"sys_{st.session_state.form_reset}")
        hours = st.selectbox("Duration", [0.5, 1.0, 1.5, 2.0], key=f"dur_{st.session_state.form_reset}")
        price = calculate_gaming_price(selected_system, hours)
        
        if st.button("➕ Add to Cart", key=f"addcart_{st.session_state.form_reset}"):
            st.session_state.cart.append({
                'system': selected_system, 'hours': hours, 'price': price
            })
            st.rerun()
        
        # Cart display
        if st.session_state.cart:
            cart_df = pd.DataFrame(st.session_state.cart)
            st.dataframe(cart_df, use_container_width=True)
            total_booking = cart_df['price'].sum()
            st.metric("Booking Total", f"₹{total_booking:.0f}")
            
            if st.form_submit_button("🚀 Start Session", type="primary"):
                # Double booking check
                available = True
                for _, item in cart_df.iterrows():
                    if not is_system_available(item['system'], str(date), str(time), item['hours']):
                        st.error(f"❌ {item['system']} not available!")
                        available = False
                
                if available:
                    # Insert booking
                    for _, item in cart_df.iterrows():
                        conn.query(f"""
                            INSERT INTO sales (date, scheduled_date, entry_time, customer, phone, 
                                            system, duration, total, fnb_items, fnb_total, 
                                            method, status)
                            VALUES ('{get_now_datetime()}', '{date}', '{time.strftime("%I:%M %p")}', 
                                   '{customer}', '{phone}', '{item['system']}', {item['hours']}, 
                                   {item['price']}, '', 0.0, 'Pending', 'Booked')
                        """)
                    
                    st.session_state.cart = []
                    st.session_state.form_reset += 1
                    st.success("✅ Booking created!")
                    st.rerun()

# === TAB 3: Cafe POS ===
with tab3:
    st.subheader("🍔 Hunger Monkey Cafe POS")
    
    # Live cart
    if st.session_state.cafe_cart:
        cart_df = pd.DataFrame(st.session_state.cafe_cart)
        st.dataframe(cart_df, use_container_width=True)
        st.metric("Cart Total", f"₹{cart_df['sell_price'].sum():.0f}")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Menu grid
        for category, items in CAFE_MENU.items():
            st.subheader(category)
            cols = st.columns(2)
            for idx, (item_name, prices) in enumerate(items.items()):
                col_idx = idx % 2
                with cols[col_idx]:
                    if st.button(f"{item_name}\n₹{prices['sell']}", 
                               key=f"menu_{item_name}_{st.session_state.form_reset}",
                               use_container_width=True):
                        st.session_state.cafe_cart.append({
                            'item': item_name,
                            'sell_price': prices['sell'],
                            'cost_price': prices['cost']
                        })
                        st.rerun()
        
        # Custom item
        with st.expander("➕ Custom Item"):
            custom_name = st.text_input("Item Name", key=f"custom_name_{st.session_state.form_reset}")
            custom_sell = st.number_input("Sell Price", key=f"custom_sell_{st.session_state.form_reset}")
            custom_cost = st.number_input("Cost Price", key=f"custom_cost_{st.session_state.form_reset}")
            if st.button("Add Custom", key=f"add_custom_{st.session_state.form_reset}"):
                st.session_state.cafe_cart.append({
                    'item': custom_name,
                    'sell_price': custom_sell,
                    'cost_price': custom_cost
                })
                st.rerun()
    
    with col2:
        # Customer assignment
        active_players = st.session_state.active_sales['customer'].tolist() if not st.session_state.active_sales.empty else []
        customer_type = st.selectbox("Assign to:", 
                                   ["Walk-in (Cafe Only)"] + active_players,
                                   key=f"assign_{st.session_state.form_reset}")
        
        if st.button("💳 Process Order", type="primary", use_container_width=True, 
                    disabled=len(st.session_state.cafe_cart) == 0):
            if st.session_state.cafe_cart:
                cart_df = pd.DataFrame(st.session_state.cafe_cart)
                total_revenue = cart_df['sell_price'].sum()
                total_cost = cart_df['cost_price'].sum()
                profit = total_revenue - total_cost
                items_json = json.dumps([row['item'] for _, row in cart_df.iterrows()])
                
                # ALWAYS log to cafe_orders
                conn.query(f"""
                    INSERT INTO cafe_orders (date, time, customer, items, total_revenue, 
                                          total_cost, profit, method)
                    VALUES ('{get_today_date()}', '{get_time_12hr()}', '{customer_type}', 
                           '{items_json}', {total_revenue}, {total_cost}, {profit}, 'Processed')
                """)
                
                # IF assigned to gamer, update their sales row
                if customer_type != "Walk-in (Cafe Only)" and not st.session_state.active_sales.empty:
                    gamer_row = st.session_state.active_sales[
                        st.session_state.active_sales['customer'] == customer_type
                    ].iloc[0]
                    
                    current_fnb_items = sanitize_for_supabase(gamer_row['fnb_items']) or "[]"
                    current_fnb_total = sanitize_for_supabase(gamer_row['fnb_total']) or 0.0
                    
                    new_items = json.loads(current_fnb_items) if current_fnb_items else []
                    new_items.extend([row['item'] for _, row in cart_df.iterrows()])
                    
                    conn.query(f"""
                        UPDATE sales SET 
                        fnb_items = '{json.dumps(new_items)}',
                        fnb_total = {current_fnb_total + total_revenue}
                        WHERE id = {gamer_row['id']}
                    """)
                
                st.session_state.cafe_cart = []
                st.session_state.form_reset += 1
                st.success("✅ Order processed!")
                st.rerun()

# === TAB 4: Master Vault (Admin) ===
with tab4:
    if st.button("🔐 Enter Admin Mode", type="primary"):
        pass
    
    admin_pass = st.text_input("Admin Passcode", type="password")
    if admin_pass == "Admin@2026":
        st.success("✅ Access Granted!")
        
        # WTD/MTD Gaming Revenue
        today_sales = conn.query_df(f"SELECT SUM(total) as gaming_today FROM sales WHERE DATE(date) = '{get_today_date()}' AND status = 'Completed'")
        gaming_today = sanitize_for_supabase(today_sales['gaming_today'].iloc[0])
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("WTD Gaming Revenue", f"₹{gaming_today:.0f}")
        with col2:
            month_sales = conn.query_df(f"SELECT SUM(total) as gaming_month FROM sales WHERE MONTH(date) = {now.month} AND YEAR(date) = {now.year} AND status = 'Completed'")
            st.metric("MTD Gaming Revenue", f"₹{sanitize_for_supabase(month_sales['gaming_month'].iloc[0]):.0f}")
        
        # F&B Vendor Dashboard
        st.subheader("🍔 F&B Vendor Payout Dashboard")
        cafe_today = conn.query_df(f"SELECT * FROM cafe_orders WHERE date = '{get_today_date()}'")
        if not cafe_today.empty:
            rev, cost, profit = cafe_today['total_revenue'].sum(), cafe_today['total_cost'].sum(), cafe_today['profit'].sum()
            col1, col2, col3 = st.columns(3)
            with col1: st.metric("Total Revenue", f"₹{rev:.0f}")
            with col2: st.metric("Vendor Owed (70%)", f"₹{cost:.0f}")
            with col3: st.metric("Cafe Profit (30%)", f"₹{profit:.0f}")
        
        # Master P&L
        st.subheader("📊 Master P&L")
        expenses_today = conn.query_df(f"SELECT SUM(amount) as total_exp FROM expenses WHERE expense_date = '{get_today_date()}'")
        net_profit = gaming_today + profit - sanitize_for_supabase(expenses_today['total_exp'].iloc[0] if not expenses_today.empty else 0)
        st.metric("Today's Net Profit", f"₹{net_profit:.0f}", delta_color="normal")
    else:
        st.warning("⚠️ Enter passcode to access admin dashboard")

# Add expenses form (simple)
with st.expander("➕ Quick Expense"):
    with st.form("expense_form"):
        exp_date = st.date_input("Date", value=now.date())
        category = st.selectbox("Category", ["Rent", "Utilities", "Staff", "Misc"])
        amount = st.number_input("Amount")
        method = st.selectbox("Method", ["Cash", "UPI"])
        if st.form_submit_button("Add Expense"):
            conn.query(f"""
                INSERT INTO expenses (expense_date, category, amount, method)
                VALUES ('{exp_date}', '{category}', {amount}, '{method}')
            """)
            st.success("✅ Expense logged!")

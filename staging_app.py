import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
import json
import supabase
from st_supabase import create_supabase_client  # Standard package

# Initialize session state at the VERY TOP to prevent unhashable dict errors
if 'cart' not in st.session_state:
    st.session_state.cart = []
if 'cafe_cart' not in st.session_state:
    st.session_state.cafe_cart = []
if 'form_reset' not in st.session_state:
    st.session_state.form_reset = 0
if 'active_sales' not in st.session_state:
    st.session_state.active_sales = pd.DataFrame()
if 'supabase_client' not in st.session_state:
    st.session_state.supabase_client = None

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

# Supabase Configuration - UPDATE THESE WITH YOUR CREDENTIALS
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "YOUR_SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "YOUR_SUPABASE_ANON_KEY")

@st.cache_resource
def init_supabase():
    """Initialize Supabase client"""
    try:
        client = create_supabase_client(SUPABASE_URL, SUPABASE_KEY)
        return client
    except:
        st.error("❌ Supabase connection failed. Check your secrets.toml")
        return None

def sanitize_for_supabase(value):
    """CRITICAL: Prevent NaN crashes in Supabase API"""
    if pd.isna(value) or value is None or value == "nan":
        return 0.0 if isinstance(value, (int, float, np.floating)) else ""
    if isinstance(value, float) and np.isnan(value):
        return 0.0
    return value

def df_from_supabase(table_name, filters=""):
    """Helper to fetch data as pandas DataFrame"""
    client = st.session_state.supabase_client
    if not client:
        return pd.DataFrame()
    
    try:
        response = client.table(table_name).select("*").execute()
        df = pd.DataFrame(response.data)
        return df
    except:
        return pd.DataFrame()

def update_supabase(table_name, record_id, data):
    """Helper to update record"""
    client = st.session_state.supabase_client
    if not client:
        return False
    
    try:
        client.table(table_name).update(data).eq('id', record_id).execute()
        return True
    except:
        return False

def insert_supabase(table_name, data):
    """Helper to insert record"""
    client = st.session_state.supabase_client
    if not client:
        return False
    
    try:
        client.table(table_name).insert(data).execute()
        return True
    except:
        return False

def get_today_date():
    return now.strftime("%Y-%m-%d")

def get_now_datetime():
    return now.strftime("%Y-%m-%d %H:%M:%S+05:30")

def get_time_12hr():
    return now.strftime("%I:%M %p")

def parse_time_12hr(time_str):
    """Parse 12hr time format"""
    try:
        return datetime.strptime(time_str, "%I:%M %p").time()
    except:
        return now.time()

def calculate_remaining_time(entry_time_str, duration_hours):
    """Calculate live remaining time for active sessions"""
    try:
        entry_time = parse_time_12hr(entry_time_str)
        entry_dt = now.replace(hour=entry_time.hour, minute=entry_time.minute, second=0, microsecond=0)
        end_time = entry_dt + timedelta(hours=duration_hours)
        remaining = max(0, (end_time - now).total_seconds() / 3600)
        return remaining
    except:
        return 0

def is_system_available(system, booked_date, start_time_str, duration_hours):
    """Double booking prevention logic"""
    active_df = df_from_supabase('sales', f"status=eq.Active,system=eq.{system},scheduled_date=eq.{booked_date}")
    booked_df = df_from_supabase('sales', f"status=eq.Booked,system=eq.{system},scheduled_date=eq.{booked_date}")
    return len(active_df) == 0 and len(booked_df) == 0

def calculate_gaming_price(system, hours):
    """Exact gaming pricing logic"""
    base_key = '1h' if hours >= 1 else '0.5h'
    return GAMING_PRICES.get(system, {}).get(base_key, 0)

# === MAIN APP ===
st.set_page_config(page_title="🎮 Gaming Cafe POS & ERP", layout="wide")
st.title("🎮 Gaming Cafe POS & ERP System")
st.markdown("---")

# Initialize Supabase
if st.session_state.supabase_client is None:
    st.session_state.supabase_client = init_supabase()

# Sidebar for quick stats
try:
    active_count = len(df_from_supabase('sales', "status=eq.Active"))
    today_gaming = df_from_supabase('sales', f"status=eq.Completed,date=ilike.{get_today_date()}%").assign(total=lambda x: x['total'].apply(sanitize_for_supabase))['total'].sum()
    pending_fnb = df_from_supabase('sales', "status=eq.Active").assign(fnb_total=lambda x: x['fnb_total'].apply(sanitize_for_supabase))['fnb_total'].sum()
    
    with st.sidebar:
        st.metric("Live Active Sessions", active_count)
        st.metric("Today's Gaming Revenue", f"₹{today_gaming:.0f}")
        st.metric("Pending F&B Tabs", f"₹{pending_fnb:.0f}")
except:
    st.sidebar.info("Loading stats...")

tab1, tab2, tab3, tab4 = st.tabs(["🖥️ Active Floor & Checkout", "📅 Bookings & Groups", "🍔 Cafe POS", "💰 Master Vault"])

# === TAB 1: Active Floor & Unified Checkout ===
with tab1:
    # Fetch active sales
    active_df = df_from_supabase('sales', "status=eq.Active")
    st.session_state.active_sales = active_df
    
    if not active_df.empty:
        for idx, row in active_df.iterrows():
            remaining_hrs = calculate_remaining_time(
                sanitize_for_supabase(row['entry_time']), 
                sanitize_for_supabase(row['duration'])
            )
            
            col1, col2, col3, col4 = st.columns(4)
            color = "inverse" if remaining_hrs <= 0.1 else None
            
            with col1:
                st.metric(f"**{row['customer']}**", f"{row['system']}", delta=f"{remaining_hrs:.1f}h", delta_color=color)
            with col2:
                st.metric("Gaming", f"₹{sanitize_for_supabase(row['total']):.0f}")
            with col3:
                st.metric("F&B Tab", f"₹{sanitize_for_supabase(row['fnb_total']):.0f}")
            with col4:
                if st.button(f"**Checkout**", key=f"checkout_{row.get('id', idx)}_{st.session_state.form_reset}", 
                           type="primary", use_container_width=True):
                    # Unified Checkout Modal
                    with st.container():
                        st.subheader(f"🛒 Unified Checkout: {row['customer']}")
                        
                        col_a, col_b = st.columns([1, 2])
                        with col_a:
                            final_hours = st.number_input("Final Billed Hours", 
                                                        min_value=0.0, 
                                                        value=float(sanitize_for_supabase(row['duration'])),
                                                        key=f"hours_{row.get('id', idx)}_{st.session_state.form_reset}")
                            gaming_total = calculate_gaming_price(row['system'], final_hours)
                        
                        with col_b:
                            fnb_total = float(sanitize_for_supabase(row['fnb_total']))
                            grand_total = gaming_total + fnb_total
                            st.metric("**Grand Total**", f"₹{grand_total:.0f}")
                        
                        payment_method = st.selectbox("Payment Method", 
                                                    ['Cash', 'UPI', 'Pending'],
                                                    key=f"method_{row.get('id', idx)}_{st.session_state.form_reset}")
                        
                        if st.button("✅ Complete Checkout", key=f"complete_{row.get('id', idx)}_{st.session_state.form_reset}", type="primary"):
                            # Update sales table
                            update_data = {
                                'duration': final_hours,
                                'total': gaming_total,
                                'method': payment_method,
                                'status': 'Completed'
                            }
                            if update_supabase('sales', row['id'], update_data):
                                st.session_state.form_reset += 1
                                st.success("✅ Checkout completed!")
                                st.rerun()
                            else:
                                st.error("❌ Update failed!")
    else:
        st.info("🎉 No active sessions!")

# === TAB 2: Bookings & Group Cart ===
with tab2:
    st.subheader("📅 New Booking / Group Session")
    
    with st.form("booking_form", clear_on_submit=False):
        col1, col2, col3, col4 = st.columns(4)
        with col1: customer = st.text_input("👤 Customer Name", key=f"cust_{st.session_state.form_reset}")
        with col2: phone = st.text_input("📱 Phone", key=f"phone_{st.session_state.form_reset}")
        with col3: date = st.date_input("📅 Date", value=now.date(), key=f"date_{st.session_state.form_reset}")
        with col4: start_time = st.time_input("🕐 Start Time", value=now.time(), key=f"time_{st.session_state.form_reset}")
        
        st.subheader("🛒 Group Cart")
        systems_list = list(GAMING_PRICES.keys())
        
        # Add to cart
        selected_system = st.selectbox("Add System", systems_list, key=f"sys_{st.session_state.form_reset}")
        hours = st.selectbox("Duration", [0.5, 1.0, 1.5, 2.0], key=f"dur_{st.session_state.form_reset}")
        price = calculate_gaming_price(selected_system, hours)
        st.info(f"₹{price} for {hours}h on {selected_system}")
        
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
            st.metric("**Booking Total**", f"₹{total_booking:.0f}")
            
            if st.form_submit_button("🚀 Start Session", type="primary"):
                # Double booking check
                available = True
                for _, item in cart_df.iterrows():
                    if not is_system_available(item['system'], str(date), str(start_time), item['hours']):
                        st.error(f"❌ **{item['system']}** not available on {date}!")
                        available = False
                
                if available:
                    # Insert bookings
                    for _, item in cart_df.iterrows():
                        booking_data = {
                            'date': get_now_datetime(),
                            'scheduled_date': str(date),
                            'entry_time': start_time.strftime("%I:%M %p"),
                            'customer': customer,
                            'phone': phone,
                            'system': item['system'],
                            'duration': item['hours'],
                            'total': item['price'],
                            'fnb_items': '',
                            'fnb_total': 0.0,
                            'method': 'Pending',
                            'status': 'Active'
                        }
                        insert_supabase('sales', booking_data)
                    
                    st.session_state.cart = []
                    st.session_state.form_reset += 1
                    st.success("✅ Session started!")
                    st.rerun()
                else:
                    st.error("Cannot proceed - system conflicts!")

# === TAB 3: Cafe POS ===
with tab3:
    st.subheader("🍔 Hunger Monkey Cafe POS")
    
    # Live cart display
    if st.session_state.cafe_cart:
        cart_df = pd.DataFrame(st.session_state.cafe_cart)
        st.dataframe(cart_df, use_container_width=True)
        cart_total = cart_df['sell_price'].sum()
        st.metric("**Cart Total**", f"₹{cart_total:.0f}")

    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Menu grid
        for category, items in CAFE_MENU.items():
            st.subheader(category)
            cols = st.columns(len(items))
            for idx, (item_name, prices) in enumerate(items.items()):
                with cols[idx]:
                    if st.button(f"{item_name}\n₹{prices['sell']}", 
                               key=f"menu_{item_name}_{st.session_state.form_reset}",
                               use_container_width=True, help=f"Cost: ₹{prices['cost']}"):
                        st.session_state.cafe_cart.append({
                            'item': item_name,
                            'sell_price': prices['sell'],
                            'cost_price': prices['cost']
                        })
                        st.rerun()
        
        # Custom item
        with st.expander("➕ Custom Item"):
            custom_name = st.text_input("Item Name", key=f"custom_name_{st.session_state.form_reset}")
            custom_sell = st.number_input("Sell Price ₹", min_value=0.0, key=f"custom_sell_{st.session_state.form_reset}")
            custom_cost = st.number_input("Cost Price ₹", min_value=0.0, key=f"custom_cost_{st.session_state.form_reset}")
            if st.button("➕ Add Custom Item", key=f"add_custom_{st.session_state.form_reset}"):
                st.session_state.cafe_cart.append({
                    'item': custom_name,
                    'sell_price': custom_sell,
                    'cost_price': custom_cost
                })
                st.rerun()
    
    with col2:
        # Customer assignment
        active_players = st.session_state.active_sales['customer'].unique().tolist() if not st.session_state.active_sales.empty else []
        customer_type = st.selectbox("👤 Assign to:", 
                                   ["Walk-in (Cafe Only)"] + active_players,
                                   key=f"assign_{st.session_state.form_reset}")
        
        if st.session_state.cafe_cart and st.button("💳 Process Order", type="primary", use_container_width=True):
            cart_df = pd.DataFrame(st.session_state.cafe_cart)

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
import json
from supabase import create_client, Client
import os

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

# Supabase Configuration - Put these in Streamlit Secrets (secrets.toml)
SUPABASE_URL = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL"))
SUPABASE_KEY = st.secrets.get("SUPABASE_ANON_KEY", os.getenv("SUPABASE_ANON_KEY"))

@st.cache_resource
def init_supabase():
    """Initialize Supabase client - STANDARD supabase-py"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        st.error("❌ **Supabase credentials missing!** Add to `secrets.toml`:")
        st.code("""
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_ANON_KEY = "your-anon-key"
        """)
        return None
    
    try:
        client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        # Test connection
        client.table("sales").select("count").limit(1).execute()
        st.success("✅ Supabase connected!")
        return client
    except Exception as e:
        st.error(f"❌ Supabase connection failed: {str(e)}")
        return None

def sanitize_for_supabase(value):
    """CRITICAL: Prevent NaN crashes in Supabase API"""
    if pd.isna(value) or value is None or str(value).lower() in ['nan', 'none']:
        return 0.0 if isinstance(value, (int, float)) else ""
    if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
        return 0.0
    return value

def df_from_supabase(client, table_name, filters=None):
    """Fetch data as pandas DataFrame"""
    if not client:
        return pd.DataFrame()
    
    try:
        query = client.table(table_name).select("*")
        if filters:
            query = query.eq(filters['column'], filters['value'])
        response = query.execute()
        df = pd.DataFrame(response.data)
        # Convert numeric columns
        numeric_cols = ['total', 'fnb_total', 'duration', 'profit']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].apply(sanitize_for_supabase)
        return df
    except:
        return pd.DataFrame()

def get_today_date():
    return now.strftime("%Y-%m-%d")

def get_now_datetime():
    return now.strftime("%Y-%m-%d %H:%M:%S+05:30")

def get_time_12hr():
    return now.strftime("%I:%M %p")

def calculate_remaining_time(entry_time_str, duration_hours):
    """Calculate live remaining time"""
    try:
        # Parse 12hr format
        entry_dt = datetime.strptime(entry_time_str, "%I:%M %p").replace(
            year=now.year, month=now.month, day=now.day
        )
        entry_dt = IST.localize(entry_dt)
        end_time = entry_dt + timedelta(hours=float(duration_hours))
        remaining = max(0, (end_time - now).total_seconds() / 3600)
        return remaining
    except:
        return 0

def calculate_gaming_price(system, hours):
    """Exact gaming pricing logic"""
    base_key = '1h' if hours >= 1 else '0.5h'
    return GAMING_PRICES.get(system, {}).get(base_key, 0)

# === MAIN APP ===
st.set_page_config(page_title="🎮 Gaming Cafe POS & ERP", layout="wide")
st.title("🎮 Gaming Cafe POS & ERP System")
st.caption("✅ Production Ready • Asia/Kolkata • Auto NaN Safe")

# Initialize Supabase ONCE
if st.session_state.supabase_client is None:
    st.session_state.supabase_client = init_supabase()
client = st.session_state.supabase_client

# Sidebar Stats
try:
    if client:
        active_df = df_from_supabase(client, 'sales', {'column': 'status', 'value': 'Active'})
        today_df = df_from_supabase(client, 'sales', {'column': 'status', 'value': 'Completed'})
        today_gaming = today_df['total'].sum()
        
        with st.sidebar:
            st.metric("👥 Live Sessions", len(active_df))
            st.metric("💰 Gaming Today", f"₹{today_gaming:.0f}")
            pending_fnb = active_df['fnb_total'].sum()
            st.metric("🍔 Pending F&B", f"₹{pending_fnb:.0f}")
except:
    st.sidebar.info("📊 Stats loading...")

tab1, tab2, tab3, tab4 = st.tabs(["🖥️ Active Floor", "📅 Bookings", "🍔 Cafe POS", "💰 Dashboard"])

# === TAB 1: Active Floor ===
with tab1:
    active_df = df_from_supabase(client, 'sales', {'column': 'status', 'value': 'Active'})
    st.session_state.active_sales = active_df
    
    if not active_df.empty:
        for idx, row in active_df.iterrows():
            remaining = calculate_remaining_time(row['entry_time'], row['duration'])
            is_overdue = remaining <= 0
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(row['customer'], f"{row['system']}", 
                         delta=f"{remaining:.1f}h", 
                         delta_color="inverse" if is_overdue else "normal")
            with col2: st.metric("Gaming", f"₹{row['total']:.0f}")
            with col3: st.metric("F&B", f"₹{row['fnb_total']:.0f}")
            with col4:
                if st.button("🛒 Checkout", key=f"chk_{row['id']}_{st.session_state.form_reset}"):
                    with st.container():
                        st.subheader(f"Checkout: {row['customer']}")
                        hrs = st.number_input("Hours", value=float(row['duration']), 
                                            key=f"hrs_{row['id']}")
                        gaming_total = calculate_gaming_price(row['system'], hrs)
                        fnb_total = float(row['fnb_total'])
                        grand_total = gaming_total + fnb_total
                        
                        st.metric("Grand Total", f"₹{grand_total:.0f}")
                        method = st.selectbox("Method", ['Cash', 'UPI'])
                        
                        if st.button("Complete", key=f"comp_{row['id']}_{st.session_state.form_reset}"):
                            update_data = {
                                'duration': hrs,
                                'total': gaming_total,
                                'method': method,
                                'status': 'Completed'
                            }
                            if client.table('sales').update(update_data).eq('id', row['id']).execute():
                                st.session_state.form_reset += 1
                                st.rerun()
    else:
        st.balloons()
        st.success("🎉 Floor is clear!")

# === TAB 2: Bookings ===
with tab2:
    with st.form("booking"):
        col1, col2, col3, col4 = st.columns(4)
        customer = col1.text_input("Name")
        phone = col2.text_input("Phone")
        date = col3.date_input("Date", value=now.date())
        time_str = col4.time_input("Time", value=now.time()).strftime("%I:%M %p")
        
        st.subheader("Cart")
        sys = st.selectbox("System", list(GAMING_PRICES.keys()))
        dur = st.selectbox("Hours", [0.5, 1, 1.5, 2])
        price = calculate_gaming_price(sys, dur)
        st.info(f"₹{price}")
        
        if st.button("Add"):
            st.session_state.cart.append({'sys': sys, 'dur': dur, 'price': price})
            st.rerun()
        
        if st.session_state.cart:
            df = pd.DataFrame(st.session_state.cart)
            st.dataframe(df)
            if st.form_submit_button("Start Session"):
                for item in st.session_state.cart:
                    data = {
                        'date': get_now_datetime(),
                        'scheduled_date': str(date),
                        'entry_time': time_str,
                        'customer': customer,
                        'phone': phone,
                        'system': item['sys'],
                        'duration': item['dur'],
                        'total': item['price'],
                        'fnb_items': '',
                        'fnb_total': 0.0,
                        'status': 'Active'
                    }
                    client.table('sales').insert(data).execute()
                st.session_state.cart = []
                st.success("✅ Started!")
                st.rerun()

# === TAB 3: Cafe POS ===
with tab3:
    if st.session_state.cafe_cart:
        df = pd.DataFrame(st.session_state.cafe_cart)
        st.dataframe(df)
        st.metric("Total", f"₹{df['sell'].sum():.0f}")
    
    cols = st.columns(3)
    idx = 0
    for cat, items in CAFE_MENU.items():
        with cols[idx % 3]:
            st.subheader(cat[:10])
            for name, prices in list(items.items())[:3]:
                if st.button(f"{name[:12]}\n₹{prices['sell']}", key=f"{name}_{st.session_state.form_reset}"):
                    st.session_state.cafe_cart.append({
                        'item': name, 'sell': prices['sell'], 'cost': prices['cost']
                    })
                    st.rerun()
            idx += 1
    
    # Process order
    customers = ['Walk-in'] + st.session_state.active_sales['customer'].tolist()
    customer = st.selectbox("Customer", customers, key=f"cust_{st.session_state.form_reset}")
    
    if st.session_state.cafe_cart and st.button("Process Order"):
        cart_df = pd.DataFrame(st.session_state.cafe_cart)
        total_rev = cart_df['sell'].sum()
        total_cost = cart_df['cost'].sum()
        profit = total_rev - total_cost
        
        # Log to cafe_orders
        order_data = {
            'date': get_today_date(),
            'time': get_time_12hr(),
            'customer': customer,
            'items': json.dumps(cart_df['item'].tolist()),
            'total_revenue': total_rev,
            'total_cost': total_cost,
            'profit': profit,
            'method': 'POS'
        }
        client.table('cafe_orders').insert(order_data).execute()
        
        # Update gamer tab if applicable
        if customer != 'Walk-in' and customer in st.session_state.active_sales['customer'].values:
            gamer_row = st.session_state.active_sales[st.session_state.active_sales['customer'] == customer].iloc[0]
            client.table('sales').update({
                'fnb_total': float(gamer_row['fnb_total']) + total_rev,
                'fnb_items': json.dumps(cart_df['item'].tolist())
            }).eq('id', gamer_row['id']).execute()
        
        st.session_state.cafe_cart = []
        st.success("✅ Order processed!")
        st.rerun()

# === TAB 4: Dashboard ===
with tab4:
    if st.text_input("Passcode", type="password") == "Admin@2026":
        # Today's stats
        today_sales = df_from_supabase(client, 'sales', {'column': 'status', 'value': 'Completed'})
        today_cafe = df_from_supabase(client, 'cafe_orders')
        today_exp = df_from_supabase(client, 'expenses')
        
        gaming_rev = today_sales['total'].sum()
        cafe_profit = today_cafe['profit'].sum()
        vendor_owed = today_cafe['total_cost'].sum()
        expenses = today_exp['amount'].sum()
        net_profit = gaming_rev + cafe_profit - expenses
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("🎮 Gaming", f"₹{gaming_rev:.0f}")
        col2.metric("🍔 Cafe Profit", f"₹{cafe_profit:.0f}")
        col3.metric("💸 Vendor Owed", f"₹{vendor_owed:.0f}")
        col4.metric("💰 Net Profit", f"₹{net_profit:.0f}", delta_color="normal")
        
        st.dataframe(today_cafe)
    else:
        st.info("🔐 Enter passcode: **Admin@2026**")

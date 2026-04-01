import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import datetime, timedelta
import pytz
from streamlit_autorefresh import st_autorefresh

# --- 1. CRM STYLE & CONFIG ---
st.set_page_config(page_title="Gamerarena CRM", page_icon="🎮", layout="wide")
st_autorefresh(interval=60000, limit=None, key="crm_refresh")

st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }
    .stButton>button { background: #4F46E5; color: white; border-radius: 6px; width: 100%; font-weight: 600; border: none; transition: 0.2s; }
    .stButton>button:hover { background: #4338CA; box-shadow: 0 4px 6px rgba(0,0,0,0.2); transform: translateY(-1px); }
    .pos-btn>button { background: #2B2B40; color: #E0E7FF; border: 1px solid #4F46E5; height: 60px; font-size: 14px; white-space: normal; }
    .pos-btn>button:hover { background: #4F46E5; }
    .crm-card { background-color: #1E1E2D; padding: 20px; border-radius: 8px; border-left: 4px solid #4F46E5; margin-bottom: 12px; }
    .warning-card { background-color: #2D1E1E; padding: 20px; border-radius: 8px; border-left: 4px solid #EF4444; margin-bottom: 12px; }
    .overdue-card { background-color: #2D1E1E; padding: 20px; border-radius: 8px; border-left: 4px solid #B91C1C; margin-bottom: 12px; border: 1px solid #EF4444; }
    .metric-box { background-color: #1E1E2D; padding: 20px; border-radius: 8px; text-align: center; border: 1px solid #2B2B40; }
</style>
""", unsafe_allow_html=True)

# --- 2. STATE MANAGEMENT & AUTH ---
IST = pytz.timezone('Asia/Kolkata')

if "auth" not in st.session_state: st.session_state.auth = False
if "cart" not in st.session_state: st.session_state.cart = []
if "cafe_cart" not in st.session_state: st.session_state.cafe_cart = [] 
if "form_reset" not in st.session_state: st.session_state.form_reset = 0

if not st.session_state.auth:
    st.title("🔒 Gamerarena Central Login")
    pwd = st.text_input("Enter Staff Passcode", type="password")
    if st.button("Login"):
        if pwd == "Admin@2026":
            st.session_state.auth = True; st.rerun()
        else: st.error("❌ Invalid Passcode")
    st.stop()

# --- 3. DATABASE & PRICING ---
try: conn = st.connection("supabase", type=SupabaseConnection)
except: st.error("Database Connection Error."); st.stop()

SYSTEMS = {"PS1":"PS5", "PS2":"PS5", "PS3":"PS5", "PC1":"PC", "PC2":"PC", "SIM1":"Racing Sim"}

def get_price(cat, dur, extra=0):
    if cat == "PS5": return (int(dur) * (150 + (extra * 100))) + ((1 if (dur % 1) != 0 else 0) * (100 + (extra * 100)))
    elif cat == "PC": return (int(dur) * 100) + ((1 if (dur % 1) != 0 else 0) * 70)
    elif cat == "Racing Sim": return (int(dur) * 250) + ((1 if (dur % 1) != 0 else 0) * 150)
    return 0

# EXACT HARDCODED MENU (Selling Price vs Vendor Cost)
CAFE_MENU = {
    "🍟 Finger Food & Fries": {
        "Veggie Nuggets": {"sell": 209, "cost": 160},
        "Chilli Garlic Bites": {"sell": 209, "cost": 160},
        "Veg Cheese Balls": {"sell": 229, "cost": 180},
        "Jalapeno Poppers": {"sell": 230, "cost": 180},
        "Pizza Fingers": {"sell": 229, "cost": 170},
        "Salted French Fries": {"sell": 139, "cost": 100},
        "Peri-Peri French Fries": {"sell": 159, "cost": 120},
        "Chilli Garlic French Fries": {"sell": 169, "cost": 130},
        "Cheesy French Fries": {"sell": 179, "cost": 140}
    },
    "🍔 Burgers & Meals": {
        "Tikki Tango Burger": {"sell": 89, "cost": 50},
        "Tikki Tango Meal": {"sell": 199, "cost": 149},
        "Peri Peri Mini Burger": {"sell": 119, "cost": 69},
        "Peri Peri Mini Meal": {"sell": 229, "cost": 169},
        "Paneer Pataka Burger": {"sell": 230, "cost": 95},
        "Paneer Pataka Meal": {"sell": 229, "cost": 169},
        "Big Crunch Burger": {"sell": 229, "cost": 99},
        "Big Crunch Meal": {"sell": 239, "cost": 179}
    },
    "🥤 Shakes & Coffee": {
        "Cold Coffee": {"sell": 129, "cost": 99},
        "Vanilla Milkshake": {"sell": 149, "cost": 120},
        "Irish Cold Coffee": {"sell": 159, "cost": 130},
        "Cold Chocolate": {"sell": 169, "cost": 139},
        "Oreo Milkshake": {"sell": 179, "cost": 150}
    },
    "🍹 Mocktails": {
        "Blue Lagoon": {"sell": 129, "cost": 99},
        "Green Apple Mojito": {"sell": 129, "cost": 99},
        "Lime Ice Tea": {"sell": 129, "cost": 99},
        "Mint Mojito": {"sell": 129, "cost": 99},
        "Chilli Guava": {"sell": 129, "cost": 99},
        "Black Current": {"sell": 129, "cost": 99},
        "Watermelon": {"sell": 129, "cost": 99},
        "Paan": {"sell": 129, "cost": 99},
        "Pineapple": {"sell": 129, "cost": 99},
        "Blueberry": {"sell": 129, "cost": 99}
    }
}

# --- 4. TABS ---
t1, t2, t_cafe, t3, t4, t5 = st.tabs(["🕹️ Active Floor", "📝 Bookings", "🍔 Cafe POS", "📊 Daily Summary", "📅 Reports", "🧠 Vault"])

# ==========================================
# TAB 1 & TAB 2 (EXISTING GAMING FLOOR LOGIC)
# ==========================================
with t1:
    st.subheader("🕹️ Live Timers")
    try:
        res = conn.table("sales").select("*").eq("status", "Active").execute()
        active_df = pd.DataFrame(res.data)
        if not active_df.empty:
            for _, row in active_df.iterrows():
                try:
                    entry_dt = pd.to_datetime(f"{row['date'][:10]} {row['entry_time']}").tz_localize(IST)
                    time_left = ((entry_dt + timedelta(hours=row['duration'])) - datetime.now(IST)).total_seconds() / 60.0
                except: time_left = 999 
                if time_left < 0: cc, txt = "overdue-card", f"🚨 OVERDUE ({abs(int(time_left))}m)"
                elif time_left <= 5: cc, txt = "warning-card", f"⚠️ {int(time_left)}m REMAINING"
                else: cc, txt = "crm-card", f"⏳ {int(time_left)}m remaining"
                st.markdown(f"<div class='{cc}'><h4 style='margin:0;color:#E0E7FF;'>{row['system']} | {row['customer']}</h4><p style='margin:5px 0 0 0;color:#9CA3AF;'>In: {row['entry_time']} | {row['duration']} Hrs | ₹{row['total']}<br><b style='color:#FCD34D;'>{txt}</b></p></div>", unsafe_allow_html=True)
            
            st.write("### Manage Floor")
            active_df['lbl'] = active_df['customer'] + " | " + active_df['system']
            sel = st.selectbox("Select Player", active_df['lbl'].tolist(), label_visibility="collapsed")
            row = active_df[active_df['lbl'] == sel].iloc[0]
            ca, cb = st.columns(2)
            with ca:
                ext = st.number_input("Extra Hrs", 0.5, 5.0, 0.5)
                if st.button("➕ Extend Session", use_container_width=True):
                    new_dur = float(row['duration']) + float(ext)
                    new_total = float(row['total']) + float(get_price(SYSTEMS[row['system']], ext, 0))
                    conn.table("sales").update({"total": new_total, "duration": new_dur}).eq("id", int(row['id'])).execute()
                    st.rerun()
            with cb:
                try: played_mins = int((datetime.now(IST) - pd.to_datetime(f"{row['date'][:10]} {row['entry_time']}").tz_localize(IST)).total_seconds() / 60.0)
                except: played_mins = 0
                rec_dur = float(row['duration'])
                if played_mins <= 40 and row['duration'] >= 1.0: rec_dur = 0.5
                elif played_mins > 40 and played_mins <= 60 and row['duration'] > 1.0: rec_dur = 1.0
                
                chk_1, chk_2 = st.columns(2)
                f_dur = chk_1.number_input("Billed Hrs", 0.5, 12.0, float(rec_dur), 0.5)
                f_total = chk_2.number_input("Final Bill (₹)", 0, 10000, int(row['total']), 10)
                pay = st.radio("Pay Method", ["Cash", "UPI"], horizontal=True, label_visibility="collapsed")
                if st.button("🛑 Confirm & Close", type="primary", use_container_width=True):
                    conn.table("sales").update({"status": "Completed", "method": pay, "duration": float(f_dur), "total": float(f_total)}).eq("id", int(row['id'])).execute()
                    st.balloons(); st.rerun()
        else: st.info("Floor is clear.")
    except: st.write("Loading floor...")

with t2:
    col_form, col_cart = st.columns([1.2, 1], gap="large")
    with col_form:
        st.subheader("Booking Terminal")
        with st.container(border=True):
            name = st.text_input("Gamer Name", key=f"name_{st.session_state.form_reset}")
            sch_date = datetime.now(IST).strftime('%Y-%m-%d')
            time_str = datetime.now(IST).strftime("%I:%M %p")
            
            sys_col, dur_col, ctrl_col = st.columns([2, 1, 1])
            sel_sys = sys_col.selectbox("Hardware", list(SYSTEMS.keys()), key=f"sys_{st.session_state.form_reset}")
            dur = dur_col.number_input("Hours", 0.5, 12.0, 1.0, 0.5, key=f"dur_{st.session_state.form_reset}")
            ctrl = ctrl_col.number_input("Extra Ctrl", 0, 3, 0, key=f"ctrl_{st.session_state.form_reset}") if "PS" in sel_sys else 0
            
            if st.button("➕ Add to Cart", use_container_width=True):
                st.session_state.cart.append({"system": sel_sys, "duration": dur, "price": get_price(SYSTEMS[sel_sys], dur, ctrl)})
                st.rerun()

    with col_cart:
        st.subheader("🛒 Cart")
        with st.container(border=True):
            if st.session_state.cart:
                for i, item in enumerate(st.session_state.cart):
                    c1, c2, c3 = st.columns([3, 1.5, 1])
                    c1.write(f"🎮 **{item['system']}** ({item['duration']}h)")
                    c2.write(f"₹{item['price']}")
                    if c3.button("❌", key=f"del_{i}_{st.session_state.form_reset}"):
                        st.session_state.cart.pop(i); st.rerun()
                st.markdown(f"### Total: ₹{sum(item['price'] for item in st.session_state.cart)}")
                
                if st.button("🚀 Start Session Now", type="primary", use_container_width=True):
                    if not name: st.error("Provide a Name.")
                    else:
                        for item in st.session_state.cart:
                            conn.table("sales").insert({
                                "customer": name, "system": item['system'], "duration": float(item['duration']), 
                                "total": float(item['price']), "method": "Pending", 
                                "entry_time": time_str, "status": "Active", "scheduled_date": sch_date
                            }).execute()
                        st.session_state.cart = []; st.session_state.form_reset += 1; st.rerun()
            else: st.info("Cart empty.")

# ==========================================
# TAB 3: THE CAFE POS (EXACT PRICES)
# ==========================================
with t_cafe:
    pos_grid, pos_receipt = st.columns([2, 1], gap="large")
    
    with pos_grid:
        st.subheader("🍔 Hunger Monkey Menu")
        for category, items in CAFE_MENU.items():
            with st.expander(category, expanded=True):
                cols = st.columns(4)
                for idx, (item_name, pricing) in enumerate(items.items()):
                    with cols[idx % 4]:
                        st.markdown("<div class='pos-btn'>", unsafe_allow_html=True)
                        sell_price = pricing["sell"]
                        cost_price = pricing["cost"]
                        margin = sell_price - cost_price
                        
                        if st.button(f"{item_name}\n₹{sell_price}", key=f"food_{item_name}", use_container_width=True):
                            found = False
                            for c_item in st.session_state.cafe_cart:
                                if c_item['name'] == item_name:
                                    c_item['qty'] += 1
                                    c_item['total'] = c_item['qty'] * sell_price
                                    found = True
                                    break
                            if not found:
                                st.session_state.cafe_cart.append({
                                    "name": item_name, "qty": 1, "price": sell_price, "total": sell_price,
                                    "cost": cost_price,
                                    "margin": margin
                                })
                            st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)

    with pos_receipt:
        st.subheader("🧾 Live Receipt")
        with st.container(border=True):
            c_name = st.text_input("Customer/Table Name", key=f"cafe_name_{st.session_state.form_reset}")
            st.divider()
            
            if st.session_state.cafe_cart:
                for i, item in enumerate(st.session_state.cafe_cart):
                    r_c1, r_c2, r_c3 = st.columns([3, 1, 1])
                    r_c1.write(f"{item['qty']}x {item['name']}")
                    r_c2.write(f"₹{item['total']}")
                    if r_c3.button("❌", key=f"fdel_{i}_{st.session_state.form_reset}"):
                        st.session_state.cafe_cart.pop(i); st.rerun()
                
                st.divider()
                gross_total = sum(item['total'] for item in st.session_state.cafe_cart)
                total_cost = sum(item['cost'] * item['qty'] for item in st.session_state.cafe_cart)
                total_profit = sum(item['margin'] * item['qty'] for item in st.session_state.cafe_cart)
                
                st.markdown(f"### Total: ₹{gross_total}")
                f_pay = st.radio("Payment", ["Cash", "UPI"], horizontal=True)
                
                if st.button("💸 Complete F&B Sale", type="primary", use_container_width=True):
                    if not c_name: st.error("Please enter a customer name.")
                    else:
                        items_str = ", ".join([f"{x['qty']}x {x['name']}" for x in st.session_state.cafe_cart])
                        conn.table("cafe_orders").insert({
                            "date": datetime.now(IST).strftime('%Y-%m-%d'),
                            "time": datetime.now(IST).strftime("%I:%M %p"),
                            "customer": c_name, "items": items_str,
                            "total_revenue": gross_total, "total_cost": total_cost, 
                            "profit": total_profit, "method": f_pay
                        }).execute()
                        st.session_state.cafe_cart = []
                        st.session_state.form_reset += 1
                        st.success("Food Order Processed!")
                        st.rerun()
            else:
                st.info("Tap menu items to build receipt.")

# ==========================================
# TAB 6: VAULT (WITH F&B PAYOUT LEDGER)
# ==========================================
with t5:
    st.subheader("🔐 Master Intelligence Vault")
    if st.text_input("Master Key", type="password", key="vkey") == "Shreenad@0511":
        try:
            # GAMING METRICS
            raw_v = conn.table("sales").select("*").execute()
            vdf = pd.DataFrame(raw_v.data)
            if not vdf.empty:
                vdf['date_str'] = vdf['date'].str[:10]
                comp_df = vdf[vdf['status'] == 'Completed']
                tot_gaming = comp_df['total'].sum()
                st.markdown(f"<div class='metric-box'><h4>Total Gaming Revenue</h4><h2 style='color:#34D399;'>₹{tot_gaming:,.0f}</h2></div>", unsafe_allow_html=True)
            
            st.divider()
            
            # CAFE / F&B METRICS
            st.subheader("🍔 Hunger Monkey Payout Dashboard")
            raw_c = conn.table("cafe_orders").select("*").execute()
            cdf = pd.DataFrame(raw_c.data)
            
            if not cdf.empty:
                today_str = datetime.now(IST).strftime('%Y-%m-%d')
                today_cafe = cdf[cdf['date'] == today_str]
                
                f1, f2, f3 = st.columns(3)
                f1.metric("Today's Food Sales (Gross)", f"₹{today_cafe['total_revenue'].sum():,.0f}")
                f2.metric("Cafe Profit (Net)", f"₹{today_cafe['profit'].sum():,.0f}")
                f3.metric("Owed to Vendor", f"₹{today_cafe['total_cost'].sum():,.0f}", delta="- Vendor Payout", delta_color="inverse")
                
                st.write("**Recent Food Orders**")
                st.dataframe(cdf[['date', 'time', 'customer', 'items', 'total_revenue', 'method']].sort_values('date', ascending=False), hide_index=True, use_container_width=True)
            else:
                st.caption("No food orders processed yet.")
                
        except Exception as e: st.error(f"Vault error: {e}")

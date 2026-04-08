import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import datetime, timedelta
import pytz
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIG & THEME ---
st.set_page_config(page_title="Gamerarena Unified POS", layout="wide", page_icon="🎮")
st_autorefresh(interval=30000, limit=None, key="crm_refresh")
IST = pytz.timezone('Asia/Kolkata')

C = {'bg': '#0B0E14', 'card': '#1A1F2B', 'ice': '#98DED9', 'warn': '#FF754C', 'danger': '#EF4444', 'border': '#2D3446'}

st.markdown(f"""
<style>
    .stApp {{ background-color: {C['bg']}; color: white; }}
    h1, h2, h3, h4, p, span, label {{ color: white !important; font-family: 'Inter', sans-serif; }}
    .pos-btn>button {{ background: #161922; border: 1px solid #2D3446; color: white; height: 80px; border-radius: 10px; width: 100%; transition: 0.2s; }}
    .pos-btn>button:hover {{ border-color: {C['ice']}; color: {C['ice']} !important; }}
    .action-panel {{ background: {C['card']}; padding: 20px; border-radius: 16px; border: 1px solid {C['border']}; }}
    .metric-box {{ background: #161922; padding: 15px; border-radius: 10px; border-top: 3px solid {C['ice']}; margin-bottom: 10px; }}
</style>
""", unsafe_allow_html=True)

# --- 2. STATE & DB ---
if "auth" not in st.session_state: st.session_state.auth = False
if "fnb_cart" not in st.session_state: st.session_state.fnb_cart = []
if "form_reset" not in st.session_state: st.session_state.form_reset = 0

if not st.session_state.auth:
    if st.text_input("Enter Passcode", type="password") == "Admin@2026": st.session_state.auth = True; st.rerun()
    st.stop()

try: conn = st.connection("supabase", type=SupabaseConnection)
except: st.error("Database Connection Failed."); st.stop()

SYSTEMS = {"PS1":"PS5", "PS2":"PS5", "PS3":"PS5", "PC1":"PC", "PC2":"PC", "SIM1":"Racing Sim"}
def get_price(cat, dur):
    if cat == "PS5": return (int(dur) * 150) + ((1 if (dur % 1) != 0 else 0) * 100)
    elif cat == "PC": return (int(dur) * 100) + ((1 if (dur % 1) != 0 else 0) * 70)
    elif cat == "Racing Sim": return (int(dur) * 250) + ((1 if (dur % 1) != 0 else 0) * 150)
    return 0

# Fetch Data
inv_res = conn.table("inventory").select("*").neq("category", "Sandwiches").execute()
inv_df = pd.DataFrame(inv_res.data) if inv_res.data else pd.DataFrame()
active_res = conn.table("sales").select("*").eq("status", "Active").execute()
active_df = pd.DataFrame(active_res.data) if active_res.data else pd.DataFrame()

# --- 3. TABS ---
t_floor, t_fnb, t_new, t_vault = st.tabs(["🕹️ Gaming Floor", "🍔 Food & Beverages", "📝 New Session", "🧠 Vault & Stock"])

# ==========================================
# TAB 1: GAMING FLOOR (WITH SPLIT BILLING)
# ==========================================
with t_floor:
    col_view, col_control = st.columns([2.5, 1])
    
    with col_view:
        if active_df.empty: st.info("Floor is clear.")
        else:
            grid = st.columns(3)
            for i, (_, r) in enumerate(active_df.iterrows()):
                try:
                    start = pd.to_datetime(f"{r['date'][:10]} {r['entry_time']}").tz_localize(IST)
                    elapsed = (datetime.now(IST) - start).total_seconds() / 60
                    left = int((r['duration'] * 60) - elapsed)
                    color = C['ice'] if left > 10 else (C['warn'] if left > 0 else C['danger'])
                    
                    game_cost = r['total']
                    food_cost = r.get('fnb_total') or 0
                    
                    with grid[i % 3]:
                        st.markdown(f"""
                        <div style='background:{C['card']}; padding:15px; border-radius:15px; border-top:4px solid {color}; margin-bottom:15px;'>
                            <b style='color:{color}'>{r['system']}</b> | {r['customer']}<br>
                            <h2 style='margin:5px 0;'>{left if left > 0 else 0}m left</h2>
                            <small>Game: ₹{game_cost:.0f} | Food: ₹{food_cost:.0f}</small>
                        </div>
                        """, unsafe_allow_html=True)
                except: pass

    with col_control:
        st.markdown("<div class='action-panel'>", unsafe_allow_html=True)
        st.subheader("Manage Session")
        if not active_df.empty:
            active_df['lbl'] = active_df['system'] + " - " + active_df['customer']
            sel = st.selectbox("Select Player", active_df['lbl'].tolist(), label_visibility="collapsed")
            p = active_df[active_df['lbl'] == sel].iloc[0]
            
            mode = st.radio("Action", ["Checkout", "Add Time"], horizontal=True)
            
            if mode == "Checkout":
                game_bill = p['total']
                food_bill = p.get('fnb_total') or 0
                grand_total = game_bill + food_bill
                
                st.markdown(f"""
                <div class='metric-box'>
                    <div>Gaming Bill: <span style='float:right'>₹{game_bill:.0f}</span></div>
                    <div>F&B Tab: <span style='float:right'>₹{food_bill:.0f}</span></div>
                    <hr style='margin:10px 0; border-color:#2D3446;'>
                    <h3 style='margin:0; color:{C['ice']}'>Total: <span style='float:right'>₹{grand_total:.0f}</span></h3>
                </div>
                """, unsafe_allow_html=True)
                
                meth = st.radio("Payment", ["Cash", "UPI"], horizontal=True)
                if st.button("Complete Transaction", use_container_width=True):
                    conn.table("sales").update({"status": "Completed", "method": meth, "total": float(grand_total)}).eq("id", int(p['id'])).execute()
                    st.rerun()
                    
            elif mode == "Add Time":
                h = st.number_input("Extra Hours", 0.5, 5.0, 0.5, 0.5)
                if st.button("Confirm Extension", use_container_width=True):
                    new_t = p['total'] + get_price(SYSTEMS[p['system']], h)
                    conn.table("sales").update({"total": new_t, "duration": p['duration'] + h}).eq("id", int(p['id'])).execute()
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# TAB 2: UNIFIED F&B POS (NO NUMBERS, 3 COLS)
# ==========================================
with t_fnb:
    st.subheader("Food & Beverage System")
    col_menu, col_cart = st.columns([2.5, 1], gap="large")
    
    with col_menu:
        if not inv_df.empty:
            c1, c2, c3 = st.columns(3)
            
            # 1. Hunger Monkey (Burgers & Fries)
            with c1:
                st.markdown("### 🍔 Hunger Monkey")
                hm_items = inv_df[inv_df['category'].isin(['Fries & Snacks', 'Burgers & Meals'])]
                for _, r in hm_items.iterrows():
                    st.markdown("<div class='pos-btn'>", unsafe_allow_html=True)
                    if st.button(f"{r['item_name']}\n₹{r['selling_price']:.0f}", key=f"fnb_{r['id']}", use_container_width=True):
                        st.session_state.fnb_cart.append({"name": r['item_name'], "price": r['selling_price'], "cost": r['cost_price']})
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
            
            # 2. Beverages
            with c2:
                st.markdown("### 🥤 Beverages")
                bev_items = inv_df[inv_df['category'].isin(['Beverages', 'Mocktails'])]
                for _, r in bev_items.iterrows():
                    st.markdown("<div class='pos-btn'>", unsafe_allow_html=True)
                    if st.button(f"{r['item_name']}\n₹{r['selling_price']:.0f}", key=f"fnb_{r['id']}", use_container_width=True):
                        st.session_state.fnb_cart.append({"name": r['item_name'], "price": r['selling_price'], "cost": r['cost_price']})
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
            
            # 3. Chips & BYOB
            with c3:
                st.markdown("### 🍟 Chips & BYOB")
                chips_items = inv_df[inv_df['category'] == 'Chips']
                for _, r in chips_items.iterrows():
                    st.markdown("<div class='pos-btn'>", unsafe_allow_html=True)
                    if st.button(f"{r['item_name']}\n₹{r['selling_price']:.0f}", key=f"fnb_{r['id']}", use_container_width=True):
                        st.session_state.fnb_cart.append({"name": r['item_name'], "price": r['selling_price'], "cost": r['cost_price']})
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
                
                # BYOB SPECIAL MODULE
                st.markdown("<div style='background:#2D3446; padding:15px; border-radius:10px; margin-top:15px;'>", unsafe_allow_html=True)
                st.write("**Build Your Own Bag (BYOB)**")
                chip_choice = st.selectbox("Base", ["Blue Lays", "Kurkure", "Doritos", "Uncle Chipps"])
                has_cheese = st.checkbox("Add Cheese (+₹30)")
                byob_price = 139 if has_cheese else 109
                byob_cost = 105 if has_cheese else 75
                
                if st.button(f"Add BYOB to Cart (₹{byob_price})", use_container_width=True):
                    cheese_txt = "w/ Cheese" if has_cheese else "No Cheese"
                    st.session_state.fnb_cart.append({"name": f"BYOB ({chip_choice} - {cheese_txt})", "price": byob_price, "cost": byob_cost})
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

    # F&B CART PANEL
    with col_cart:
        st.markdown("<div class='action-panel'>", unsafe_allow_html=True)
        st.subheader("🛒 Current Order")
        
        if not st.session_state.fnb_cart:
            st.info("Tap items to build order.")
        else:
            total_sell = sum([x['price'] for x in st.session_state.fnb_cart])
            total_cost = sum([x['cost'] for x in st.session_state.fnb_cart])
            items_str = " | ".join([x['name'] for x in st.session_state.fnb_cart])
            
            for i, item in enumerate(st.session_state.fnb_cart):
                c_name, c_del = st.columns([4, 1])
                c_name.write(f"• {item['name']} (₹{item['price']:.0f})")
                if c_del.button("X", key=f"del_{i}"):
                    st.session_state.fnb_cart.pop(i); st.rerun()
            
            st.markdown(f"<h3 style='color:{C['ice']}'>Total: ₹{total_sell:.0f}</h3>", unsafe_allow_html=True)
            
            assign_to = st.radio("Bill To:", ["Walk-in (Pay Now)", "Add to Active Gamer"])
            
            gamer_id = None
            if assign_to == "Add to Active Gamer":
                if not active_df.empty:
                    active_df['lbl'] = active_df['system'] + " - " + active_df['customer']
                    sel_g = st.selectbox("Select Gamer", active_df['lbl'].tolist(), label_visibility="collapsed")
                    gamer_id = int(active_df[active_df['lbl'] == sel_g].iloc[0]['id'])
                else:
                    st.warning("No active gamers.")
            
            if st.button("✅ CONFIRM ORDER", use_container_width=True):
                # 1. Always log in cafe_orders for vendor payout math
                conn.table("cafe_orders").insert({
                    "date": datetime.now(IST).strftime('%Y-%m-%d'),
                    "items": items_str, "total_revenue": total_sell, 
                    "total_cost": total_cost, "profit": total_sell - total_cost,
                    "method": "Tab" if assign_to == "Add to Active Gamer" else "Direct"
                }).execute()
                
                # 2. If gamer selected, attach to their tab
                if assign_to == "Add to Active Gamer" and gamer_id:
                    current = conn.table("sales").select("fnb_items, fnb_total").eq("id", gamer_id).execute()
                    old_i = current.data[0]['fnb_items'] or ""
                    old_t = current.data[0]['fnb_total'] or 0
                    conn.table("sales").update({
                        "fnb_items": f"{old_i} | {items_str}" if old_i else items_str,
                        "fnb_total": float(old_t + total_sell)
                    }).eq("id", gamer_id).execute()
                    st.success("Added to Gamer's Tab!")
                else:
                    st.success("Walk-in Order Processed!")
                
                # Clear cart
                st.session_state.fnb_cart = []
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# TAB 3 & 4: NEW SESSION & VAULT
# ==========================================
with t_new:
    st.subheader("Start Gaming Session")
    n1, n2 = st.columns(2)
    name = n1.text_input("Customer Name", key=f"n_{st.session_state.form_reset}")
    sys = n2.selectbox("Hardware", list(SYSTEMS.keys()))
    dur = n1.number_input("Hours", 0.5, 10.0, 1.0, 0.5)
    if st.button("🚀 LAUNCH SESSION"):
        if name:
            conn.table("sales").insert({
                "customer": name, "system": sys, "duration": dur, "total": float(get_price(SYSTEMS[sys], dur)), 
                "status": "Active", "date": datetime.now(IST).isoformat(), "scheduled_date": datetime.now(IST).strftime('%Y-%m-%d'), 
                "entry_time": datetime.now(IST).strftime("%I:%M %p")
            }).execute()
            st.session_state.form_reset += 1; st.rerun()

with t_vault:
    st.subheader("Financial Vault")
    if st.text_input("Vault Passcode", type="password") == "Shreenad@0511":
        st.write("### Today's Performance")
        raw = conn.table("sales").select("*").execute()
        df = pd.DataFrame(raw.data)
        if not df.empty:
            df['date_str'] = df['date'].str[:10]
            today = datetime.now(IST).strftime('%Y-%m-%d')
            comp = df[(df['date_str'] == today) & (df['status'] == 'Completed')]
            
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"<div class='metric-box'>Total Gaming Income<br><h2 style='color:{C['ice']}'>₹{comp['total'].sum():,.0f}</h2></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='metric-box'>Total Cash<br><h2>₹{comp[comp['method']=='Cash']['total'].sum():,.0f}</h2></div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='metric-box'>Total UPI<br><h2>₹{comp[comp['method']!='Cash']['total'].sum():,.0f}</h2></div>", unsafe_allow_html=True)
        
        st.divider()
        st.write("### F&B Vendor Payouts")
        sales_res = conn.table("cafe_orders").select("*").execute()
        sdf = pd.DataFrame(sales_res.data)
        if not sdf.empty:
            rev = sdf['total_revenue'].sum()
            cost = sdf['total_cost'].sum()
            prof = rev - cost
            m1, m2, m3 = st.columns(3)
            m1.metric("F&B Gross Sold", f"₹{rev:,.0f}")
            m2.metric("Owed to Vendor (Cost)", f"₹{cost:,.0f}")
            m3.metric("Net F&B Profit", f"₹{prof:,.0f}")

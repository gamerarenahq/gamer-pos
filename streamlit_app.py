import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import datetime, timedelta
import pytz
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIG & UI THEME ---
st.set_page_config(page_title="Gamerarena Master ERP", page_icon="🎮", layout="wide")
st_autorefresh(interval=60000, limit=None, key="crm_refresh")
IST = pytz.timezone('Asia/Kolkata')

st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; font-family: 'Inter', sans-serif; }
    .stApp { background-color: #0B0E14; color: white; }
    h1, h2, h3, h4, p, span, label { color: white !important; }
    .stButton>button { background: #4F46E5; color: white; border-radius: 8px; width: 100%; font-weight: 600; border: none; transition: 0.2s; }
    .stButton>button:hover { background: #4338CA; transform: translateY(-2px); }
    .crm-card { background-color: #1A1F2B; padding: 20px; border-radius: 12px; border-left: 4px solid #98DED9; margin-bottom: 12px; }
    .warning-card { background-color: #1A1F2B; padding: 20px; border-radius: 12px; border-left: 4px solid #FF754C; margin-bottom: 12px; }
    .overdue-card { background-color: #2D1E1E; padding: 20px; border-radius: 12px; border-left: 4px solid #EF4444; margin-bottom: 12px; }
    .metric-box { background-color: #1A1F2B; padding: 20px; border-radius: 12px; text-align: center; border-top: 3px solid #98DED9; }
    .panel-box { background: #1A1F2B; padding: 20px; border-radius: 16px; border: 1px solid #2D3446; }
    .menu-btn>button { background: #161922; border: 1px solid #2D3446; height: 70px; border-radius: 10px; }
    .menu-btn>button:hover { border-color: #98DED9; color: #98DED9 !important; }
</style>
""", unsafe_allow_html=True)

# --- 2. STATE & AUTH ---
if "auth" not in st.session_state: st.session_state.auth = False
if "cart" not in st.session_state: st.session_state.cart = []
if "fnb_cart" not in st.session_state: st.session_state.fnb_cart = []
if "form_reset" not in st.session_state: st.session_state.form_reset = 0

if not st.session_state.auth:
    st.title("🔒 Gamerarena Central Login")
    if st.text_input("Enter Passcode", type="password") == "Admin@2026":
        st.session_state.auth = True; st.rerun()
    st.stop()

# --- 3. DATABASE SETUP ---
try: conn = st.connection("supabase", type=SupabaseConnection)
except: st.error("Database Connection Error."); st.stop()

SYSTEMS = {"PS1":"PS5", "PS2":"PS5", "PS3":"PS5", "PC1":"PC", "PC2":"PC", "SIM1":"Racing Sim"}

def get_price(cat, dur, extra=0):
    if cat == "PS5": return (int(dur) * (150 + (extra * 100))) + ((1 if (dur % 1) != 0 else 0) * (100 + (extra * 100)))
    elif cat == "PC": return (int(dur) * 100) + ((1 if (dur % 1) != 0 else 0) * 70)
    elif cat == "Racing Sim": return (int(dur) * 250) + ((1 if (dur % 1) != 0 else 0) * 150)
    return 0

inv_cols = ["id", "item_name", "category", "cost_price", "selling_price", "stock_level"]
db_cols = ["id", "customer", "phone", "system", "duration", "total", "method", "entry_time", "status", "scheduled_date", "fnb_total", "fnb_items", "date"]

try:
    inv_res = conn.table("inventory").select("*").order('item_name').execute()
    inv_df = pd.DataFrame(inv_res.data) if inv_res.data else pd.DataFrame(columns=inv_cols)
    
    active_res = conn.table("sales").select("*").in_("status", ["Active", "Booked"]).execute()
    db_df = pd.DataFrame(active_res.data) if active_res.data else pd.DataFrame(columns=db_cols)
except Exception as e:
    st.error(f"Syncing Database... {e}")
    inv_df = pd.DataFrame(columns=inv_cols)
    db_df = pd.DataFrame(columns=db_cols)

# --- 4. TABS LAYOUT ---
t1, t2, t3, t4, t5 = st.tabs(["🕹️ Live Floor", "🍔 Cafe & Stock", "📅 Bookings & Queue", "📊 Daily Snapshot", "🧠 Master Vault"])

# ==========================================
# TAB 1: LIVE FLOOR & CHECKOUT
# ==========================================
with t1:
    col_floor, col_op = st.columns([2.5, 1], gap="large")
    active_gamers = db_df[db_df['status'] == 'Active'] if not db_df.empty else pd.DataFrame()
    
    with col_floor:
        st.subheader("Active Sessions")
        if active_gamers.empty: st.info("Floor is clear.")
        else:
            grid = st.columns(3)
            for i, (_, row) in enumerate(active_gamers.iterrows()):
                try:
                    entry_dt = pd.to_datetime(f"{row['date'][:10]} {row['entry_time']}").tz_localize(IST)
                    time_left = ((entry_dt + timedelta(hours=row['duration'])) - datetime.now(IST)).total_seconds() / 60.0
                except: time_left = 999 

                if time_left < 0: cc, txt = "overdue-card", f"🚨 {abs(int(time_left))}m OVERDUE"
                elif time_left <= 10: cc, txt = "warning-card", f"⚠️ {int(time_left)}m LEFT"
                else: cc, txt = "crm-card", f"⏳ {int(time_left)}m left"
                
                fnb_val = row.get('fnb_total') or 0
                fnb_str = f" | F&B: ₹{fnb_val:.0f}" if fnb_val > 0 else ""

                with grid[i % 3]:
                    st.markdown(f"<div class='{cc}'><h4 style='color:#98DED9; margin:0;'>{row['system']}</h4><b>{row['customer']}</b><br><span style='font-size:12px; color:#9CA3AF;'>Game: ₹{row['total']:.0f}{fnb_str}</span><h3 style='margin:5px 0;'>{txt}</h3></div>", unsafe_allow_html=True)

    with col_op:
        st.markdown("<div class='panel-box'>", unsafe_allow_html=True)
        st.subheader("Operator Panel")
        if not active_gamers.empty:
            active_gamers['lbl'] = active_gamers['customer'] + " | " + active_gamers['system']
            sel = st.selectbox("Select Gamer", active_gamers['lbl'].tolist(), label_visibility="collapsed")
            row = active_gamers[active_gamers['lbl'] == sel].iloc[0]
            
            op_mode = st.radio("Action", ["Smart Checkout", "Add Time"], horizontal=True)
            
            if op_mode == "Smart Checkout":
                try: played_mins = int((datetime.now(IST) - pd.to_datetime(f"{row['date'][:10]} {row['entry_time']}").tz_localize(IST)).total_seconds() / 60.0)
                except: played_mins = 0
                st.caption(f"⏱️ Actual Time Played: **{played_mins} mins**")
                
                rec_dur = float(row['duration'])
                if played_mins <= 40 and row['duration'] >= 1.0: rec_dur = 0.5
                elif played_mins > 40 and played_mins <= 60 and row['duration'] > 1.0: rec_dur = 1.0
                
                f_dur = st.number_input("Billed Hrs", 0.5, 12.0, float(rec_dur), 0.5)
                
                game_bill = float(row['total'])
                food_bill = float(row.get('fnb_total') or 0)
                grand_total = game_bill + food_bill
                
                st.markdown(f"<div style='background:#161922; padding:10px; border-radius:8px;'><small>Gaming: ₹{game_bill:.0f}<br>F&B Tab: ₹{food_bill:.0f}</small><h3 style='color:#98DED9; margin:0;'>Total: ₹{grand_total:.0f}</h3></div><br>", unsafe_allow_html=True)
                
                pay = st.radio("Pay Method", ["Cash", "UPI"], horizontal=True)
                if st.button("🛑 Collect & Close", type="primary"):
                    conn.table("sales").update({"status": "Completed", "method": pay, "duration": float(f_dur), "total": float(grand_total)}).eq("id", int(row['id'])).execute()
                    st.balloons(); st.rerun()
                    
            elif op_mode == "Add Time":
                ext = st.number_input("Extra Hrs", 0.5, 5.0, 0.5)
                if st.button("➕ Extend Session"):
                    new_dur = float(row['duration']) + float(ext)
                    new_total = float(row['total']) + float(get_price(SYSTEMS[row['system']], ext, 0))
                    conn.table("sales").update({"total": new_total, "duration": new_dur}).eq("id", int(row['id'])).execute()
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# TAB 2: CAFE POS & INVENTORY MANAGER
# ==========================================
with t2:
    pos_tab, inv_tab = st.tabs(["🛒 F&B Point of Sale", "📦 Stock & Inventory Manager"])
    
    with pos_tab:
        col_menu, col_cart = st.columns([2.5, 1], gap="large")
        with col_menu:
            if inv_df.empty: st.warning("Inventory is empty. Go to the Stock tab to add items.")
            else:
                cat_list = inv_df['category'].dropna().unique()
                for cat in cat_list:
                    with st.expander(f"📌 {cat}", expanded=(cat in ['Burgers & Meals', 'Fries & Snacks'])):
                        cat_items = inv_df[inv_df['category'] == cat]
                        grid = st.columns(4)
                        for i, (_, r) in enumerate(cat_items.iterrows()):
                            st.markdown("<div class='menu-btn'>", unsafe_allow_html=True)
                            label = f"{r['item_name']}\n₹{r['selling_price']:.0f}"
                            if grid[i % 4].button(label, key=f"fnb_{r['id']}", disabled=r['stock_level'] <= 0, use_container_width=True):
                                st.session_state.fnb_cart.append({"id": r['id'], "name": r['item_name'], "price": r['selling_price'], "cost": r['cost_price']})
                                st.rerun()
                            st.markdown("</div>", unsafe_allow_html=True)
                
                with st.expander("🍟 BYOB (Build Your Own Bag)"):
                    chip_choice = st.selectbox("Base Chips", ["Blue Lays", "Kurkure", "Doritos", "Uncle Chipps"])
                    has_cheese = st.checkbox("Add Cheese (+₹30)")
                    byob_p = 140 if has_cheese else 110
                    byob_c = 105 if has_cheese else 75
                    if st.button(f"Add BYOB (₹{byob_p})"):
                        txt = f"BYOB ({chip_choice} {'w/ Cheese' if has_cheese else ''})"
                        st.session_state.fnb_cart.append({"id": "byob", "name": txt, "price": byob_p, "cost": byob_c})
                        st.rerun()

        with col_cart:
            st.markdown("<div class='panel-box'>", unsafe_allow_html=True)
            st.subheader("🛒 Food Cart")
            if not st.session_state.fnb_cart: st.info("Cart is empty.")
            else:
                tot_sell = sum([x['price'] for x in st.session_state.fnb_cart])
                tot_cost = sum([x['cost'] for x in st.session_state.fnb_cart])
                items_str = " | ".join([x['name'] for x in st.session_state.fnb_cart])
                
                for i, item in enumerate(st.session_state.fnb_cart):
                    c_n, c_d = st.columns([4, 1])
                    c_n.write(f"• {item['name']} (₹{item['price']:.0f})")
                    if c_d.button("X", key=f"delf_{i}"): st.session_state.fnb_cart.pop(i); st.rerun()
                
                st.markdown(f"### Total: ₹{tot_sell:.0f}")
                
                assign = st.radio("Bill To:", ["Add to Active Gamer", "Walk-in (Pay Now)"])
                gamer_id = None
                if assign == "Add to Active Gamer":
                    if not active_gamers.empty:
                        sel_g = st.selectbox("Select Gamer", active_gamers['lbl'].tolist(), label_visibility="collapsed")
                        gamer_id = int(active_gamers[active_gamers['lbl'] == sel_g].iloc[0]['id'])
                    else: st.warning("No active gamers.")
                
                if st.button("✅ CONFIRM ORDER", use_container_width=True):
                    for item in st.session_state.fnb_cart:
                        if item['id'] != 'byob':
                            cur_stock = inv_df[inv_df['id'] == item['id']].iloc[0]['stock_level']
                            conn.table("inventory").update({"stock_level": int(cur_stock - 1)}).eq("id", item['id']).execute()
                            
                    conn.table("cafe_orders").insert({
                        "date": datetime.now(IST).strftime('%Y-%m-%d'), "items": items_str, 
                        "total_revenue": float(tot_sell), "total_cost": float(tot_cost), "profit": float(tot_sell - tot_cost),
                        "method": "Tab" if assign == "Add to Active Gamer" else "Direct"
                    }).execute()
                    
                    if assign == "Add to Active Gamer" and gamer_id:
                        cur_tab = conn.table("sales").select("fnb_items, fnb_total").eq("id", gamer_id).execute().data[0]
                        old_i = cur_tab.get('fnb_items') or ""
                        old_t = cur_tab.get('fnb_total') or 0
                        conn.table("sales").update({"fnb_items": f"{old_i} | {items_str}" if old_i else items_str, "fnb_total": float(old_t + tot_sell)}).eq("id", gamer_id).execute()
                    
                    st.session_state.fnb_cart = []; st.success("Order Processed!"); st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    with inv_tab:
        st.subheader("Manage Catalog & Stock")
        c1, c2 = st.columns(2, gap="large")
        
        with c1:
            st.write("### 📥 Refill Existing Stock")
            if not inv_df.empty:
                refill_item = st.selectbox("Select Item to Refill", inv_df['item_name'].tolist())
                refill_qty = st.number_input("Quantity Arrived", 1, 500, 10)
                if st.button("Update Stock Levels", use_container_width=True):
                    c_qty = inv_df[inv_df['item_name'] == refill_item].iloc[0]['stock_level']
                    conn.table("inventory").update({"stock_level": int(c_qty + refill_qty)}).eq("item_name", refill_item).execute()
                    st.success(f"Added stock to {refill_item}!"); st.rerun()
            
            st.write("---")
            st.write("### 🗑️ Delete Item")
            if not inv_df.empty:
                del_item = st.selectbox("Select Item to Delete", inv_df['item_name'].tolist())
                if st.button("Delete from Database", type="primary", use_container_width=True):
                    conn.table("inventory").delete().eq("item_name", del_item).execute()
                    st.warning(f"Deleted {del_item} permanently!"); st.rerun()

        with c2:
            st.write("### ➕ Add New Item")
            with st.form("new_inv"):
                n_name = st.text_input("Name (e.g., Red Bull, Snickers)")
                # Clean, straightforward categories
                n_cat = st.selectbox("Category", ["Burgers & Meals", "Fries & Snacks", "Mocktails", "Beverages", "Chips", "Cold Drinks", "Chocolates", "Other"])
                n_cost = st.number_input("Cost to you (₹)", 0)
                n_sell = st.number_input("Selling Price (₹)", 0)
                n_qty = st.number_input("Starting Stock", 0)
                if st.form_submit_button("Add to Database", use_container_width=True):
                    conn.table("inventory").insert({"item_name": n_name, "category": n_cat, "cost_price": n_cost, "selling_price": n_sell, "stock_level": n_qty}).execute()
                    st.success("Item Added!"); st.rerun()
        
        st.write("---")
        st.write("### Low Stock Alerts")
        if not inv_df.empty:
            low = inv_df[inv_df['stock_level'] <= 5]
            if not low.empty: st.error("🚨 These items need restocking immediately!")
            st.dataframe(inv_df[['item_name', 'category', 'stock_level', 'selling_price']], use_container_width=True, hide_index=True)

# ==========================================
# TAB 3: BOOKINGS, CART & QUEUE
# ==========================================
with t3:
    col_form, col_cart = st.columns([1.2, 1], gap="large")
    with col_form:
        st.subheader("1. Lead & Details")
        with st.container(border=True):
            name = st.text_input("Gamer / Group Name", key=f"name_{st.session_state.form_reset}")
            phone = st.text_input("Phone Number", key=f"phone_{st.session_state.form_reset}")
            st.write("---")
            b_type = st.radio("Booking Type", ["🏃‍♂️ Walk-in (Play Now)", "📅 Advance Booking"], horizontal=True, key=f"type_{st.session_state.form_reset}")
            
            if "Walk-in" in b_type:
                sch_date = datetime.now(IST).strftime('%Y-%m-%d')
                time_str = datetime.now(IST).strftime("%I:%M %p")
                final_status = "Active"; btn_txt = "🚀 Start Session Now"
            else:
                b_date = st.date_input("Future Date", value=datetime.now(IST).date(), min_value=datetime.now(IST).date())
                sch_date = b_date.strftime('%Y-%m-%d')
                b_time = st.time_input("Time", value=datetime.now(IST).time(), step=60)
                time_str = b_time.strftime("%I:%M %p")
                final_status = "Booked"; btn_txt = f"📅 Confirm Reservation"

        st.subheader("2. Add Hardware")
        with st.container(border=True):
            sys_col, dur_col, ctrl_col = st.columns([2, 1, 1])
            sel_sys = sys_col.selectbox("Hardware", list(SYSTEMS.keys()), key=f"sys_{st.session_state.form_reset}")
            dur = dur_col.number_input("Hours", 0.5, 12.0, 1.0, 0.5, key=f"dur_{st.session_state.form_reset}")
            ctrl = ctrl_col.number_input("Extra Ctrl", 0, 3, 0) if "PS" in sel_sys else 0
            if st.button("➕ Add to Cart", use_container_width=True):
                st.session_state.cart.append({"system": sel_sys, "duration": dur, "ctrl": ctrl, "price": get_price(SYSTEMS[sel_sys], dur, ctrl)})
                st.rerun()

    with col_cart:
        st.markdown("<div class='panel-box'>", unsafe_allow_html=True)
        st.subheader("🛒 Booking Cart")
        if st.session_state.cart:
            for i, item in enumerate(st.session_state.cart):
                c_info, c_price, c_del = st.columns([3, 1.5, 1])
                c_info.write(f"🎮 **{item['system']}** ({item['duration']}h)")
                c_price.write(f"₹{item['price']}")
                if c_del.button("❌", key=f"del_{i}_{st.session_state.form_reset}"): st.session_state.cart.pop(i); st.rerun()
            st.divider()
            st.markdown(f"### Total: ₹{sum(item['price'] for item in st.session_state.cart)}")
            
            if st.button(btn_txt, type="primary", use_container_width=True):
                if not name: st.error("Please enter a Name.")
                else:
                    conflict = False
                    if final_status == "Booked" and not db_df.empty:
                        for item in st.session_state.cart:
                            sys_df = db_df[(db_df['system'] == item['system']) & (db_df['scheduled_date'] == sch_date)]
                            if not sys_df.empty:
                                new_s = datetime.strptime(f"{sch_date} {time_str}", "%Y-%m-%d %I:%M %p")
                                new_e = new_s + timedelta(hours=item['duration'])
                                for _, r in sys_df.iterrows():
                                    db_s = datetime.strptime(f"{sch_date} {r['entry_time']}", "%Y-%m-%d %I:%M %p")
                                    db_e = db_s + timedelta(hours=r['duration'])
                                    if new_s < db_e and new_e > db_s:
                                        conflict = True; st.error(f"⚠️ Conflict on {item['system']} from {r['entry_time']} for {r['duration']}h.")
                                        break
                            if conflict: break
                    if not conflict:
                        for item in st.session_state.cart:
                            conn.table("sales").insert({"customer": name, "phone": phone, "system": item['system'], "duration": float(item['duration']), "total": float(item['price']), "method": "Pending", "entry_time": time_str, "status": final_status, "scheduled_date": sch_date}).execute()
                        st.session_state.cart = []; st.session_state.form_reset += 1; st.success("Success!"); st.rerun()
        else: st.info("Cart is empty.")
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.write("### 📅 Upcoming Bookings")
        if not db_df.empty:
            up_df = db_df[db_df['status'] == 'Booked']
            if not up_df.empty:
                st.dataframe(up_df[['scheduled_date', 'entry_time', 'customer', 'system', 'duration']], hide_index=True)
                sel_edit = st.selectbox("Cancel Booking", up_df['customer'] + " | " + up_df['system'])
                if st.button("🚫 Cancel Booking"):
                    t_id = up_df[up_df['customer'] + " | " + up_df['system'] == sel_edit].iloc[0]['id']
                    conn.table("sales").update({"status": "Cancelled"}).eq("id", int(t_id)).execute()
                    st.rerun()

# ==========================================
# TAB 4: SNAPSHOT & REPORTS
# ==========================================
with t4:
    st.subheader("📊 Today's Summary & Exports")
    try:
        raw = conn.table("sales").select("*").execute()
        df = pd.DataFrame(raw.data)
        if not df.empty:
            df['date_str'] = df['date'].str[:10] 
            today_str = datetime.now(IST).strftime('%Y-%m-%d')
            t_df = df[df['date_str'] == today_str]
            comp = t_df[t_df['status'] == 'Completed']
            m1, m2, m3, m4 = st.columns(4)
            m1.markdown(f"<div class='metric-box'>Cash Collected<h2>₹{comp[comp['method']=='Cash']['total'].sum():,.0f}</h2></div>", unsafe_allow_html=True)
            m2.markdown(f"<div class='metric-box'>UPI Collected<h2>₹{comp[comp['method']!='Cash']['total'].sum():,.0f}</h2></div>", unsafe_allow_html=True)
            m3.markdown(f"<div class='metric-box' style='border-color:#4F46E5'>Total Revenue<h2 style='color:#4F46E5'>₹{comp['total'].sum():,.0f}</h2></div>", unsafe_allow_html=True)
            m4.markdown(f"<div class='metric-box' style='border-color:#FF754C'>Pending on Floor<h2 style='color:#FF754C'>₹{t_df[t_df['status']=='Active']['total'].sum():,.0f}</h2></div>", unsafe_allow_html=True)
            
            st.divider()
            st.write("### Export Data")
            d_range = st.date_input("Select Date Range to Export", [datetime.now(IST).date(), datetime.now(IST).date()])
            if len(d_range) == 2:
                s_dt, e_dt = [d.strftime('%Y-%m-%d') for d in d_range]
                f_edf = df[(df['date_str'] >= s_dt) & (df['date_str'] <= e_dt)]
                st.download_button("📥 Export CSV", f_edf.to_csv(index=False).encode('utf-8'), f"Export_{s_dt}_to_{e_dt}.csv", "text/csv")
    except: st.error("Error loading summary.")

# ==========================================
# TAB 5: MASTER VAULT
# ==========================================
with t5:
    st.subheader("🔐 Master Intelligence Vault")
    if st.text_input("Master Key", type="password") == "Shreenad@0511":
        try:
            raw_v = conn.table("sales").select("*").execute()
            vdf = pd.DataFrame(raw_v.data)
            
            with st.expander("💸 Record Cafe Expenses", expanded=False):
                with st.form("expense_form"):
                    e_desc, e_amt, e_meth = st.columns(3)
                    desc = e_desc.text_input("Expense Details")
                    amt = e_amt.number_input("Amount (₹)", 0)
                    meth = e_meth.selectbox("Paid Via", ["Cash", "UPI"])
                    if st.form_submit_button("Log Expense"):
                        conn.table("expenses").insert({"expense_date": datetime.now(IST).strftime('%Y-%m-%d'), "category": desc, "amount": amt, "method": meth}).execute()
                        st.success("Logged!"); st.rerun()

            st.divider()
            
            st.write("### 🍔 F&B Financials")
            sales_res = conn.table("cafe_orders").select("*").execute()
            sdf = pd.DataFrame(sales_res.data)
            if not sdf.empty:
                p_col1, p_col2 = st.columns(2)
                # Clean, unified F&B numbers
                p_col1.markdown(f"<div class='metric-box' style='border-color:#EF4444'><h4>Total F&B Cost</h4><h2 style='color:#EF4444'>₹{sdf['total_cost'].sum():,.0f}</h2></div>", unsafe_allow_html=True)
                p_col2.markdown(f"<div class='metric-box'><h4>Total Net F&B Profit</h4><h2 style='color:#34D399'>₹{sdf['profit'].sum():,.0f}</h2></div>", unsafe_allow_html=True)

            st.divider()

            if not vdf.empty:
                vdf['date_str'] = vdf['date'].str[:10]
                comp_df = vdf[vdf['status'] == 'Completed'].copy()
                
                st.subheader("📅 Day-Wise Profit & Loss Ledger")
                tot_inc = comp_df.groupby('date_str')['total'].sum().rename('Gross Income').reset_index()
                
                exp_raw = conn.table("expenses").select("*").execute()
                exp_df = pd.DataFrame(exp_raw.data)
                if not exp_df.empty:
                    exp_summary = exp_df.groupby('expense_date')['amount'].sum().rename('Total Expenses').reset_index()
                    master_ledger = pd.merge(tot_inc, exp_summary, left_on='date_str', right_on='expense_date', how='outer').fillna(0)
                else:
                    master_ledger = tot_inc; master_ledger['Total Expenses'] = 0
                
                master_ledger['Net Profit'] = master_ledger['Gross Income'] - master_ledger['Total Expenses']
                master_ledger = master_ledger.sort_values('date_str', ascending=False)
                st.dataframe(master_ledger[['date_str', 'Gross Income', 'Total Expenses', 'Net Profit']], hide_index=True, use_container_width=True)

        except Exception as e: st.error(f"Vault processing error: {e}")

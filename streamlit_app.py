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
    .metric-box { background-color: #1A1F2B; padding: 20px; border-radius: 12px; text-align: center; border-top: 3px solid #98DED9; margin-bottom: 15px; }
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
VENDOR_CATS = ["Burgers & Meals", "Fries & Snacks", "Mocktails", "Beverages"]

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

                if time_left < 0: 
                    b_col = "#EF4444"
                    bg_col = "#2D1E1E"
                    t_col = "#EF4444"
                    txt = f"🚨 {abs(int(time_left))}m OVERDUE"
                elif time_left <= 10: 
                    b_col = "#FF754C"
                    bg_col = "#2D231E"
                    t_col = "#FF754C"
                    txt = f"⚠️ {int(time_left)}m LEFT"
                else: 
                    b_col = "#98DED9"
                    bg_col = "#1A1F2B"
                    t_col = "#98DED9"
                    txt = f"⏳ {int(time_left)}m left"
                
                fnb_val = row.get('fnb_total') or 0
                if fnb_val > 0:
                    fnb_html = f"<span style='background:#42201D; color:#FF754C; padding:6px 14px; border-radius:8px; font-size:14px; font-weight:700; box-shadow: 0 2px 4px rgba(0,0,0,0.2);'>🍔 ₹{fnb_val:.0f}</span>"
                else:
                    fnb_html = ""

                card_html = (
                    f"<div style='background:{bg_col}; border:1px solid #2D3446; border-top:4px solid {b_col}; border-radius:14px; padding:20px; margin-bottom:15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>"
                    f"<div style='display:flex; justify-content:space-between; align-items:center; border-bottom: 1px solid #2D3446; padding-bottom: 10px; margin-bottom: 15px;'>"
                    f"<span style='color:white; font-size:18px; font-weight:800; letter-spacing: 0.5px;'>{row['system']}</span>"
                    f"<span style='color:#9CA3AF; font-size:14px; font-weight:600;'>{row['customer']}</span>"
                    f"</div>"
                    f"<div style='text-align: center; margin-bottom: 15px;'>"
                    f"<h2 style='color:{t_col}; margin:0; padding:0; font-size:34px; font-weight:900; letter-spacing: 0.5px;'>{txt}</h2>"
                    f"</div>"
                    f"<div style='display:flex; gap:10px; justify-content: center; flex-wrap:wrap;'>"
                    f"<span style='background:#2B3245; color:#98DED9; padding:6px 14px; border-radius:8px; font-size:14px; font-weight:700; box-shadow: 0 2px 4px rgba(0,0,0,0.2);'>🎮 ₹{row['total']:.0f}</span>"
                    f"{fnb_html}"
                    f"</div>"
                    f"</div>"
                )

                with grid[i % 3]:
                    st.markdown(card_html, unsafe_allow_html=True)

    with col_op:
        st.markdown("<div class='panel-box'>", unsafe_allow_html=True)
        st.subheader("Operator Panel")
        if not active_gamers.empty:
            active_gamers['lbl'] = active_gamers['customer'] + " | " + active_gamers['system']
            sel = st.selectbox("Select Gamer", active_gamers['lbl'].tolist(), label_visibility="collapsed", key="t1_gamer_sel")
            row = active_gamers[active_gamers['lbl'] == sel].iloc[0]
            
            op_mode = st.radio("Action", ["Smart Checkout", "Add Time"], horizontal=True, key="t1_op_mode")
            
            if op_mode == "Smart Checkout":
                try: played_mins = int((datetime.now(IST) - pd.to_datetime(f"{row['date'][:10]} {row['entry_time']}").tz_localize(IST)).total_seconds() / 60.0)
                except: played_mins = 0
                st.caption(f"⏱️ Actual Time Played: **{played_mins} mins**")
                
                rec_dur = float(row['duration'])
                if played_mins <= 40 and row['duration'] >= 1.0: rec_dur = 0.5
                elif played_mins > 40 and played_mins <= 60 and row['duration'] > 1.0: rec_dur = 1.0
                
                f_dur = st.number_input("Billed Hrs", 0.5, 12.0, float(rec_dur), 0.5, key="t1_billed_hrs")
                
                game_bill = float(row['total'])
                food_bill = float(row.get('fnb_total') or 0)
                grand_total = game_bill + food_bill
                
                st.markdown(f"<div style='background:#161922; padding:10px; border-radius:8px;'><small>Gaming: ₹{game_bill:.0f}<br>F&B Tab: ₹{food_bill:.0f}</small><h3 style='color:#98DED9; margin:0;'>Total: ₹{grand_total:.0f}</h3></div><br>", unsafe_allow_html=True)
                
                pay = st.radio("Pay Method", ["Cash", "UPI"], horizontal=True, key="t1_pay_method")
                if st.button("🛑 Collect & Close", type="primary", key="t1_close_btn"):
                    conn.table("sales").update({"status": "Completed", "method": pay, "duration": float(f_dur), "total": float(grand_total)}).eq("id", int(row['id'])).execute()
                    st.balloons(); st.rerun()
                    
            elif op_mode == "Add Time":
                ext = st.number_input("Extra Hrs", 0.5, 5.0, 0.5, key="t1_extra_hrs")
                if st.button("➕ Extend Session", key="t1_ext_btn"):
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
                            
                            track_stock = cat not in VENDOR_CATS
                            is_disabled = track_stock and r['stock_level'] <= 0
                            stock_label = f"\n({r['stock_level']} left)" if track_stock else ""
                            label = f"{r['item_name']}\n₹{r['selling_price']:.0f}{stock_label}"
                            
                            if grid[i % 4].button(label, key=f"fnb_{r['id']}", disabled=is_disabled, use_container_width=True):
                                st.session_state.fnb_cart.append({"id": r['id'], "name": r['item_name'], "price": r['selling_price'], "cost": r['cost_price'], "track_stock": track_stock})
                                st.rerun()
                            st.markdown("</div>", unsafe_allow_html=True)
                
                with st.expander("🍟 BYOB (Build Your Own Bag)"):
                    chip_choice = st.selectbox("Base Chips", ["Blue Lays", "Kurkure", "Doritos", "Uncle Chipps"], key="t2_byob_chips")
                    has_cheese = st.checkbox("Add Cheese (+₹30)", key="t2_byob_cheese")
                    byob_p = 140 if has_cheese else 110
                    byob_c = 105 if has_cheese else 75
                    if st.button(f"Add BYOB (₹{byob_p})", key="t2_byob_btn"):
                        txt = f"BYOB ({chip_choice} {'w/ Cheese' if has_cheese else ''})"
                        st.session_state.fnb_cart.append({"id": "byob", "name": txt, "price": byob_p, "cost": byob_c, "track_stock": False})
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
                
                assign = st.radio("Bill To:", ["Add to Active Gamer", "Walk-in (Pay Now)"], key="t2_assign")
                gamer_id = None
                direct_pay_method = None
                
                if assign == "Add to Active Gamer":
                    if not active_gamers.empty:
                        sel_g = st.selectbox("Select Gamer", active_gamers['lbl'].tolist(), label_visibility="collapsed", key="t2_gamer_sel")
                        gamer_id = int(active_gamers[active_gamers['lbl'] == sel_g].iloc[0]['id'])
                    else: st.warning("No active gamers.")
                else:
                    direct_pay_method = st.radio("Walk-in Payment Method", ["Cash", "UPI"], horizontal=True, key="t2_walkin_pay")
                
                if st.button("✅ CONFIRM ORDER", use_container_width=True, key="t2_confirm_btn"):
                    for item in st.session_state.fnb_cart:
                        if item.get('track_stock', False) and item['id'] != 'byob':
                            cur_stock = inv_df[inv_df['id'] == item['id']].iloc[0]['stock_level']
                            conn.table("inventory").update({"stock_level": int(cur_stock - 1)}).eq("id", item['id']).execute()
                            
                    conn.table("cafe_orders").insert({
                        "date": datetime.now(IST).strftime('%Y-%m-%d'), "items": items_str, 
                        "total_revenue": float(tot_sell), "total_cost": float(tot_cost), "profit": float(tot_sell - tot_cost),
                        "method": "Tab" if assign == "Add to Active Gamer" else direct_pay_method
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
                trackable_items = inv_df[~inv_df['category'].isin(VENDOR_CATS)]
                if not trackable_items.empty:
                    refill_item = st.selectbox("Select Item to Refill", trackable_items['item_name'].tolist(), key="t2_refill_item")
                    refill_qty = st.number_input("Quantity Arrived", 1, 500, 10, key="t2_refill_qty")
                    if st.button("Update Stock Levels", use_container_width=True, key="t2_refill_btn"):
                        c_qty = inv_df[inv_df['item_name'] == refill_item].iloc[0]['stock_level']
                        conn.table("inventory").update({"stock_level": int(c_qty + refill_qty)}).eq("item_name", refill_item).execute()
                        st.success(f"Added stock to {refill_item}!"); st.rerun()
                else: st.info("No trackable items in inventory.")
            
            st.write("---")
            st.write("### 🗑️ Delete Item")
            if not inv_df.empty:
                del_item = st.selectbox("Select Item to Delete", inv_df['item_name'].tolist(), key="t2_del_item")
                if st.button("Delete from Database", type="primary", use_container_width=True, key="t2_del_btn"):
                    conn.table("inventory").delete().eq("item_name", del_item).execute()
                    st.warning(f"Deleted {del_item} permanently!"); st.rerun()

        with c2:
            st.write("### ➕ Add New Item")
            with st.form("new_inv"):
                n_name = st.text_input("Name (e.g., Red Bull, Snickers)", key="t2_n_name")
                
                existing_cats = inv_df['category'].dropna().unique().tolist() if not inv_df.empty else []
                base_cats = ["Burgers & Meals", "Fries & Snacks", "Mocktails", "Beverages", "Chips", "Cold Drinks", "Chocolates"]
                all_cats = sorted(list(set(base_cats + existing_cats))) + ["➕ Create New Category"]
                
                n_cat_sel = st.selectbox("Category", all_cats, key="t2_n_cat_sel")
                n_cat_new = st.text_input("If 'Create New Category', type name here:", key="t2_n_cat_new")
                
                n_cost = st.number_input("Cost to you (₹)", 0.0, key="t2_n_cost")
                n_sell = st.number_input("Selling Price (₹)", 0.0, key="t2_n_sell")
                n_qty = st.number_input("Starting Stock (Leave 0 for outside vendor items)", 0, key="t2_n_qty")
                
                if st.form_submit_button("Add to Database", use_container_width=True):
                    final_cat = n_cat_new.strip() if n_cat_sel == "➕ Create New Category" else n_cat_sel
                    
                    if not n_name.strip():
                        st.error("⚠️ Please enter a name for the item.")
                    elif not final_cat:
                        st.error("⚠️ Please select or enter a category.")
                    elif not inv_df.empty and n_name.lower().strip() in inv_df['item_name'].str.lower().str.strip().values:
                        st.error(f"⚠️ '{n_name}' already exists in your inventory!")
                    else:
                        try:
                            conn.table("inventory").insert({"item_name": n_name.strip(), "category": final_cat, "cost_price": float(n_cost), "selling_price": float(n_sell), "stock_level": int(n_qty)}).execute()
                            st.success(f"Successfully added {n_name}!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to add to database. Error: {e}")
        
        st.write("---")
        st.write("### Low Stock Alerts (In-House Only)")
        if not inv_df.empty:
            trackable_only = inv_df[~inv_df['category'].isin(VENDOR_CATS)]
            low = trackable_only[trackable_only['stock_level'] <= 5]
            if not low.empty: st.error("🚨 These items need restocking immediately!")
            st.dataframe(trackable_only[['item_name', 'category', 'stock_level', 'selling_price']], use_container_width=True, hide_index=True)

# ==========================================
# TAB 3: BOOKINGS, CART & QUEUE
# ==========================================
with t3:
    col_form, col_cart = st.columns([1.2, 1], gap="large")
    with col_form:
        st.subheader("1. Lead & Details")
        with st.container(border=True):
            name = st.text_input("Gamer / Group Name", key=f"t3_n_{st.session_state.form_reset}")
            phone = st.text_input("Phone Number", key=f"t3_p_{st.session_state.form_reset}")
            st.write("---")
            b_type = st.radio("Booking Type", ["🏃‍♂️ Walk-in (Play Now)", "🕒 Book for Later (Advance)"], horizontal=True, key=f"t3_bt_{st.session_state.form_reset}")
            
            if "Walk-in" in b_type:
                sch_date = datetime.now(IST).strftime('%Y-%m-%d')
                b_time = st.time_input("Session Start Time", value=datetime.now(IST).time(), step=60, key=f"t3_wt_{st.session_state.form_reset}")
                time_str = b_time.strftime("%I:%M %p")
                final_status = "Active"; btn_txt = "🚀 Start Session Now"
                st.info(f"Session will be logged for today at {time_str}")
            else:
                d_col, t_col = st.columns(2)
                b_date = d_col.date_input("Select Date", value=datetime.now(IST).date(), min_value=datetime.now(IST).date(), key=f"t3_d_{st.session_state.form_reset}")
                def_time = (datetime.now(IST) + timedelta(hours=1)).replace(minute=0, second=0).time()
                b_time = t_col.time_input("Select Time", value=def_time, step=900, key=f"t3_bt2_{st.session_state.form_reset}")
                sch_date = b_date.strftime('%Y-%m-%d')
                time_str = b_time.strftime("%I:%M %p")
                final_status = "Booked"; btn_txt = f"📅 Confirm Reservation"
                st.info(f"Slot will be reserved for {b_date.strftime('%b %d')} at {time_str}")

        st.subheader("2. Add Hardware")
        with st.container(border=True):
            sys_col, dur_col, ctrl_col = st.columns([2, 1, 1])
            sel_sys = sys_col.selectbox("Hardware", list(SYSTEMS.keys()), key=f"t3_sys_{st.session_state.form_reset}")
            dur = dur_col.number_input("Hours", 0.5, 12.0, 1.0, 0.5, key=f"t3_dur_{st.session_state.form_reset}")
            ctrl = ctrl_col.number_input("Extra Ctrl", 0, 3, 0, key=f"t3_ctrl_{st.session_state.form_reset}") if "PS" in sel_sys else 0
            
            if st.button("➕ Add to Cart", use_container_width=True, key=f"t3_add_{st.session_state.form_reset}"):
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
                if c_del.button("❌", key=f"t3_del_{i}_{st.session_state.form_reset}"): st.session_state.cart.pop(i); st.rerun()
            st.divider()
            st.markdown(f"### Total: ₹{sum(item['price'] for item in st.session_state.cart)}")
            
            if st.button(btn_txt, type="primary", use_container_width=True, key=f"t3_book_{st.session_state.form_reset}"):
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
        
        st.write("### 📅 Upcoming Bookings Queue")
        if not db_df.empty:
            up_df = db_df[db_df['status'] == 'Booked']
            if not up_df.empty:
                st.dataframe(up_df[['scheduled_date', 'entry_time', 'customer', 'system', 'duration']], hide_index=True, use_container_width=True)
                
                up_df['lbl'] = up_df['customer'] + " | " + up_df['system']
                c_chk, c_can = st.columns(2)
                
                with c_chk:
                    st.write("✅ **Check-In Gamer**")
                    sel_chk = st.selectbox("Select Gamer", up_df['lbl'].tolist(), key="t3_chk_sel", label_visibility="collapsed")
                    if st.button("🚀 Start Session", use_container_width=True, key="t3_start_btn"):
                        t_id = up_df[up_df['lbl'] == sel_chk].iloc[0]['id']
                        now_time = datetime.now(IST).strftime("%I:%M %p")
                        conn.table("sales").update({"status": "Active", "entry_time": now_time}).eq("id", int(t_id)).execute()
                        st.success("Checked in successfully!"); st.rerun()
                
                with c_can:
                    st.write("🚫 **Cancel Booking**")
                    sel_can = st.selectbox("Select Gamer", up_df['lbl'].tolist(), key="t3_can_sel", label_visibility="collapsed")
                    if st.button("Cancel Booking", type="primary", use_container_width=True, key="t3_can_btn"):
                        t_id = up_df[up_df['lbl'] == sel_can].iloc[0]['id']
                        conn.table("sales").update({"status": "Cancelled"}).eq("id", int(t_id)).execute()
                        st.warning("Booking Cancelled!"); st.rerun()

# ==========================================
# TAB 4: SNAPSHOT & REPORTS
# ==========================================
with t4:
    st.subheader("📊 Today's Summary & Exports")
    if st.text_input("Manager Passcode", type="password", key="t4_pwd") == "Shreenad@0511":
        try:
            raw = conn.table("sales").select("*").execute()
            df = pd.DataFrame(raw.data)
            
            today_str = datetime.now(IST).strftime('%Y-%m-%d')
            
            try:
                cafe_raw = conn.table("cafe_orders").select("*").eq("date", today_str).execute()
                cafe_df = pd.DataFrame(cafe_raw.data)
                today_fnb = cafe_df['total_revenue'].sum() if not cafe_df.empty else 0
                today_fnb_profit = cafe_df['profit'].sum() if not cafe_df.empty else 0
                fnb_cash = cafe_df[cafe_df['method'] == 'Cash']['total_revenue'].sum() if not cafe_df.empty else 0
                fnb_upi = cafe_df[cafe_df['method'] == 'UPI']['total_revenue'].sum() if not cafe_df.empty else 0
            except:
                today_fnb = 0; today_fnb_profit = 0; fnb_cash = 0; fnb_upi = 0

            if not df.empty:
                df['date_str'] = df['date'].str[:10] 
                t_df = df[df['date_str'] == today_str]
                comp = t_df[t_df['status'] == 'Completed']
                
                total_cash = comp[comp['method']=='Cash']['total'].sum() + fnb_cash
                total_upi = comp[comp['method']!='Cash']['total'].sum() + fnb_upi
                grand_total = total_cash + total_upi
                
                m1, m2, m3, m4, m5, m6 = st.columns(6)
                m1.markdown(f"<div class='metric-box'>Cash Collected<h2>₹{total_cash:,.0f}</h2></div>", unsafe_allow_html=True)
                m2.markdown(f"<div class='metric-box'>UPI Collected<h2>₹{total_upi:,.0f}</h2></div>", unsafe_allow_html=True)
                m3.markdown(f"<div class='metric-box' style='border-color:#4F46E5'>Total Revenue<h2 style='color:#4F46E5'>₹{grand_total:,.0f}</h2></div>", unsafe_allow_html=True)
                m4.markdown(f"<div class='metric-box' style='border-color:#34D399'>Today's F&B Sale<h2 style='color:#34D399'>₹{today_fnb:,.0f}</h2></div>", unsafe_allow_html=True)
                m5.markdown(f"<div class='metric-box' style='border-color:#10B981'>Today's F&B Profit<h2 style='color:#10B981'>₹{today_fnb_profit:,.0f}</h2></div>", unsafe_allow_html=True)
                m6.markdown(f"<div class='metric-box' style='border-color:#FF754C'>Pending on Floor<h2 style='color:#FF754C'>₹{t_df[t_df['status']=='Active']['total'].sum():,.0f}</h2></div>", unsafe_allow_html=True)
                
                st.divider()
                st.write("### Export Data")
                d_range = st.date_input("Select Date Range to Export", [datetime.now(IST).date(), datetime.now(IST).date()], key="t4_drange")
                if len(d_range) == 2:
                    s_dt, e_dt = [d.strftime('%Y-%m-%d') for d in d_range]
                    f_edf = df[(df['date_str'] >= s_dt) & (df['date_str'] <= e_dt)]
                    st.download_button("📥 Export CSV", f_edf.to_csv(index=False).encode('utf-8'), f"Export_{s_dt}_to_{e_dt}.csv", "text/csv", key="t4_export_btn")
        except: st.error("Error loading summary.")

# ==========================================
# TAB 5: MASTER VAULT
# ==========================================
with t5:
    st.subheader("🔐 Master Intelligence Vault")
    if st.text_input("Master Key", type="password", key="t5_pwd") == "Shreenad@0511":
        try:
            raw_v = conn.table("sales").select("*").execute()
            vdf = pd.DataFrame(raw_v.data)
            
            with st.expander("💸 Record Cafe Expenses", expanded=False):
                with st.form("expense_form"):
                    e_desc, e_amt, e_meth = st.columns(3)
                    desc = e_desc.text_input("Expense Details", key="t5_e_desc")
                    amt = e_amt.number_input("Amount (₹)", 0, key="t5_e_amt")
                    meth = e_meth.selectbox("Paid Via", ["Cash", "UPI"], key="t5_e_meth")
                    if st.form_submit_button("Log Expense", use_container_width=True):
                        conn.table("expenses").insert({"expense_date": datetime.now(IST).strftime('%Y-%m-%d'), "category": desc, "amount": amt, "method": meth}).execute()
                        st.success("Logged!"); st.rerun()

            st.divider()
            
            if not vdf.empty:
                vdf['date_str'] = vdf['date'].str[:10]
                comp_df = vdf[vdf['status'] == 'Completed'].copy()
                
                cafe_res = conn.table("cafe_orders").select("*").in_("method", ["Cash", "UPI"]).execute()
                cafe_direct_df = pd.DataFrame(cafe_res.data)
                
                if not cafe_direct_df.empty:
                    cafe_direct_df['date_str'] = cafe_direct_df['date'].str[:10]
                    cafe_direct_df['total'] = cafe_direct_df['total_revenue']
                    revenue_df = pd.concat([comp_df[['date_str', 'total']], cafe_direct_df[['date_str', 'total']]])
                else:
                    revenue_df = comp_df[['date_str', 'total']]

                revenue_df['date_obj'] = pd.to_datetime(revenue_df['date_str'])

                now_d = datetime.now(IST).date()
                start_tw = now_d - timedelta(days=now_d.weekday())
                start_lw = start_tw - timedelta(days=7)
                end_lw = start_tw - timedelta(days=1)
                
                start_tm = now_d.replace(day=1)
                end_lm = start_tm - timedelta(days=1)
                start_lm = end_lm.replace(day=1)

                wtd = revenue_df[revenue_df['date_obj'].dt.date >= start_tw]['total'].sum()
                lw = revenue_df[(revenue_df['date_obj'].dt.date >= start_lw) & (revenue_df['date_obj'].dt.date <= end_lw)]['total'].sum()
                mtd = revenue_df[revenue_df['date_obj'].dt.date >= start_tm]['total'].sum()
                lm = revenue_df[(revenue_df['date_obj'].dt.date >= start_lm) & (revenue_df['date_obj'].dt.date <= end_lm)]['total'].sum()
                lifetime = revenue_df['total'].sum()

                st.write("### 📈 Executive Revenue Dashboard")
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Lifetime Gross", f"₹{lifetime:,.0f}")
                c2.metric("This Month (MTD)", f"₹{mtd:,.0f}", delta=f"{((mtd-lm)/lm*100) if lm else 0:.1f}% vs Last Month")
                c3.metric("Last Month", f"₹{lm:,.0f}")
                c4.metric("This Week (WTD)", f"₹{wtd:,.0f}", delta=f"{((wtd-lw)/lw*100) if lw else 0:.1f}% vs Last Week")
                c5.metric("Last Week", f"₹{lw:,.0f}")
                
                st.divider()
                
                st.write("### 🎮 Hardware Income Breakdown")
                hw_map = {"PC1":"PC", "PC2":"PC", "PS1":"PS5", "PS2":"PS5", "PS3":"PS5", "SIM1":"Racing Sim"}
                comp_df['Category'] = comp_df['system'].map(hw_map).fillna(comp_df['system'])
                comp_df['date_obj'] = pd.to_datetime(comp_df['date_str'])
                
                hw_life = comp_df.groupby('Category')['total'].sum().rename('Lifetime Gross')
                hw_tm = comp_df[comp_df['date_obj'].dt.date >= start_tm].groupby('Category')['total'].sum().rename('This Month')
                hw_lm = comp_df[(comp_df['date_obj'].dt.date >= start_lm) & (comp_df['date_obj'].dt.date <= end_lm)].groupby('Category')['total'].sum().rename('Last Month')
                
                hw_summary = pd.concat([hw_life, hw_tm, hw_lm], axis=1).fillna(0).reset_index()
                st.dataframe(hw_summary, hide_index=True, use_container_width=True)

            st.divider()

            st.write("### 🍔 F&B Financials")
            sales_res = conn.table("cafe_orders").select("*").execute()
            sdf = pd.DataFrame(sales_res.data)
            if not sdf.empty:
                p_col1, p_col2 = st.columns(2)
                p_col1.markdown(f"<div class='metric-box' style='border-color:#EF4444'><h4>Total F&B Cost</h4><h2 style='color:#EF4444'>₹{sdf['total_cost'].sum():,.0f}</h2></div>", unsafe_allow_html=True)
                p_col2.markdown(f"<div class='metric-box'><h4>Total Net F&B Profit</h4><h2 style='color:#34D399'>₹{sdf['profit'].sum():,.0f}</h2></div>", unsafe_allow_html=True)

            st.divider()

            if not vdf.empty:
                st.subheader("📅 Day-Wise Profit & Loss Ledger")
                tot_inc = revenue_df.groupby('date_str')['total'].sum().rename('Gross Income').reset_index()
                
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

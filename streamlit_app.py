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

# --- NEW: SYSTEM SIDEBAR ---
with st.sidebar:
    st.write("### ⚙️ System Controls")
    if st.button("🔄 Force Sync Data", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()
    if st.button("🔒 Lock Screen", use_container_width=True):
        st.session_state.auth = False
        st.rerun()

# --- 3. DATABASE SETUP & HELPER FUNCS ---
try: 
    conn = st.connection("supabase", type=SupabaseConnection, ttl=0)
except Exception as e: 
    st.error(f"Database Connection Error. {e}"); st.stop()

SYSTEMS = {"PS1":"PS5", "PS2":"PS5", "PS3":"PS5", "PC1":"PC", "PC2":"PC", "SIM1":"Racing Sim"}
VENDOR_CATS = ["Burgers & Meals", "Fries & Snacks", "Mocktails", "Beverages"]

def get_price(cat, dur, extra=0):
    full_hours = int(dur)
    half_hours = 1 if (dur % 1) != 0 else 0
    
    if cat == "PC":
        return (full_hours * 100) + (half_hours * 70)
    elif cat == "Racing Sim":
        return (full_hours * 250) + (half_hours * 150)
    elif cat == "PS5":
        base_full = 150 + (extra * 100)
        base_half = 100 + (extra * 100)
        return (full_hours * base_full) + (half_hours * base_half)
    return 0

def get_extra_ctrls(cat, orig_dur, orig_tot):
    if cat != "PS5": return 0
    try:
        full_hours = int(orig_dur)
        half_hours = 1 if (orig_dur % 1) != 0 else 0
        base_cost = (full_hours * 150) + (half_hours * 100)
        premium_paid = orig_tot - base_cost
        cost_per_extra_ctrl = (full_hours * 100) + (half_hours * 100)
        if cost_per_extra_ctrl == 0: return 0
        extra = round(premium_paid / cost_per_extra_ctrl)
        return max(0, int(extra))
    except: return 0

def get_cash_upi(df, amt_col='total'):
    cash_total = 0.0
    upi_total = 0.0
    for _, r in df.iterrows():
        m = str(r.get('method', ''))
        try: val = float(r.get(amt_col, 0.0))
        except: val = 0.0
        
        if m == 'Cash': cash_total += val
        elif m == 'UPI': upi_total += val
        elif m.startswith('Split|'):
            try:
                pts = m.split('|')
                cash_total += float(pts[1])
                upi_total += float(pts[2])
            except: pass
    return cash_total, upi_total

def get_ordinal(n):
    if 11 <= (n % 100) <= 13: return str(n) + 'th'
    return str(n) + ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]

inv_cols = ["id", "item_name", "category", "cost_price", "selling_price", "stock_level"]
db_cols = ["id", "customer", "phone", "system", "duration", "total", "method", "entry_time", "status", "scheduled_date", "fnb_total", "fnb_items", "date"]

# THE FIX: Explicitly forcing ttl=0 on every single database read operation
try:
    inv_res = conn.table("inventory").select("*").order('item_name').execute(ttl=0)
    inv_df = pd.DataFrame(inv_res.data) if inv_res.data else pd.DataFrame(columns=inv_cols)
    
    active_res = conn.table("sales").select("*").in_("status", ["Active", "Booked"]).execute(ttl=0)
    db_df = pd.DataFrame(active_res.data) if active_res.data else pd.DataFrame(columns=db_cols)
    
    today_str_query = datetime.now(IST).strftime('%Y-%m-%d')
    tab_res = conn.table("sales").select("*").eq("status", "Completed").eq("method", "Master Tab").gte("date", today_str_query).execute(ttl=0)
    tab_df = pd.DataFrame(tab_res.data) if tab_res.data else pd.DataFrame(columns=db_cols)
    
    if not db_df.empty:
        db_df['total'] = pd.to_numeric(db_df['total'], errors='coerce').fillna(0.0)
        db_df['fnb_total'] = pd.to_numeric(db_df['fnb_total'], errors='coerce').fillna(0.0)
    if not tab_df.empty:
        tab_df['total'] = pd.to_numeric(tab_df['total'], errors='coerce').fillna(0.0)
        
except Exception as e:
    st.error(f"Syncing Database... {e}")
    inv_df = pd.DataFrame(columns=inv_cols)
    db_df = pd.DataFrame(columns=db_cols)
    tab_df = pd.DataFrame(columns=db_cols)

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
                
                fnb_val = float(row.get('fnb_total') or 0.0)
                game_val = float(row.get('total') or 0.0)
                
                fnb_html = f"<span style='background:#42201D; color:#FF754C; padding:6px 14px; border-radius:8px; font-size:14px; font-weight:700; box-shadow: 0 2px 4px rgba(0,0,0,0.2);'>🍔 ₹{fnb_val:.0f}</span>" if fnb_val > 0 else ""

                card_html = (
                    f"<div style='background:{bg_col}; border:1px solid #2D3446; border-top:4px solid {b_col}; border-radius:14px; padding:20px; margin-bottom:15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>"
                    f"<div style='display:flex; justify-content:space-between; align-items:center; border-bottom: 1px solid #2D3446; padding-bottom: 10px; margin-bottom: 15px;'>"
                    f"<span style='color:white; font-size:18px; font-weight:800; letter-spacing: 0.5px;'>{row['system']}</span>"
                    f"<span style='color:#9CA3AF; font-size:14px; font-weight:600;'>{row['customer']} • <span style='color:#98DED9;'>In: {row['entry_time']}</span></span>"
                    f"</div>"
                    f"<div style='text-align: center; margin-bottom: 15px;'>"
                    f"<h2 style='color:{t_col}; margin:0; padding:0; font-size:34px; font-weight:900; letter-spacing: 0.5px;'>{txt}</h2>"
                    f"</div>"
                    f"<div style='display:flex; gap:10px; justify-content: center; flex-wrap:wrap;'>"
                    f"<span style='background:#2B3245; color:#98DED9; padding:6px 14px; border-radius:8px; font-size:14px; font-weight:700; box-shadow: 0 2px 4px rgba(0,0,0,0.2);'>🎮 ₹{game_val:.0f}</span>"
                    f"{fnb_html}"
                    f"</div>"
                    f"</div>"
                )
                with grid[i % 3]: st.markdown(card_html, unsafe_allow_html=True)

    with col_op:
        st.markdown("<div class='panel-box'>", unsafe_allow_html=True)
        st.subheader("Operator Panel")
        if not active_gamers.empty:
            active_gamers['lbl'] = active_gamers['customer'] + " | " + active_gamers['system']
            sel = st.selectbox("Select Gamer", active_gamers['lbl'].tolist(), label_visibility="collapsed", key="t1_gamer_sel")
            row = active_gamers[active_gamers['lbl'] == sel].iloc[0]
            g_id = str(row['id'])
            
            raw_t = float(row.get('total') or 0.0)
            raw_f = float(row.get('fnb_total') or 0.0)
            db_state_key = f"{g_id}_{raw_t}_{raw_f}"
            
            op_mode = st.radio("Action", ["Smart Checkout", "Add Time"], horizontal=True, key=f"t1_op_mode_{db_state_key}")
            
            if op_mode == "Smart Checkout":
                try: played_mins = int((datetime.now(IST) - pd.to_datetime(f"{row['date'][:10]} {row['entry_time']}").tz_localize(IST)).total_seconds() / 60.0)
                except: played_mins = 0
                st.caption(f"⏱️ Actual Time Played: **{played_mins} mins**")
                
                rec_dur = float(row['duration'])
                if played_mins <= 40 and row['duration'] >= 1.0: rec_dur = 0.5
                elif played_mins > 40 and played_mins <= 60 and row['duration'] > 1.0: rec_dur = 1.0
                
                f_dur = st.number_input("Billed Hrs", 0.5, 12.0, float(rec_dur), 0.5, key=f"t1_bhrs_{db_state_key}")
                
                orig_dur = float(row['duration'])
                orig_tot = raw_t
                sys_cat = SYSTEMS.get(row['system'], 'PC')
                
                if f_dur == orig_dur:
                    dyn_game_bill = orig_tot
                else:
                    extra_c = get_extra_ctrls(sys_cat, orig_dur, orig_tot)
                    dyn_game_bill = float(get_price(sys_cat, f_dur, extra_c))
                
                food_bill = raw_f
                past_tabs = tab_df[tab_df['customer'] == row['customer']] if not tab_df.empty else pd.DataFrame()
                past_tab_amt = past_tabs['total'].sum() if not past_tabs.empty else 0.0

                calc_total = dyn_game_bill + food_bill + past_tab_amt
                
                if past_tab_amt > 0:
                    st.markdown(f"<small style='color:#9CA3AF;'>Current Game: ₹{dyn_game_bill:.0f} | F&B: ₹{food_bill:.0f} | <span style='color:#FF754C'>Past Unpaid Tab: ₹{past_tab_amt:.0f}</span></small>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<small style='color:#9CA3AF;'>Expected Gaming: ₹{dyn_game_bill:.0f} | F&B Tab: ₹{food_bill:.0f}</small>", unsafe_allow_html=True)

                final_total = st.number_input("Final Checkout Amount (₹)", min_value=0.0, value=float(calc_total), step=1.0, key=f"t1_final_tot_{db_state_key}_{f_dur}_{calc_total}")
                
                pay = st.radio("Pay Method", ["Cash", "UPI", "Split Payment", "Hold on Tab (Switching PC/PS5)"], horizontal=True, key=f"t1_pay_{db_state_key}")
                
                final_method_str = pay
                if pay == "Split Payment":
                    st.caption("How much was paid in Cash?")
                    split_cash = st.number_input("Cash Portion (₹)", min_value=0.0, max_value=float(final_total), value=float(final_total)/2, step=10.0, key=f"t1_split_{db_state_key}_{final_total}")
                    st.info(f"💳 Remaining UPI Portion: **₹{final_total - split_cash:.0f}**")
                    final_method_str = f"Split|{split_cash}|{final_total - split_cash}"
                elif pay == "Hold on Tab (Switching PC/PS5)":
                    final_method_str = "Master Tab"
                
                if st.button("🛑 Collect & Close", type="primary", key=f"t1_close_{db_state_key}"):
                    if final_method_str != "Master Tab" and not past_tabs.empty:
                        for past_id in past_tabs['id']:
                            conn.table("sales").update({"method": final_method_str}).eq("id", int(past_id)).execute()
                    
                    current_row_final = final_total - past_tab_amt if final_method_str != "Master Tab" else final_total
                    conn.table("sales").update({"status": "Completed", "method": final_method_str, "duration": float(f_dur), "total": float(current_row_final)}).eq("id", int(row['id'])).execute()
                    st.cache_data.clear(); st.balloons(); st.rerun()
                    
            elif op_mode == "Add Time":
                ext = st.number_input("Extra Hrs", 0.5, 5.0, 0.5, key=f"t1_ext_hrs_{db_state_key}")
                if st.button("➕ Extend Session", key=f"t1_ext_btn_{db_state_key}"):
                    new_dur = float(row['duration']) + float(ext)
                    
                    orig_dur = float(row['duration'])
                    orig_tot = raw_t
                    sys_cat = SYSTEMS.get(row['system'], 'PC')
                    extra_c = get_extra_ctrls(sys_cat, orig_dur, orig_tot)
                    
                    new_total = float(get_price(sys_cat, new_dur, extra_c))
                    
                    conn.table("sales").update({"total": new_total, "duration": new_dur}).eq("id", int(row['id'])).execute()
                    st.cache_data.clear(); st.rerun()
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
                final_fnb_pay = None
                
                if assign == "Add to Active Gamer":
                    if not active_gamers.empty:
                        sel_g = st.selectbox("Select Gamer", active_gamers['lbl'].tolist(), label_visibility="collapsed", key="t2_gamer_sel")
                        gamer_id = int(active_gamers[active_gamers['lbl'] == sel_g].iloc[0]['id'])
                    else: st.warning("No active gamers.")
                else:
                    direct_pay_method = st.radio("Walk-in Payment Method", ["Cash", "UPI", "Split Payment"], horizontal=True, key="t2_walkin_pay")
                    final_fnb_pay = direct_pay_method
                    if direct_pay_method == "Split Payment":
                        walk_split_c = st.number_input("Cash Portion (₹)", min_value=0.0, max_value=float(tot_sell), value=float(tot_sell)/2, step=10.0, key="t2_wsc")
                        st.info(f"💳 Remaining UPI Portion: **₹{tot_sell - walk_split_c:.0f}**")
                        final_fnb_pay = f"Split|{walk_split_c}|{tot_sell - walk_split_c}"
                
                if st.button("✅ CONFIRM ORDER", use_container_width=True, key="t2_confirm_btn"):
                    for item in st.session_state.fnb_cart:
                        if item.get('track_stock', False) and item['id'] != 'byob':
                            cur_stock = inv_df[inv_df['id'] == item['id']].iloc[0]['stock_level']
                            conn.table("inventory").update({"stock_level": int(cur_stock - 1)}).eq("id", item['id']).execute()
                            
                    conn.table("cafe_orders").insert({
                        "date": datetime.now(IST).strftime('%Y-%m-%d'), "items": items_str, 
                        "total_revenue": float(tot_sell), "total_cost": float(tot_cost), "profit": float(tot_sell - tot_cost),
                        "method": "Tab" if assign == "Add to Active Gamer" else final_fnb_pay
                    }).execute()
                    
                    if assign == "Add to Active Gamer" and gamer_id:
                        # THE FIX: Apply ttl=0 to read queries inside conditional blocks
                        cur_tab = conn.table("sales").select("fnb_items, fnb_total").eq("id", gamer_id).execute(ttl=0).data[0]
                        old_i = cur_tab.get('fnb_items') or ""
                        old_t = float(cur_tab.get('fnb_total') or 0.0)
                        conn.table("sales").update({"fnb_items": f"{old_i} | {items_str}" if old_i else items_str, "fnb_total": float(old_t + tot_sell)}).eq("id", gamer_id).execute()
                    
                    st.session_state.fnb_cart = []; st.cache_data.clear(); st.success("Order Processed!"); st.rerun()
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
                        st.cache_data.clear(); st.success(f"Added stock to {refill_item}!"); st.rerun()
                else: st.info("No trackable items in inventory.")
            
            st.write("---")
            st.write("### 🗑️ Delete Item")
            if not inv_df.empty:
                del_item = st.selectbox("Select Item to Delete", inv_df['item_name'].tolist(), key="t2_del_item")
                if st.button("Delete from Database", type="primary", use_container_width=True, key="t2_del_btn"):
                    conn.table("inventory").delete().eq("item_name", del_item).execute()
                    st.cache_data.clear(); st.warning(f"Deleted {del_item} permanently!"); st.rerun()

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
                    if not n_name.strip(): st.error("⚠️ Please enter a name for the item.")
                    elif not final_cat: st.error("⚠️ Please select or enter a category.")
                    elif not inv_df.empty and n_name.lower().strip() in inv_df['item_name'].str.lower().str.strip().values: st.error(f"⚠️ '{n_name}' already exists in your inventory!")
                    else:
                        try:
                            conn.table("inventory").insert({"item_name": n_name.strip(), "category": final_cat, "cost_price": float(n_cost), "selling_price": float(n_sell), "stock_level": int(n_qty)}).execute()
                            st.cache_data.clear(); st.success(f"Successfully added {n_name}!")
                            st.rerun()
                        except Exception as e: st.error(f"Failed to add to database. Error: {e}")

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
            else:
                d_col, t_col = st.columns(2)
                b_date = d_col.date_input("Select Date", value=datetime.now(IST).date(), min_value=datetime.now(IST).date(), key=f"t3_d_{st.session_state.form_reset}")
                def_time = (datetime.now(IST) + timedelta(hours=1)).replace(minute=0, second=0).time()
                b_time = t_col.time_input("Select Time", value=def_time, step=900, key=f"t3_bt2_{st.session_state.form_reset}")
                sch_date = b_date.strftime('%Y-%m-%d')
                time_str = b_time.strftime("%I:%M %p")
                final_status = "Booked"; btn_txt = f"📅 Confirm Reservation"

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
                        st.session_state.cart = []; st.session_state.form_reset += 1; st.cache_data.clear(); st.success("Success!"); st.rerun()
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
                        st.cache_data.clear(); st.success("Checked in successfully!"); st.rerun()
                
                with c_can:
                    st.write("🚫 **Cancel Booking**")
                    sel_can = st.selectbox("Select Gamer", up_df['lbl'].tolist(), key="t3_can_sel", label_visibility="collapsed")
                    if st.button("Cancel Booking", type="primary", use_container_width=True, key="t3_can_btn"):
                        t_id = up_df[up_df['lbl'] == sel_can].iloc[0]['id']
                        conn.table("sales").update({"status": "Cancelled"}).eq("id", int(t_id)).execute()
                        st.cache_data.clear(); st.warning("Booking Cancelled!"); st.rerun()

# ==========================================
# TAB 4: SNAPSHOT & REPORTS (STAFF VIEW)
# ==========================================
with t4:
    st.subheader("📊 Daily Floor Snapshot")
    if st.text_input("Staff Passcode", type="password", key="t4_pwd") == "Shreenad@0511":
        try:
            # THE FIX: Enforce live fetch for critical daily snapshot queries
            raw = conn.table("sales").select("*").execute(ttl=0)
            df = pd.DataFrame(raw.data)
            today_str = datetime.now(IST).strftime('%Y-%m-%d')
            
            try:
                cafe_raw = conn.table("cafe_orders").select("*").eq("date", today_str).execute(ttl=0)
                cafe_df = pd.DataFrame(cafe_raw.data)
                if not cafe_df.empty:
                    cafe_df['total_revenue'] = pd.to_numeric(cafe_df['total_revenue'], errors='coerce').fillna(0.0)
                    direct_fnb_df = cafe_df[cafe_df['method'] != 'Tab']
                    direct_fnb_cash, direct_fnb_upi = get_cash_upi(direct_fnb_df, 'total_revenue')
                else:
                    direct_fnb_cash = direct_fnb_upi = 0.0
            except:
                direct_fnb_cash = direct_fnb_upi = 0.0

            if not df.empty:
                df['date_str'] = df['date'].str[:10] 
                t_df = df[df['date_str'] == today_str]
                comp = t_df[t_df['status'] == 'Completed'].copy()
                comp['total'] = pd.to_numeric(comp['total'], errors='coerce').fillna(0.0)
                checkout_cash, checkout_upi = get_cash_upi(comp, 'total')
                pending_floor = pd.to_numeric(t_df[t_df['status']=='Active']['total'], errors='coerce').fillna(0.0).sum()
            else:
                checkout_cash = checkout_upi = pending_floor = 0.0

            total_drawer_cash = checkout_cash + direct_fnb_cash
            total_bank_upi = checkout_upi + direct_fnb_upi

            st.write("### 💰 Today's Collections")
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"<div class='metric-box'>Total Cash (Drawer)<h2 style='color:white'>₹{total_drawer_cash:,.0f}</h2></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='metric-box'>Total UPI (Bank)<h2 style='color:white'>₹{total_bank_upi:,.0f}</h2></div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='metric-box' style='border-color:#FF754C'>Pending on Floor<h2 style='color:#FF754C'>₹{pending_floor:,.0f}</h2></div>", unsafe_allow_html=True)
            
        except Exception as e: st.error(f"Error loading summary. {e}")

# ==========================================
# TAB 5: MASTER VAULT (OWNER VIEW)
# ==========================================
with t5:
    st.subheader("🔐 Master Intelligence Vault")
    if st.text_input("Master Key", type="password", key="t5_pwd") == "Su22101992@":
        try:
            with st.expander("💸 Record Cafe Expenses", expanded=False):
                with st.form("expense_form"):
                    e_desc, e_amt, e_meth = st.columns(3)
                    desc = e_desc.text_input("Expense Details", key="t5_e_desc")
                    amt = e_amt.number_input("Amount (₹)", 0, key="t5_e_amt")
                    meth = e_meth.selectbox("Paid Via", ["Cash", "UPI"], key="t5_e_meth")
                    if st.form_submit_button("Log Expense", use_container_width=True):
                        conn.table("expenses").insert({"expense_date": datetime.now(IST).strftime('%Y-%m-%d'), "category": desc, "amount": amt, "method": meth}).execute()
                        st.cache_data.clear(); st.success("Logged!"); st.rerun()

            st.divider()
            
            today_str = datetime.now(IST).strftime('%Y-%m-%d')
            
            # THE FIX: Enforce live fetch for the Master Vault
            raw_v = conn.table("sales").select("*").execute(ttl=0)
            vdf = pd.DataFrame(raw_v.data)
            
            cafe_res = conn.table("cafe_orders").select("*").execute(ttl=0)
            cafe_all_df = pd.DataFrame(cafe_res.data)
            
            # --- 1. Compute Today's Critical Data for the Vault ---
            if not cafe_all_df.empty:
                cafe_today = cafe_all_df[cafe_all_df['date'].str.startswith(today_str)].copy()
                if not cafe_today.empty:
                    cafe_today['total_revenue'] = pd.to_numeric(cafe_today['total_revenue'], errors='coerce').fillna(0.0)
                    cafe_today['profit'] = pd.to_numeric(cafe_today['profit'], errors='coerce').fillna(0.0)
                    gross_fnb_sale = cafe_today['total_revenue'].sum()
                    gross_fnb_profit = cafe_today['profit'].sum()
                    direct_fnb_df = cafe_today[cafe_today['method'] != 'Tab']
                    direct_fnb_cash, direct_fnb_upi = get_cash_upi(direct_fnb_df, 'total_revenue')
                else:
                    gross_fnb_sale = gross_fnb_profit = direct_fnb_cash = direct_fnb_upi = 0.0
            else:
                gross_fnb_sale = gross_fnb_profit = direct_fnb_cash = direct_fnb_upi = 0.0

            if not vdf.empty:
                vdf['date_str'] = vdf['date'].str[:10]
                comp_df = vdf[vdf['status'] == 'Completed'].copy()
                comp_df['total'] = pd.to_numeric(comp_df['total'], errors='coerce').fillna(0.0)
                comp_df['fnb_total'] = pd.to_numeric(comp_df['fnb_total'], errors='coerce').fillna(0.0)
                comp_df['pure_game'] = comp_df['total'] - comp_df['fnb_total']
                
                today_comp = comp_df[comp_df['date_str'] == today_str].copy()
                checkout_cash, checkout_upi = get_cash_upi(today_comp, 'total')
                pure_game_rev = today_comp['pure_game'].sum()
                
                hw_map_wa = {"PS1":"PS5", "PS2":"PS5", "PS3":"PS5", "PC1":"PC", "PC2":"PC", "SIM1":"SIM"}
                today_comp['Category'] = today_comp['system'].map(hw_map_wa).fillna(today_comp['system'])
                today_hw_group = today_comp.groupby('Category')['pure_game'].sum()
                ps_wa = today_hw_group.get('PS5', 0.0)
                pc_wa = today_hw_group.get('PC', 0.0)
                sim_wa = today_hw_group.get('SIM', 0.0)
            else:
                comp_df = pd.DataFrame()
                checkout_cash = checkout_upi = pure_game_rev = 0.0
                ps_wa = pc_wa = sim_wa = 0.0

            total_drawer_cash = checkout_cash + direct_fnb_cash
            total_bank_upi = checkout_upi + direct_fnb_upi
            total_revenue = pure_game_rev + gross_fnb_profit
            
            # --- Render Today's Master Summary ---
            st.write("### 📅 Today's Master Summary")
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"<div class='metric-box' style='border-color:#4F46E5'>Net Revenue (Game + F&B Profit)<h2 style='color:#4F46E5'>₹{total_revenue:,.0f}</h2></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='metric-box'>Total Cash (Drawer)<h2 style='color:white'>₹{total_drawer_cash:,.0f}</h2></div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='metric-box'>Total UPI (Bank)<h2 style='color:white'>₹{total_bank_upi:,.0f}</h2></div>", unsafe_allow_html=True)
            
            st.write("### 🎮 Today's Gaming Breakdown")
            st.markdown(f"<div class='metric-box' style='border-color:#98DED9'>Pure Gaming Sale (Hardware Time Only)<h2 style='color:#98DED9'>₹{pure_game_rev:,.0f}</h2></div>", unsafe_allow_html=True)
            
            st.write("### 🍔 Today's F&B Breakdown")
            f1, f2 = st.columns(2)
            f1.markdown(f"<div class='metric-box' style='border-color:#34D399'>Total F&B Sale<h2 style='color:#34D399'>₹{gross_fnb_sale:,.0f}</h2></div>", unsafe_allow_html=True)
            f2.markdown(f"<div class='metric-box' style='border-color:#10B981'>F&B Profit (Yours)<h2 style='color:#10B981'>₹{gross_fnb_profit:,.0f}</h2></div>", unsafe_allow_html=True)
            
            st.write("### 📱 One-Click WhatsApp Report")
            today_date_obj = datetime.now(IST)
            date_str_wa = f"{get_ordinal(today_date_obj.day)} {today_date_obj.strftime('%B')}"
            
            whatsapp_msg = f"""*Today's income - {date_str_wa}*

a. Cash - {total_drawer_cash:,.0f}
b. UPI -  {total_bank_upi:,.0f}
c. F&B sale - {gross_fnb_sale:,.0f}
d. F&B profit- {gross_fnb_profit:,.0f}

*A+B-C+D= Total  - {total_revenue:,.0f}*

Breakup: 
PS5- {ps_wa:,.0f}
PC- {pc_wa:,.0f}
SIM- {sim_wa:,.0f}"""

            st.code(whatsapp_msg, language='markdown')
            
            st.divider()
            
            st.write("### 📅 Custom Hardware Breakdown")
            d_range_hw = st.date_input("Select Date or Range to analyze hardware performance", [datetime.now(IST).date(), datetime.now(IST).date()], key="t5_hw_range")
            if len(d_range_hw) == 2:
                s_dt, e_dt = [d.strftime('%Y-%m-%d') for d in d_range_hw]
                if not vdf.empty:
                    hw_filter = vdf[(vdf['date_str'] >= s_dt) & (vdf['date_str'] <= e_dt) & (vdf['status'] == 'Completed')].copy()
                    
                    if not hw_filter.empty:
                        hw_filter['total'] = pd.to_numeric(hw_filter['total'], errors='coerce').fillna(0.0)
                        hw_filter['fnb_total'] = pd.to_numeric(hw_filter['fnb_total'], errors='coerce').fillna(0.0)
                        hw_filter['pure_game'] = hw_filter['total'] - hw_filter['fnb_total']
                        
                        hw_map = {"PS1":"PlayStation", "PS2":"PlayStation", "PS3":"PlayStation", 
                                  "PC1":"PC", "PC2":"PC", "SIM1":"Simulator"}
                        hw_filter['Category'] = hw_filter['system'].map(hw_map).fillna(hw_filter['system'])
                        
                        hw_group = hw_filter.groupby('Category')['pure_game'].sum()
                        
                        ps_rev = hw_group.get('PlayStation', 0.0)
                        pc_rev = hw_group.get('PC', 0.0)
                        sim_rev = hw_group.get('Simulator', 0.0)
                        
                        h1, h2, h3 = st.columns(3)
                        h1.markdown(f"<div class='metric-box' style='border-color:#0070D1'>PlayStation (PS1-PS3)<h2 style='color:#0070D1'>₹{ps_rev:,.0f}</h2></div>", unsafe_allow_html=True)
                        h2.markdown(f"<div class='metric-box' style='border-color:#10B981'>PC (PC1-PC2)<h2 style='color:#10B981'>₹{pc_rev:,.0f}</h2></div>", unsafe_allow_html=True)
                        h3.markdown(f"<div class='metric-box' style='border-color:#F59E0B'>Simulator (SIM1)<h2 style='color:#F59E0B'>₹{sim_rev:,.0f}</h2></div>", unsafe_allow_html=True)
                    else:
                        st.info("No completed gaming sessions found in this date range.")
                else:
                    st.info("No sales data available to analyze.")

            st.divider()
            st.write("### Export Data")
            d_range = st.date_input("Select Date Range to Export", [datetime.now(IST).date(), datetime.now(IST).date()], key="t5_drange")
            if len(d_range) == 2:
                s_dt, e_dt = [d.strftime('%Y-%m-%d') for d in d_range]
                f_edf = vdf[(vdf['date_str'] >= s_dt) & (vdf['date_str'] <= e_dt)] if not vdf.empty else pd.DataFrame()
                if not f_edf.empty:
                    st.download_button("📥 Export CSV", f_edf.to_csv(index=False).encode('utf-8'), f"Export_{s_dt}_to_{e_dt}.csv", "text/csv", key="t5_export_btn")
            
            st.divider()

            # --- Executive Revenue Dashboard ---
            if not comp_df.empty:
                daily_game = comp_df.groupby('date_str')['pure_game'].sum().reset_index()
                
                if not cafe_all_df.empty:
                    cafe_all_df['date_str'] = cafe_all_df['date'].str[:10]
                    cafe_all_df['total_revenue'] = pd.to_numeric(cafe_all_df['total_revenue'], errors='coerce').fillna(0.0)
                    daily_fnb = cafe_all_df.groupby('date_str')['total_revenue'].sum().reset_index()
                else:
                    daily_fnb = pd.DataFrame(columns=['date_str', 'total_revenue'])

                master_ledger = pd.merge(daily_game, daily_fnb, on='date_str', how='outer').fillna(0.0)
                master_ledger['Gross Income'] = master_ledger['pure_game'] + master_ledger['total_revenue']

                revenue_df = master_ledger[['date_str', 'Gross Income']].rename(columns={'Gross Income': 'total'})
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
                
                st.write("### 🎮 Lifetime Hardware Breakdown (Pure Gaming)")
                hw_map = {"PC1":"PC", "PC2":"PC", "PS1":"PS5", "PS2":"PS5", "PS3":"PS5", "SIM1":"Racing Sim"}
                comp_df['Category'] = comp_df['system'].map(hw_map).fillna(comp_df['system'])
                comp_df['date_obj'] = pd.to_datetime(comp_df['date_str'])
                
                hw_life = comp_df.groupby('Category')['pure_game'].sum().rename('Lifetime Gross')
                hw_tm = comp_df[comp_df['date_obj'].dt.date >= start_tm].groupby('Category')['pure_game'].sum().rename('This Month')
                hw_lm = comp_df[(comp_df['date_obj'].dt.date >= start_lm) & (comp_df['date_obj'].dt.date <= end_lm)].groupby('Category')['pure_game'].sum().rename('Last Month')
                
                hw_summary = pd.concat([hw_life, hw_tm, hw_lm], axis=1).fillna(0).reset_index()
                st.dataframe(hw_summary, hide_index=True, use_container_width=True)

            st.divider()

            if not vdf.empty:
                st.subheader("📅 Day-Wise Profit & Loss Ledger")
                tot_inc = revenue_df[['date_str', 'total']].rename(columns={'total': 'Gross Income'})
                
                # THE FIX: Enforce live fetch for Expenses ledger
                exp_raw = conn.table("expenses").select("*").execute(ttl=0)
                exp_df = pd.DataFrame(exp_raw.data)
                if not exp_df.empty:
                    exp_df['amount'] = pd.to_numeric(exp_df['amount'], errors='coerce').fillna(0.0)
                    exp_summary = exp_df.groupby('expense_date')['amount'].sum().rename('Total Expenses').reset_index()
                    master_ledger = pd.merge(tot_inc, exp_summary, left_on='date_str', right_on='expense_date', how='outer').fillna(0)
                else:
                    master_ledger = tot_inc; master_ledger['Total Expenses'] = 0
                
                master_ledger['Net Profit'] = master_ledger['Gross Income'] - master_ledger['Total Expenses']
                master_ledger = master_ledger.sort_values('date_str', ascending=False)
                st.dataframe(master_ledger[['date_str', 'Gross Income', 'Total Expenses', 'Net Profit']], hide_index=True, use_container_width=True)

        except Exception as e: st.error(f"Vault processing error: {e}")

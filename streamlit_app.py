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
    
    /* Deep Obsidian Background */
    .stApp, .stApp > header { background-color: #0B0E14; color: #FFFFFF; }
    
    /* Force all text to Pure White for contrast */
    h1, h2, h3, h4, p, span, label, div { color: #FFFFFF !important; }
    
    /* Glowing Ice Blue Primary Buttons */
    .stButton>button { 
        background: linear-gradient(135deg, #00D0FF 0%, #0080FF 100%); 
        color: #FFFFFF !important; 
        border-radius: 8px; 
        width: 100%; 
        font-weight: 700; 
        border: none; 
        transition: 0.3s; 
        box-shadow: 0 4px 15px rgba(0, 208, 255, 0.25);
    }
    .stButton>button:hover { 
        background: linear-gradient(135deg, #00BFFF 0%, #0066CC 100%); 
        transform: translateY(-2px); 
        box-shadow: 0 6px 20px rgba(0, 208, 255, 0.4);
    }
    
    /* Panels & Metric Boxes */
    .metric-box { 
        background-color: #121824; 
        padding: 20px; 
        border-radius: 12px; 
        text-align: center; 
        border-top: 3px solid #00D0FF; 
        margin-bottom: 15px; 
        box-shadow: 0 4px 10px rgba(0,0,0,0.5); 
    }
    .panel-box { 
        background: #121824; 
        padding: 20px; 
        border-radius: 16px; 
        border: 1px solid #1E293B; 
        box-shadow: 0 4px 10px rgba(0,0,0,0.5); 
    }
    
    /* POS Menu Buttons */
    .menu-btn>button { 
        background: #1A2235; 
        border: 1px solid #2D3748; 
        height: 70px; 
        border-radius: 10px; 
        color: #E2E8F0 !important;
        transition: 0.2s;
    }
    .menu-btn>button:hover { 
        border-color: #00D0FF; 
        color: #00D0FF !important; 
        box-shadow: 0 0 12px rgba(0, 208, 255, 0.2); 
    }
    
    /* Make Input boxes blend with the dark theme */
    input, select, .stSelectbox > div > div { 
        background-color: #1A2235 !important; 
        color: white !important; 
        border: 1px solid #2D3748 !important; 
    }
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

# --- SYSTEM SIDEBAR ---
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
VENDOR_CATS = ["Burgers & Meals", "Fries & Snacks"]

def get_price(cat, dur, extra=0):
    full_hours = int(dur)
    half_hours = 1 if (dur % 1) != 0 else 0
    if cat == "PC": return (full_hours * 100) + (half_hours * 70)
    elif cat == "Racing Sim": return (full_hours * 250) + (half_hours * 150)
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

try:
    inv_res = conn.table("inventory").select("*").order('item_name').limit(10000).execute()
    inv_df = pd.DataFrame(inv_res.data) if inv_res.data else pd.DataFrame(columns=inv_cols)
    
    active_res = conn.table("sales").select("*").in_("status", ["Active", "Booked"]).order('id', desc=True).limit(10000).execute()
    db_df = pd.DataFrame(active_res.data) if active_res.data else pd.DataFrame(columns=db_cols)
    
    today_str_query = datetime.now(IST).strftime('%Y-%m-%d')
    tab_res = conn.table("sales").select("*").eq("status", "Completed").eq("method", "Master Tab").gte("date", today_str_query).order('id', desc=True).limit(10000).execute()
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

# --- 4. TABS LAYOUT (REDUCED TO 4 TABS) ---
t1, t2, t3, t4 = st.tabs(["🕹️ Live Floor", "🍔 Cafe & Stock", "📅 Bookings & Queue", "🧠 Master Vault"])

# ==========================================
# TAB 1: LIVE FLOOR & CHECKOUT
# ==========================================
with t1:
    # --- ADDED: PENDING FLOOR BANNER ---
    pending_floor = 0.0
    active_gamers = db_df[db_df['status'] == 'Active'] if not db_df.empty else pd.DataFrame()
    
    if not active_gamers.empty:
        pending_floor = pd.to_numeric(active_gamers['total'], errors='coerce').fillna(0.0).sum()
        
    st.markdown(f"<div class='metric-box' style='border-color:#FF754C; padding: 15px; margin-bottom: 20px;'><h3>Pending on Floor: <span style='color:#FF754C;'>₹{pending_floor:,.0f}</span></h3></div>", unsafe_allow_html=True)
    
    col_floor, col_op = st.columns([2.5, 1], gap="large")
    
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
                    b_col = "#00D0FF"
                    bg_col = "#121824"
                    t_col = "#00D0FF"
                    txt = f"⏳ {int(time_left)}m left"
                
                fnb_val = float(row.get('fnb_total') or 0.0)
                game_val = float(row.get('total') or 0.0)
                fnb_html = f"<span style='background:#42201D; color:#FF754C; padding:6px 14px; border-radius:8px; font-size:14px; font-weight:700; box-shadow: 0 2px 4px rgba(0,0,0,0.2);'>🍔 ₹{fnb_val:.0f}</span>" if fnb_val > 0 else ""

                card_html = (
                    f"<div style='background:{bg_col}; border:1px solid #1E293B; border-top:4px solid {b_col}; border-radius:14px; padding:20px; margin-bottom:15px; box-shadow: 0 4px 6px rgba(0,0,0,0.4);'>"
                    f"<div style='display:flex; justify-content:space-between; align-items:center; border-bottom: 1px solid #1E293B; padding-bottom: 10px; margin-bottom: 15px;'>"
                    f"<span style='color:white; font-size:18px; font-weight:800; letter-spacing: 0.5px;'>{row['system']}</span>"
                    f"<span style='color:#9CA3AF; font-size:14px; font-weight:600;'>{row['customer']} • <span style='color:#00D0FF;'>In: {row['entry_time']}</span></span>"
                    f"</div>"
                    f"<div style='text-align: center; margin-bottom: 15px;'>"
                    f"<h2 style='color:{t_col}; margin:0; padding:0; font-size:34px; font-weight:900; letter-spacing: 0.5px;'>{txt}</h2>"
                    f"</div>"
                    f"<div style='display:flex; gap:10px; justify-content: center; flex-wrap:wrap;'>"
                    f"<span style='background:#1A2235; color:#00D0FF; padding:6px 14px; border-radius:8px; font-size:14px; font-weight:700; box-shadow: 0 2px 4px rgba(0,0,0,0.3); border:1px solid #2D3748;'>🎮 ₹{game_val:.0f}</span>"
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
        
        st.markdown("<hr style='border-color: #2D3748;'>", unsafe_allow_html=True)
        st.subheader("💳 Settle Unpaid Tabs")
        if not tab_df.empty:
            unpaid_customers = tab_df['customer'].unique()
            sel_unpaid_cust = st.selectbox("Select Gamer to Settle", unpaid_customers, key="t1_unpaid_sel")
            
            cust_tabs = tab_df[tab_df['customer'] == sel_unpaid_cust]
            total_owed = cust_tabs['total'].sum()
            
            st.info(f"**{sel_unpaid_cust}** owes: **₹{total_owed:.0f}**")
            
            settle_pay = st.radio("Settle Method", ["Cash", "UPI", "Split Payment"], horizontal=True, key=f"t1_settle_pay_{sel_unpaid_cust}")
            
            final_settle_meth = settle_pay
            if settle_pay == "Split Payment":
                settle_split_cash = st.number_input("Cash Portion (₹)", min_value=0.0, max_value=float(total_owed), value=float(total_owed)/2, step=10.0, key=f"t1_settle_split_{sel_unpaid_cust}")
                st.caption(f"UPI Portion: ₹{total_owed - settle_split_cash:.0f}")
                final_settle_meth = f"Split|{settle_split_cash}|{total_owed - settle_split_cash}"
                
            if st.button("✅ Settle Tab", use_container_width=True, key=f"t1_settle_btn_{sel_unpaid_cust}"):
                for past_id in cust_tabs['id']:
                    conn.table("sales").update({"method": final_settle_meth}).eq("id", int(past_id)).execute()
                st.cache_data.clear()
                st.success(f"{sel_unpaid_cust}'s tab settled successfully!")
                st.rerun()
        else:
            st.caption("No unpaid tabs pending today.")
            
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
                        "method": "Tab" if assign == "Add to Active Gamer" else

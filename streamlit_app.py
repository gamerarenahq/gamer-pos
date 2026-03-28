with col1:
                    st.markdown(f"<div class='metric-box'><h4>Week-to-Date (WTD)</h4><h2>₹{wtd_data['total'].sum():,.2f}</h2><p>{len(wtd_data)} Sessions | {wtd_data['duration'].sum()} Hrs</p></div>", unsafe_allow_html=True)
                    st.write("")
                    st.markdown(f"<div class='metric-box'><h4>Month-to-Date (MTD)</h4><h2>₹{mtd_data['total'].sum():,.2f}</h2><p>{len(mtd_data)} Sessions | {mtd_data['duration'].sum()} Hrs</p></div>", unsafe_allow_html=True)

                with col2:
                    st.markdown(f"<div class='metric-box'><h4>Last Week (Full)</h4><h2>₹{last_week_data['total'].sum():,.2f}</h2><p>{len(last_week_data)} Sessions | {last_week_data['duration'].sum()} Hrs</p></div>", unsafe_allow_html=True)
                    st.write("")
                    st.markdown(f"<div class='metric-box'><h4>Last Month (Full)</h4><h2>₹{last_month_data['total'].sum():,.2f}</h2><p>{len(last_month_data)} Sessions | {last_month_data['duration'].sum()} Hrs</p></div>", unsafe_allow_html=True)

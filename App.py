"""
Octa Working Hours — Main Entry Point
"""
import streamlit as st
from config import APP_NAME, APP_ICON, DARK
from modules.ui_helpers import inject_css, sidebar_nav
from modules.auth import is_authenticated, clear_session, is_admin

st.set_page_config(
    page_title=APP_NAME,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

if not is_authenticated():
    st.switch_page("pages/login.py")

sidebar_nav()

# ── Welcome hero ──────────────────────────────────────────────────────────────
uname     = st.session_state.get("first_name") or st.session_state.get("username", "")
org       = st.session_state.get("organisation", "")

st.markdown(f"""
<div style="background:linear-gradient(135deg,{DARK['sidebar']} 0%,#2d4a7a 100%);
            border-radius:14px;padding:2rem 2.5rem;margin-bottom:2rem;
            border-left:5px solid {DARK['accent']}">
    <h1 style="color:white;margin:0;font-size:2rem;font-weight:800">
        ⏱️ Welcome, {uname}!
    </h1>
    <p style="color:rgba(255,255,255,0.7);margin:0.4rem 0 0;font-size:0.95rem">
        {org + ' · ' if org else ''}Octa Working Hours System
    </p>
</div>
""", unsafe_allow_html=True)

# ── Quick action cards ────────────────────────────────────────────────────────
c1, c2, c3 = st.columns(3)

cards = [
    ("📊", "My Dashboard",      "View your working hours summary and statistics.",
     "pages/dashboard.py",  DARK["accent"]),
    ("➕", "Log Working Hours", "Add today's or previous working hours to a proposal or project.",
     "pages/add_hours.py",  DARK["accent2"]),
    ("🛡️", "Admin Panel",      "Approve or return working hours for your team.",
     "pages/admin.py",       DARK["success"]),
]

for col, (icon, title, desc, page, color) in zip([c1, c2, c3], cards):
    if title == "Admin Panel" and not is_admin():
        continue
    with col:
        st.markdown(f"""
        <div style="background:{DARK['bg2']};border:1px solid {color}44;
                    border-top:4px solid {color};border-radius:12px;
                    padding:1.5rem;height:160px;
                    display:flex;flex-direction:column;justify-content:space-between">
            <div>
                <div style="font-size:2rem;margin-bottom:0.5rem">{icon}</div>
                <strong style="color:{DARK['text']};font-size:1rem">{title}</strong><br>
                <span style="color:{DARK['muted']};font-size:0.83rem">{desc}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button(f"Open {title}", key=f"btn_{title}",
                     use_container_width=True):
            st.switch_page(page)

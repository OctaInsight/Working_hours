"""Octa Working Hours — Shared UI helpers and dark-mode CSS."""
import streamlit as st
from config import DARK, APP_NAME, APP_VERSION

GLOBAL_CSS = f"""
<style>
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > section,
[data-testid="block-container"] {{
    background-color: {DARK['bg']} !important;
    color: {DARK['text']} !important;
}}
[data-testid="stVerticalBlock"],
[data-testid="stHorizontalBlock"],
[data-testid="column"],
.element-container, .stMarkdown {{
    background: transparent !important;
}}
h1,h2,h3,h4 {{ color: {DARK['text']} !important; }}
p, li {{ color: {DARK['text']}; }}
label, .stTextInput label, .stSelectbox label,
.stMultiselect label, .stTextArea label,
.stNumberInput label, .stDateInput label,
.stTimeInput label {{
    color: {DARK['muted']} !important;
    font-size: 0.85rem !important;
}}
[data-testid="stSidebar"] {{
    background: {DARK['sidebar']} !important;
    border-right: 3px solid {DARK['accent']} !important;
    box-shadow: 4px 0 20px rgba(0,188,212,0.1) !important;
}}
[data-testid="stSidebar"] * {{ color: {DARK['text']} !important; }}
[data-testid="stSidebarNav"] {{ display: none !important; }}
[data-testid="stSidebar"] [data-testid="stPageLink"] {{
    width: 100% !important; display: block !important;
}}
[data-testid="stSidebar"] [data-testid="stPageLink"] a {{
    display: block !important; width: 100% !important;
    padding: 0.45rem 0.8rem !important; border-radius: 8px !important;
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    color: {DARK['text']} !important; text-decoration: none !important;
    font-size: 0.88rem !important; margin-bottom: 3px !important;
    transition: all 0.18s !important;
}}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {{
    background: {DARK['accent']}22 !important;
    border-color: {DARK['accent']}66 !important;
    color: {DARK['accent']} !important;
}}
[data-testid="stSidebar"] [data-testid="stPageLink-active"] a {{
    background: {DARK['accent']}30 !important;
    border-color: {DARK['accent']} !important;
    color: {DARK['accent']} !important; font-weight: 600 !important;
}}
[data-testid="stSidebar"] .stButton > button {{
    background: rgba(252,129,129,0.12) !important;
    border: 1px solid rgba(252,129,129,0.3) !important;
    border-radius: 8px !important; width: 100% !important;
    color: {DARK['danger']} !important; font-size: 0.85rem !important;
}}
[data-testid="stSidebar"] .stButton > button:hover {{
    background: rgba(252,129,129,0.25) !important;
    border-color: {DARK['danger']} !important;
}}
input, textarea, input[type="text"],
input[type="number"], input[type="email"] {{
    background: {DARK['bg3']} !important;
    border: 1px solid {DARK['border']} !important;
    border-radius: 8px !important; color: {DARK['text']} !important;
}}
input::placeholder, textarea::placeholder {{
    color: {DARK['muted']} !important;
}}
div[data-baseweb="select"] > div {{
    background: {DARK['bg3']} !important;
    border-color: {DARK['border']} !important;
    color: {DARK['text']} !important;
}}
div[data-baseweb="select"] * {{ color: {DARK['text']} !important; }}
div[data-baseweb="popover"] {{
    background: {DARK['bg2']} !important;
    border: 1px solid {DARK['border']} !important;
}}
div[data-baseweb="popover"] li:hover {{ background: {DARK['bg3']} !important; }}
div[data-baseweb="calendar"],
div[data-baseweb="datepicker"] > div,
div[data-baseweb="timepicker"] > div {{
    background: {DARK['bg2']} !important; color: {DARK['text']} !important;
}}
[data-testid="stTabs"] [role="tablist"] {{
    background: {DARK['bg2']}; border-radius: 10px;
    padding: 4px; border: 1px solid {DARK['border']};
}}
[data-testid="stTabs"] [role="tab"] {{
    color: {DARK['muted']} !important; border-radius: 8px;
}}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {{
    background: {DARK['accent']} !important; color: white !important;
}}
[data-testid="stButton"] > button {{
    background: {DARK['bg3']} !important;
    border: 1px solid {DARK['border']} !important;
    color: {DARK['text']} !important; border-radius: 8px !important;
    transition: all 0.2s !important;
}}
[data-testid="stButton"] > button:hover {{
    border-color: {DARK['accent']} !important;
    color: {DARK['accent']} !important;
}}
[data-testid="stButton"] > button[kind="primary"] {{
    background: linear-gradient(135deg,{DARK['accent']},#0097A7) !important;
    border: none !important; color: white !important; font-weight: 600 !important;
}}
[data-testid="stExpander"] {{
    background: {DARK['bg2']} !important;
    border: 1px solid {DARK['border']} !important;
    border-radius: 10px !important;
}}
[data-testid="stExpander"] summary {{ color: {DARK['text']} !important; }}
[data-testid="stAlert"] {{ border-radius: 10px !important; }}
[data-testid="stAlert"][kind="info"]    {{ background: rgba(0,188,212,0.12) !important; }}
[data-testid="stAlert"][kind="success"] {{ background: rgba(40,167,69,0.12) !important; }}
[data-testid="stAlert"][kind="warning"] {{ background: rgba(255,193,7,0.12) !important; }}
[data-testid="stAlert"][kind="error"]   {{ background: rgba(220,53,69,0.12) !important; }}
[data-testid="stDataFrame"] {{ background: {DARK['bg2']} !important; }}
hr {{ border-color: {DARK['border']} !important; }}
::-webkit-scrollbar {{ width: 6px; }}
::-webkit-scrollbar-track {{ background: {DARK['bg']}; }}
::-webkit-scrollbar-thumb {{ background: {DARK['bg3']}; border-radius: 3px; }}

.page-header {{
    background: linear-gradient(135deg,{DARK['sidebar']} 0%,#2d4a7a 100%);
    padding: 1.4rem 2rem; border-radius: 12px;
    border-left: 4px solid {DARK['accent']};
    margin-bottom: 1.5rem; box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}}
.page-header h1 {{
    margin: 0; font-size: 1.7rem; font-weight: 700; color: white !important;
}}
.page-header p {{
    margin: 0.25rem 0 0; color: rgba(255,255,255,0.7) !important;
    font-size: 0.92rem;
}}
.section-label {{
    font-size: 0.72rem; font-weight: 600; letter-spacing: 0.08em;
    text-transform: uppercase; color: {DARK['accent']};
    margin: 1.4rem 0 0.6rem; padding-bottom: 0.3rem;
    border-bottom: 1px solid {DARK['border']};
}}
.stat-box {{
    background: {DARK['bg2']}; border: 1px solid {DARK['border']};
    border-top: 3px solid {DARK['accent']}; border-radius: 12px;
    padding: 1.2rem; text-align: center;
}}
.stat-val {{ font-size: 2rem; font-weight: 700; color: {DARK['text']}; line-height:1; }}
.stat-lbl {{ font-size: 0.8rem; color: {DARK['muted']}; margin-top: 0.3rem; }}
.status-approved {{ color: {DARK['success']}; font-weight: 600; }}
.status-pending  {{ color: {DARK['warning']}; font-weight: 600; }}
.status-returned {{ color: {DARK['danger']};  font-weight: 600; }}
</style>
"""


def inject_css():
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = "", icon: str = ""):
    st.markdown(f"""
    <div class="page-header">
        <h1>{icon + ' ' if icon else ''}{title}</h1>
        {'<p>' + subtitle + '</p>' if subtitle else ''}
    </div>
    """, unsafe_allow_html=True)


def section_label(text: str):
    st.markdown(f'<div class="section-label">{text}</div>',
                unsafe_allow_html=True)


def stat_box(col, label: str, value, accent_color: str = None):
    color = accent_color or DARK["accent"]
    with col:
        st.markdown(f"""
        <div class="stat-box" style="border-top-color:{color}">
            <div class="stat-val" style="color:{color}">{value}</div>
            <div class="stat-lbl">{label}</div>
        </div>
        """, unsafe_allow_html=True)


def status_pill(status: str) -> str:
    icons = {"approved": "✅", "pending": "⏳", "returned": "↩️"}
    css   = {"approved": "status-approved", "pending": "status-pending",
             "returned": "status-returned"}
    icon  = icons.get(status, "")
    cls   = css.get(status, "")
    return f'<span class="{cls}">{icon} {status.capitalize()}</span>'


def sidebar_nav():
    """Sidebar navigation for Octa Working Hours app."""
    is_auth       = st.session_state.get("authenticated", False)
    is_admin_user = st.session_state.get("role") == "admin"
    uname         = (st.session_state.get("first_name") or
                     st.session_state.get("username", ""))

    with st.sidebar:
        # Logo
        st.markdown(f"""
<div style="text-align:center;padding:1rem 0 0.8rem">
<div style="font-size:2rem">⏱️</div>
<div style="font-weight:700;font-size:1rem;color:{DARK['text']}">{APP_NAME}</div>
<div style="color:{DARK['muted']};font-size:0.68rem">v{APP_VERSION}</div>
</div>""", unsafe_allow_html=True)

        # User badge
        if is_auth and uname:
            st.markdown(
                f"<div style='background:rgba(255,255,255,0.07);"
                f"border:1px solid rgba(255,255,255,0.12);border-radius:8px;"
                f"padding:0.4rem 0.8rem;font-size:0.82rem;margin-bottom:0.4rem'>"
                f"👤 <strong style='color:{DARK['text']}'>{uname}</strong>"
                f"</div>",
                unsafe_allow_html=True
            )

        st.markdown("<hr style='border:none;border-top:1px solid rgba(255,255,255,0.12);"
                    "margin:0.3rem 0 0.5rem'>", unsafe_allow_html=True)

        # Navigation
        st.markdown(f"<div style='font-size:0.68rem;font-weight:600;letter-spacing:0.1em;"
                    f"text-transform:uppercase;color:{DARK['muted']};margin-bottom:0.3rem'>"
                    f"Navigation</div>", unsafe_allow_html=True)

        if st.button("🏠  Home",                  key="nav_home",  use_container_width=True): st.switch_page("pages/dashboard.py")
        if st.button("📊  Overall Working Hours", key="nav_dash",  use_container_width=True): st.switch_page("pages/dashboard.py")
        if st.button("➕  Add Working Hours",     key="nav_add",   use_container_width=True): st.switch_page("pages/add_hours.py")
        if st.button("📌  Assign Task",             key="nav_assign", use_container_width=True): st.switch_page("pages/assign_task.py")
        if st.button("✅  My Tasks",                key="nav_tasks",  use_container_width=True): st.switch_page("pages/my_tasks.py")

        # Admin
        if is_admin_user:
            st.markdown("<hr style='border:none;border-top:1px solid rgba(255,255,255,0.12);"
                        "margin:0.5rem 0'>", unsafe_allow_html=True)
            st.markdown(f"<div style='font-size:0.68rem;font-weight:600;letter-spacing:0.1em;"
                        f"text-transform:uppercase;color:{DARK['muted']};margin-bottom:0.3rem'>"
                        f"Administration</div>", unsafe_allow_html=True)
            if st.button("🛡️  Admin Panel", key="nav_admin", use_container_width=True): st.switch_page("pages/admin.py")

        # Account
        st.markdown("<hr style='border:none;border-top:1px solid rgba(255,255,255,0.12);"
                    "margin:0.5rem 0'>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size:0.68rem;font-weight:600;letter-spacing:0.1em;"
                    f"text-transform:uppercase;color:{DARK['muted']};margin-bottom:0.3rem'>"
                    f"Account</div>", unsafe_allow_html=True)

        if is_auth:
            if st.button("🚪  Sign Out", use_container_width=True, key="sidebar_signout"):
                from modules.auth import clear_session
                clear_session()
                st.switch_page("pages/login.py")
        else:
            if st.button("🔑  Login / Register", use_container_width=True, key="nav_login"): st.switch_page("pages/login.py")

        # Footer
        st.markdown(
            f"<div style='color:{DARK['muted']};font-size:0.65rem;"
            f"text-align:center;margin-top:1.5rem'>"
            f"Octa Platform · {__import__('datetime').date.today().year}"
            f"</div>",
            unsafe_allow_html=True
        )

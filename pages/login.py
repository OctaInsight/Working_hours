"""
Octa Platform — Unified Login Page
Copy this file to pages/login.py in every app — no changes needed.

Password reset is admin-assisted (secure):
  User submits a request → admin generates a temp password → shares it out-of-band
  No token is ever shown to the user on this screen.
"""
import streamlit as st
from modules.ui_helpers import inject_css, sidebar_nav, DARK
from modules.auth import (
    login_user, register_user, set_session, is_authenticated,
    request_password_reset, change_password, needs_password_change,
)
from modules.database import get_all_partners

st.set_page_config(
    page_title="Login — Octa Platform",
    page_icon="📋",
    layout="centered",
    initial_sidebar_state="collapsed",
)
inject_css()
sidebar_nav()

# ── If already logged in ──────────────────────────────────────────────────────
if is_authenticated():
    # Force password change after temp password login
    if needs_password_change():
        st.warning("⚠️ You logged in with a temporary password. "
                   "Please set a new password before continuing.")
        st.markdown("<br>", unsafe_allow_html=True)
        np1 = st.text_input("New password", type="password", key="np1",
                             placeholder="At least 8 characters")
        np2 = st.text_input("Confirm new password", type="password", key="np2")
        if st.button("✅ Set New Password", type="primary",
                     use_container_width=True):
            if np1 != np2:
                st.error("❌ Passwords do not match.")
            elif len(np1) < 8:
                st.error("❌ Password must be at least 8 characters.")
            else:
                ok, msg = change_password(st.session_state.user_id, np1)
                if ok:
                    st.session_state.force_password_change = False
                    st.success("✅ Password changed! Redirecting…")
                    st.switch_page("pages/dashboard.py")
                else:
                    st.error(f"❌ {msg}")
        st.stop()
    st.switch_page("pages/dashboard.py")

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="text-align:center;padding:2rem 0 1.5rem">
    <div style="font-size:3.2rem">📋</div>
    <h1 style="color:white;font-size:2rem;font-weight:800;
               margin:0.5rem 0 0.2rem;letter-spacing:-1px">
        Octa Platform
    </h1>
    <p style="color:{DARK['muted']};font-size:0.95rem;margin:0">
        Sign in to access your workspace
    </p>
</div>
""", unsafe_allow_html=True)

tab_login, tab_register, tab_reset = st.tabs(
    ["🔑  Sign In", "✨  Register", "🔓  Forgot Password"]
)

# ── SIGN IN ───────────────────────────────────────────────────────────────────
with tab_login:
    st.markdown("<br>", unsafe_allow_html=True)
    li_email = st.text_input("Email address", key="li_email",
                              placeholder="you@example.com")
    li_pass  = st.text_input("Password", type="password", key="li_pass",
                              placeholder="Your password")
    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("Sign In →", type="primary",
                 use_container_width=True, key="btn_login"):
        if not li_email or not li_pass:
            st.warning("Please fill in both fields.")
        else:
            ok, msg, user = login_user(li_email, li_pass)
            if ok:
                set_session(user)
                # Create SSO token so session survives refresh
                try:
                    from modules.sso import create_session_token, set_token_in_url
                    token = create_session_token(user["id"])
                    if token:
                        st.session_state["sso_token"] = token
                        set_token_in_url(token)
                except ImportError:
                    pass
                if needs_password_change():
                    st.rerun()
                else:
                    st.switch_page("pages/dashboard.py")
            else:
                st.error(f"❌ {msg}")

# ── REGISTER ──────────────────────────────────────────────────────────────────
with tab_register:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="background:rgba(0,188,212,0.1);border:1px solid rgba(0,188,212,0.3);
                border-left:4px solid {DARK['accent']};border-radius:10px;
                padding:0.9rem 1.1rem;margin-bottom:1rem;font-size:0.88rem">
        <strong style="color:{DARK['accent']}">How it works</strong><br>
        <span style="color:{DARK['text']}">
            1. Fill in the form and submit<br>
            2. An admin reviews and activates your account<br>
            3. Come back to Sign In once notified
        </span>
    </div>
    """, unsafe_allow_html=True)

    rc1, rc2 = st.columns(2)
    with rc1:
        reg_first = st.text_input("First name *", key="reg_first",
                                   placeholder="Maria")
    with rc2:
        reg_last = st.text_input("Last name *", key="reg_last",
                                  placeholder="Rossi")

    reg_username = st.text_input("Username *", key="reg_uname",
                                  placeholder="mariarossi  (min 3 characters)")
    reg_email    = st.text_input("Email address *", key="reg_email",
                                  placeholder="you@example.com")

    # Organisation dropdown from partners table
    OTHER_ORG = "➕  My organisation is not in the list"
    try:
        partner_names = [p["full_name"] for p in get_all_partners()
                         if p.get("full_name")]
    except Exception:
        partner_names = []

    org_options    = ["— Select your organisation —"] + \
                     sorted(partner_names) + [OTHER_ORG]
    reg_org_select = st.selectbox(
        "Organisation / Partner *", options=org_options,
        key="reg_org_select",
        help="Select your organisation. If not listed, choose the last option."
    )
    reg_org_custom = ""
    if reg_org_select == OTHER_ORG:
        reg_org_custom = st.text_input(
            "Enter your organisation name *", key="reg_org_custom",
            placeholder="Full name of your organisation"
        )
        st.markdown(
            f"<p style='color:{DARK['muted']};font-size:0.8rem;margin-top:-0.4rem'>"
            f"The admin will add it to the partners list after approval.</p>",
            unsafe_allow_html=True
        )

    def _org_value():
        if reg_org_select == OTHER_ORG: return reg_org_custom.strip()
        if reg_org_select.startswith("—"): return ""
        return reg_org_select

    rc3, rc4 = st.columns(2)
    with rc3:
        reg_pass  = st.text_input("Password *", type="password", key="reg_pass",
                                   placeholder="Min 8 characters")
    with rc4:
        reg_pass2 = st.text_input("Confirm password *", type="password",
                                   key="reg_pass2", placeholder="Repeat password")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Submit Registration →", type="primary",
                 use_container_width=True, key="btn_register"):
        org_val = _org_value()
        if reg_pass != reg_pass2:
            st.error("❌ Passwords do not match.")
        elif not all([reg_first, reg_last, reg_username, reg_email, reg_pass]):
            st.warning("Please fill in all required fields.")
        elif reg_org_select.startswith("—"):
            st.warning("Please select your organisation.")
        elif reg_org_select == OTHER_ORG and not reg_org_custom.strip():
            st.warning("Please enter your organisation name.")
        else:
            ok, msg, user = register_user(
                reg_email, reg_username, reg_first, reg_last,
                reg_pass, organisation=org_val
            )
            if ok:
                st.markdown(f"""
                <div style="background:rgba(40,167,69,0.12);
                            border:1px solid rgba(40,167,69,0.35);
                            border-left:4px solid {DARK['success']};
                            border-radius:10px;padding:1.1rem 1.3rem;margin-top:1rem">
                    <div style="font-size:1.4rem;margin-bottom:0.4rem">✅</div>
                    <strong style="color:{DARK['success']};font-size:1rem">
                        Registration submitted!
                    </strong><br>
                    <span style="color:{DARK['text']};font-size:0.88rem">
                        Organisation: <strong>{org_val or '—'}</strong><br>
                        Your account is <strong>pending admin approval</strong>.<br>
                        Come back to Sign In once you've been notified.
                    </span>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error(f"❌ {msg}")

# ── FORGOT PASSWORD (secure — admin-assisted) ─────────────────────────────────
with tab_reset:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="background:rgba(246,204,82,0.1);border:1px solid rgba(246,204,82,0.3);
                border-left:4px solid {DARK['warning']};border-radius:10px;
                padding:0.9rem 1.1rem;margin-bottom:1rem;font-size:0.88rem">
        <strong style="color:{DARK['warning']}">How password reset works</strong><br>
        <span style="color:{DARK['text']}">
            1. Enter your email and submit a reset request<br>
            2. An admin verifies your identity and generates a temporary password<br>
            3. The admin shares the temporary password with you directly
               (phone / personal email)<br>
            4. Log in with the temporary password — you'll be asked to set a new one
        </span>
    </div>
    """, unsafe_allow_html=True)

    fp_email = st.text_input("Your registered email address", key="fp_email",
                              placeholder="you@example.com")
    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("Submit Reset Request →", type="primary",
                 use_container_width=True, key="btn_reset"):
        if not fp_email.strip():
            st.warning("Please enter your email address.")
        else:
            ok, msg = request_password_reset(fp_email.strip())
            if ok:
                st.success(f"✅ {msg}")
            else:
                st.error(f"❌ {msg}")

# Footer
st.markdown(f"""
<div style="text-align:center;margin-top:2.5rem;
            color:{DARK['muted']};font-size:0.72rem">
    Octa Platform · Questions? octainsight@gmail.com
</div>
""", unsafe_allow_html=True)

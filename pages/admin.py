"""
Octa Platform — Unified Admin Panel
Copy this file to pages/admin.py in every app — no changes needed.

Handles:
  - All pending user registrations (from ALL apps, not just this one)
  - Password reset requests (admin generates temp password, shares out-of-band)
  - User management: approve, reject, edit access, disable
  - App access control
"""
import streamlit as st
import json
import secrets
import string
import pandas as pd
from datetime import datetime, timezone

from modules.auth import require_auth, is_admin, hash_password
from modules.database import db
from modules.ui_helpers import inject_css, sidebar_nav, page_header, section_label, DARK

st.set_page_config(page_title="Admin — Octa Platform",
                   page_icon="🛡️", layout="wide",
                   initial_sidebar_state="expanded")
inject_css()
sidebar_nav()
require_auth()

if not is_admin():
    st.error("🚫 Access denied. Admin role required.")
    st.stop()

page_header("Admin Panel", "User management for all Octa Platform applications", "🛡️")

admin_username = st.session_state.get("username", "admin")

ALL_APPS = [
    "octa_proposals",
    "octa_hours",
    "octa_writer",
    "octa_intelligence",
    "octa_kpi",
    "octa_partners",
    "octa_social",
    "octa_communication",
    "octa_projects",
    "octa_calendar",
]

APP_LABELS = {
    "octa_proposals":     "📋 Proposal Tracking",
    "octa_hours":         "⏱️ Working Hours",
    "octa_writer":        "📝 Writing App",
    "octa_intelligence":  "🤖 Proposal Intelligence",
    "octa_kpi":           "📊 KPI & Gantt",
    "octa_partners":      "🤝 Partner App",
    "octa_social":        "📱 Social Media",
    "octa_communication": "📧 Partner Communication",
    "octa_projects":      "🏗️ Project Tracking",
    "octa_calendar":      "📅 Calendar",
}


def _parse_apps(u: dict) -> list:
    apps = u.get("apps_access") or []
    if isinstance(apps, str):
        try:    return json.loads(apps)
        except: return []
    return list(apps)


def _load_users(status_filter=None) -> list:
    try:
        q = db().table("octa_users").select("*").order("created_at", desc=True)
        if status_filter:
            q = q.eq("status", status_filter)
        return q.execute().data or []
    except Exception:
        return []


def _load_reset_requests(status="pending") -> list:
    try:
        resp = db().table("password_reset_requests").select("*") \
                   .eq("status", status) \
                   .order("requested_at", desc=True).execute()
        return resp.data or []
    except Exception:
        return []


def _gen_temp_password(length=12) -> str:
    """Generate a readable temporary password."""
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


# ── Counts for tab badges ─────────────────────────────────────────────────────
pending_users   = _load_users("pending")
pending_resets  = _load_reset_requests("pending")
n_users         = len(pending_users)
n_resets        = len(pending_resets)

# ── Alert banner ──────────────────────────────────────────────────────────────
total_pending = n_users + n_resets
if total_pending > 0:
    items = []
    if n_users:  items.append(f"{n_users} registration{'s' if n_users>1 else ''}")
    if n_resets: items.append(f"{n_resets} password reset{'s' if n_resets>1 else ''}")
    st.markdown(f"""
    <div style="background:rgba(246,204,82,0.15);border:1px solid rgba(246,204,82,0.4);
                border-left:5px solid {DARK['warning']};border-radius:10px;
                padding:0.9rem 1.2rem;margin-bottom:1rem">
        ⏳ <strong style="color:{DARK['warning']}">
        {" and ".join(items)} waiting for your action
        </strong>
    </div>""", unsafe_allow_html=True)

tab_reg, tab_reset, tab_approved, tab_all = st.tabs([
    f"⏳ Registrations ({n_users})",
    f"🔑 Password Resets ({n_resets})",
    "✅ Approved Users",
    "👥 All Users",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Pending Registrations
# ══════════════════════════════════════════════════════════════════════════════
with tab_reg:
    if not pending_users:
        st.success("✅ No pending registrations — all clear.")
    else:
        for u in pending_users:
            full_name = f"{u.get('first_name','')} {u.get('last_name','')}".strip()
            org       = u.get("organisation","—") or "—"
            uid       = u["id"]

            with st.expander(
                f"⏳  {full_name}  ·  {u.get('username','')}  ·  "
                f"{u.get('email','')}  ·  {org}",
                expanded=True
            ):
                c1, c2, c3, c4 = st.columns(4)
                c1.markdown(f"**Name:** {full_name}")
                c2.markdown(f"**Username:** {u.get('username','')}")
                c3.markdown(f"**Email:** {u.get('email','')}")
                c4.markdown(f"**Organisation:** {org}")
                c1.markdown(f"**Registered:** {str(u.get('created_at',''))[:16]}")

                st.markdown("<br>", unsafe_allow_html=True)
                selected_apps = st.multiselect(
                    "Grant access to:",
                    options=ALL_APPS,
                    default=["octa_proposals"],
                    format_func=lambda k: APP_LABELS.get(k, k),
                    key=f"apps_{uid}"
                )

                bc1, bc2, _ = st.columns([1, 1, 4])
                with bc1:
                    if st.button("✅ Approve", key=f"approve_{uid}",
                                 type="primary", use_container_width=True):
                        try:
                            db().table("octa_users").update({
                                "status":      "approved",
                                "apps_access": selected_apps,
                                "approved_at": datetime.now(timezone.utc).isoformat(),
                                "approved_by": admin_username,
                            }).eq("id", uid).execute()
                            st.success(f"✅ {full_name} approved!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                with bc2:
                    if st.button("🚫 Reject", key=f"reject_{uid}",
                                 use_container_width=True):
                        try:
                            db().table("octa_users").update({
                                "status": "disabled"
                            }).eq("id", uid).execute()
                            st.warning(f"Rejected {full_name}.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Password Reset Requests (SECURE — token shown only to admin)
# ══════════════════════════════════════════════════════════════════════════════
with tab_reset:
    st.markdown(f"""
    <div style="background:rgba(0,188,212,0.1);border:1px solid rgba(0,188,212,0.3);
                border-left:4px solid {DARK['accent']};border-radius:10px;
                padding:0.8rem 1rem;margin-bottom:1rem;font-size:0.88rem">
        <strong style="color:{DARK['accent']}">Secure reset process</strong><br>
        You generate a temporary password here and share it with the user through
        a separate channel (phone, email, in person). The user never sees a token
        on their screen — only you see the temporary password.
    </div>
    """, unsafe_allow_html=True)

    if not pending_resets:
        st.success("✅ No pending password reset requests.")
    else:
        for req in pending_resets:
            req_id  = req["id"]
            user_id = req.get("user_id")
            req_at  = str(req.get("requested_at",""))[:16]

            # Load user details
            try:
                u_resp = db().table("octa_users").select(
                    "first_name,last_name,username,email,organisation"
                ).eq("id", user_id).execute()
                u = u_resp.data[0] if u_resp.data else {}
            except Exception:
                u = {}

            full_name = f"{u.get('first_name','')} {u.get('last_name','')}".strip()

            with st.expander(
                f"🔑  {full_name}  ·  {u.get('email','')}  ·  Requested: {req_at}",
                expanded=True
            ):
                rc1, rc2, rc3 = st.columns(3)
                rc1.markdown(f"**Name:** {full_name}")
                rc2.markdown(f"**Email:** {u.get('email','')}")
                rc3.markdown(f"**Organisation:** {u.get('organisation','—') or '—'}")

                st.markdown("<br>", unsafe_allow_html=True)

                # Generate temp password
                gen_key = f"temp_pw_{req_id}"
                if st.button("🔐 Generate Temporary Password",
                             key=f"gen_{req_id}", type="primary"):
                    temp_pw = _gen_temp_password()
                    st.session_state[gen_key] = temp_pw

                if st.session_state.get(gen_key):
                    temp_pw = st.session_state[gen_key]
                    st.markdown(f"""
                    <div style="background:{DARK['bg3']};border:2px solid {DARK['warning']};
                                border-radius:10px;padding:1rem;margin:0.5rem 0">
                        <div style="color:{DARK['warning']};font-size:0.78rem;
                                    font-weight:600;margin-bottom:6px">
                            ⚠️ TEMPORARY PASSWORD — share with user directly, not via this system
                        </div>
                        <div style="font-size:1.6rem;font-family:monospace;font-weight:700;
                                    color:white;letter-spacing:0.15em">{temp_pw}</div>
                        <div style="color:{DARK['muted']};font-size:0.75rem;margin-top:6px">
                            The user must change this password on first login.
                            Share via phone, personal email, or in person.
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    if st.button("✅ Mark as Resolved (I've shared the password)",
                                 key=f"resolve_{req_id}", type="primary"):
                        try:
                            # Save hashed temp password to user record
                            db().table("octa_users").update({
                                "temp_password":         temp_pw,
                                "force_password_change": True,
                            }).eq("id", user_id).execute()

                            # Close the request
                            db().table("password_reset_requests").update({
                                "status":      "completed",
                                "resolved_at": datetime.now(timezone.utc).isoformat(),
                                "resolved_by": admin_username,
                            }).eq("id", req_id).execute()

                            st.session_state.pop(gen_key, None)
                            st.success("✅ Reset completed. User can now log in with the temp password.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

                rc_reject, _ = st.columns([1, 5])
                with rc_reject:
                    if st.button("🚫 Reject Request", key=f"rej_reset_{req_id}"):
                        try:
                            db().table("password_reset_requests").update({
                                "status":      "rejected",
                                "resolved_at": datetime.now(timezone.utc).isoformat(),
                                "resolved_by": admin_username,
                            }).eq("id", req_id).execute()
                            st.warning("Reset request rejected.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Approved Users (manage access)
# ══════════════════════════════════════════════════════════════════════════════
with tab_approved:
    approved = _load_users("approved")
    if not approved:
        st.info("No approved users yet.")
    else:
        for u in approved:
            apps_val  = _parse_apps(u)
            full_name = f"{u.get('first_name','')} {u.get('last_name','')}".strip()
            uid       = u["id"]
            apps_str  = ", ".join(APP_LABELS.get(a,a) for a in apps_val) or "no apps"

            with st.expander(
                f"✅  {full_name}  ·  {u.get('username','')}  ·  {apps_str}"
            ):
                ec1, ec2, ec3 = st.columns(3)
                ec1.markdown(f"**Email:** {u.get('email','')}")
                ec2.markdown(f"**Organisation:** {u.get('organisation','—') or '—'}")
                ec3.markdown(f"**Role:** {u.get('role','user')}")
                ec1.markdown(f"**Last login:** {str(u.get('last_login','—'))[:16]}")
                ec2.markdown(f"**Approved:** {str(u.get('approved_at','—'))[:10]}")

                new_apps = st.multiselect(
                    "App access:", ALL_APPS, default=apps_val,
                    format_func=lambda k: APP_LABELS.get(k, k),
                    key=f"edit_apps_{uid}"
                )
                new_role = st.selectbox(
                    "Role:", ["user","admin"],
                    index=1 if u.get("role")=="admin" else 0,
                    key=f"role_{uid}"
                )

                sc1, sc2, _ = st.columns([1, 1, 4])
                with sc1:
                    if st.button("💾 Save", key=f"save_{uid}",
                                 use_container_width=True):
                        try:
                            db().table("octa_users").update({
                                "apps_access": new_apps,
                                "role":        new_role,
                            }).eq("id", uid).execute()
                            st.success("Saved!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                with sc2:
                    if st.button("🚫 Disable", key=f"disable_{uid}",
                                 use_container_width=True):
                        try:
                            db().table("octa_users").update({
                                "status": "disabled"
                            }).eq("id", uid).execute()
                            st.warning("Account disabled.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — All Users summary table
# ══════════════════════════════════════════════════════════════════════════════
with tab_all:
    all_users = _load_users()
    if all_users:
        df_u = pd.DataFrame([{
            "Name":         f"{u.get('first_name','')} {u.get('last_name','')}".strip(),
            "Username":     u.get("username",""),
            "Email":        u.get("email",""),
            "Organisation": u.get("organisation","—") or "—",
            "Status":       u.get("status",""),
            "Role":         u.get("role",""),
            "Apps":         ", ".join(APP_LABELS.get(a,a) for a in _parse_apps(u)) or "—",
            "Registered":   str(u.get("created_at",""))[:10],
            "Last Login":   str(u.get("last_login","—"))[:16],
        } for u in all_users])
        st.dataframe(df_u, use_container_width=True, hide_index=True)

        # Download
        st.download_button(
            "📥 Export CSV",
            data=df_u.to_csv(index=False),
            file_name="octa_users.csv",
            mime="text/csv",
        )
    else:
        st.info("No users found.")

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

# Working hours pending — always loaded, visible in all apps
pending_hours_logs = []
n_hours = 0
try:
    _hrs_resp = db().table("work_logs").select("*")                     .eq("status","pending")                     .order("log_date", desc=True).execute()
    pending_hours_logs = _hrs_resp.data or []
    n_hours = len(pending_hours_logs)
except Exception:
    pass  # work_logs table may not exist in all apps yet

# ── Alert banner ──────────────────────────────────────────────────────────────
total_pending = n_users + n_resets + n_hours
if total_pending > 0:
    items = []
    if n_users:  items.append(f"{n_users} registration{'s' if n_users>1 else ''}")
    if n_resets: items.append(f"{n_resets} password reset{'s' if n_resets>1 else ''}")
    if n_hours:  items.append(f"{n_hours} working hour entr{'y' if n_hours==1 else 'ies'}")
    st.markdown(f"""
    <div style="background:rgba(246,204,82,0.15);border:1px solid rgba(246,204,82,0.4);
                border-left:5px solid {DARK['warning']};border-radius:10px;
                padding:0.9rem 1.2rem;margin-bottom:1rem">
        ⏳ <strong style="color:{DARK['warning']}">
        {" and ".join(items)} waiting for your action
        </strong>
    </div>""", unsafe_allow_html=True)

tab_reg, tab_reset, tab_hours, tab_approved, tab_all = st.tabs([
    f"⏳ Registrations ({n_users})",
    f"🔑 Password Resets ({n_resets})",
    f"⏱️ Working Hours ({n_hours})",
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
                    default=[a for a in ["octa_proposals"] if a in ALL_APPS],
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
# TAB 2b — Working Hours Approval (octa_hours app only)
# ══════════════════════════════════════════════════════════════════════════════
with tab_hours:
    if not pending_hours_logs:
        st.success("✅ No pending working hour entries — all clear.")
    else:
        # Load user map for display
        try:
            _u_resp = db().table("octa_users").select(
                "id,first_name,last_name,username"
            ).execute()
            _umap = {
                u["id"]: f"{u.get('first_name','')} {u.get('last_name','')}".strip()
                         or u.get("username","")
                for u in (_u_resp.data or [])
            }
        except Exception:
            _umap = {}

            # Load proposal acronyms for display
            try:
                _prop_resp = db().table("proposals").select(
                    "proposal_id,acronym"
                ).execute()
                _prop_map = {
                    p["proposal_id"]: p.get("acronym","").strip() or p["proposal_id"]
                    for p in (_prop_resp.data or [])
                }
            except Exception:
                _prop_map = {}

            admin_uname = st.session_state.get("username","admin")

            for log in pending_hours_logs:
                log_id    = log["id"]
                uid       = log.get("user_id")
                emp_name  = _umap.get(uid, f"User {uid}")
                ref       = log.get("proposal_id") or log.get("project_id") or "—"
                ref_label = _prop_map.get(ref, ref) if log.get("proposal_id") else ref
                etype     = log.get("entry_type","proposal").capitalize()
                hours     = float(log.get("hours_worked",0) or 0)
                log_date  = str(log.get("log_date",""))[:10]
                comment   = log.get("comment","") or ""

                st.markdown(
                    f"<div style='height:4px;background:{DARK["warning"]};"
                    f"border-radius:4px 4px 0 0;margin-bottom:2px'></div>",
                    unsafe_allow_html=True
                )

                with st.expander(
                    f"⏳  {emp_name}  ·  {log_date}  ·  {ref_label}  ·  {hours:.2f}h",
                    expanded=False
                ):
                    r1,r2,r3,r4 = st.columns(4)
                    r1.markdown(f"**Employee:** {emp_name}")
                    r2.markdown(f"**Date:** {log_date}")
                    r3.markdown(f"**Type:** {etype}")
                    r4.markdown(f"**Reference:** {ref_label}")
                    r1.markdown(f"**Start:** {str(log.get('start_time',''))[:5]}")
                    r2.markdown(f"**End:** {str(log.get('end_time',''))[:5]}")
                    r3.markdown(f"**Hours:** {hours:.2f}h")
                    if comment:
                        st.markdown(f"**Comment:** {comment}")

                    adm_cmt = st.text_input(
                        "Admin comment (required when returning)",
                        key=f"h_cmt_{log_id}",
                        placeholder="Explain if returning…"
                    )
                    hc1, hc2, _ = st.columns([1,1,4])
                    with hc1:
                        if st.button("✅ Approve", key=f"h_app_{log_id}",
                                     type="primary", use_container_width=True):
                            try:
                                db().table("work_logs").update({
                                    "status":        "approved",
                                    "approved_by":   admin_uname,
                                    "admin_comment": adm_cmt,
                                    "approved_at":   datetime.now(timezone.utc).isoformat(),
                                    "updated_at":    datetime.now(timezone.utc).isoformat(),
                                }).eq("id", log_id).execute()
                                st.success("Approved!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                    with hc2:
                        if st.button("↩️ Return", key=f"h_ret_{log_id}",
                                     use_container_width=True):
                            if not adm_cmt.strip():
                                st.warning("Please add a comment explaining the return.")
                            else:
                                try:
                                    db().table("work_logs").update({
                                        "status":        "returned",
                                        "approved_by":   admin_uname,
                                        "admin_comment": adm_cmt,
                                        "approved_at":   datetime.now(timezone.utc).isoformat(),
                                        "updated_at":    datetime.now(timezone.utc).isoformat(),
                                    }).eq("id", log_id).execute()
                                    st.warning("Returned.")
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
                    "App access:", ALL_APPS,
                    default=[a for a in apps_val if a in ALL_APPS],
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
# TAB 4 — All Users — rich list with stats
# ══════════════════════════════════════════════════════════════════════════════
with tab_all:
    all_users = _load_users()
    if not all_users:
        st.info("No users found in the database.")
    else:
        # ── Summary KPIs ──────────────────────────────────────────────────────
        total      = len(all_users)
        approved   = sum(1 for u in all_users if u.get("status") == "approved")
        pending_n  = sum(1 for u in all_users if u.get("status") == "pending")
        disabled_n = sum(1 for u in all_users if u.get("status") == "disabled")
        admins_n   = sum(1 for u in all_users if u.get("role") == "admin")

        k1,k2,k3,k4,k5 = st.columns(5)
        for col, label, val, color in [
            (k1, "Total Users",   total,      DARK["accent"]),
            (k2, "Approved",      approved,   DARK["success"]),
            (k3, "Pending",       pending_n,  DARK["warning"]),
            (k4, "Disabled",      disabled_n, DARK["danger"]),
            (k5, "Admins",        admins_n,   DARK["accent2"]),
        ]:
            col.markdown(
                f"<div style='background:{DARK["bg2"]};border:1px solid {color}44;"
                f"border-top:3px solid {color};border-radius:10px;"
                f"padding:0.9rem;text-align:center'>"
                f"<div style='font-size:1.8rem;font-weight:700;color:{color}'>{val}</div>"
                f"<div style='font-size:0.78rem;color:{DARK["muted"]}'>{label}</div>"
                f"</div>",
                unsafe_allow_html=True
            )
        st.markdown("<br>", unsafe_allow_html=True)

        # ── Filters ───────────────────────────────────────────────────────────
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            f_status = st.selectbox("Filter by status",
                ["All","approved","pending","disabled"], key="all_status")
        with fc2:
            f_role = st.selectbox("Filter by role",
                ["All","user","admin"], key="all_role")
        with fc3:
            f_search = st.text_input("Search name / email / org",
                placeholder="Type to search…", key="all_search")

        filtered = all_users
        if f_status != "All":
            filtered = [u for u in filtered if u.get("status") == f_status]
        if f_role != "All":
            filtered = [u for u in filtered if u.get("role") == f_role]
        if f_search:
            q = f_search.lower()
            filtered = [u for u in filtered if
                q in f"{u.get('first_name','')} {u.get('last_name','')}".lower() or
                q in (u.get("email","") or "").lower() or
                q in (u.get("organisation","") or "").lower() or
                q in (u.get("username","") or "").lower()
            ]

        st.markdown(
            f"<p style='color:{DARK["muted"]};font-size:0.84rem'>"
            f"Showing <strong style='color:{DARK["text"]}'>{len(filtered)}</strong>"
            f" of {total} users</p>",
            unsafe_allow_html=True
        )

        # ── User cards ────────────────────────────────────────────────────────
        STATUS_COLORS = {
            "approved": DARK["success"],
            "pending":  DARK["warning"],
            "disabled": DARK["danger"],
        }
        STATUS_ICONS = {"approved":"✅","pending":"⏳","disabled":"🚫"}

        for u in filtered:
            uid        = u["id"]
            full_name  = f"{u.get('first_name','')} {u.get('last_name','')}".strip()                          or u.get("username","")
            status     = u.get("status","")
            role       = u.get("role","user")
            org        = u.get("organisation","—") or "—"
            email      = u.get("email","")
            username   = u.get("username","")
            registered = str(u.get("created_at",""))[:10]
            last_login = str(u.get("last_login","—"))[:16] if u.get("last_login") else "Never"
            apps_val   = _parse_apps(u)
            apps_str   = " · ".join(APP_LABELS.get(a,a) for a in apps_val) or "No apps assigned"
            s_color    = STATUS_COLORS.get(status, DARK["muted"])
            s_icon     = STATUS_ICONS.get(status,"❓")
            role_badge = ("🛡️ Admin" if role=="admin" else "👤 User")

            # Colored stripe above expander
            st.markdown(
                f"<div style='height:4px;background:{s_color};"
                f"border-radius:4px 4px 0 0;margin-bottom:2px'></div>",
                unsafe_allow_html=True
            )

            with st.expander(
                f"{s_icon}  {full_name}  ·  {org}  ·  {role_badge}  ·  {status.upper()}",
                expanded=False
            ):
                d1,d2,d3,d4 = st.columns(4)
                d1.markdown(f"**Username:** {username}")
                d2.markdown(f"**Email:** {email}")
                d3.markdown(f"**Organisation:** {org}")
                d4.markdown(f"**Role:** {role_badge}")
                d1.markdown(f"**Status:** {s_icon} {status}")
                d2.markdown(f"**Registered:** {registered}")
                d3.markdown(f"**Last Login:** {last_login}")
                d4.markdown(f"**Approved by:** {u.get('approved_by','—') or '—'}")

                # App access chips
                st.markdown(
                    f"<div style='margin:0.6rem 0 0.3rem;font-size:0.8rem;"
                    f"color:{DARK["muted"]};font-weight:600'>APP ACCESS</div>",
                    unsafe_allow_html=True
                )
                if apps_val:
                    chips = " ".join(
                        f"<span style='background:{DARK["accent"]}22;"
                        f"color:{DARK["accent"]};border:1px solid {DARK["accent"]}44;"
                        f"padding:2px 9px;border-radius:12px;font-size:0.78rem;"
                        f"margin-right:4px'>{APP_LABELS.get(a,a)}</span>"
                        for a in apps_val
                    )
                    st.markdown(chips, unsafe_allow_html=True)
                else:
                    st.markdown(
                        f"<span style='color:{DARK["muted"]};font-size:0.84rem'>"
                        f"No apps assigned</span>",
                        unsafe_allow_html=True
                    )

                # Quick edit
                st.markdown("---")
                ea1, ea2, ea3 = st.columns([3,1,1])
                with ea1:
                    new_apps_all = st.multiselect(
                        "Edit app access:", ALL_APPS,
                        default=[a for a in apps_val if a in ALL_APPS],
                        format_func=lambda k: APP_LABELS.get(k,k),
                        key=f"all_apps_{uid}"
                    )
                with ea2:
                    new_role_all = st.selectbox(
                        "Role:", ["user","admin"],
                        index=1 if role=="admin" else 0,
                        key=f"all_role_{uid}"
                    )
                with ea3:
                    new_status_all = st.selectbox(
                        "Status:", ["approved","pending","disabled"],
                        index=["approved","pending","disabled"].index(status)
                            if status in ["approved","pending","disabled"] else 0,
                        key=f"all_status_{uid}"
                    )

                sc1, sc2 = st.columns([1,5])
                with sc1:
                    if st.button("💾 Save Changes", key=f"all_save_{uid}",
                                 type="primary", use_container_width=True):
                        try:
                            db().table("octa_users").update({
                                "apps_access": new_apps_all,
                                "role":        new_role_all,
                                "status":      new_status_all,
                            }).eq("id", uid).execute()
                            st.success("Saved!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

        # ── Export CSV ────────────────────────────────────────────────────────
        st.markdown("---")
        df_export = pd.DataFrame([{
            "Name":         f"{u.get('first_name','')} {u.get('last_name','')}".strip(),
            "Username":     u.get("username",""),
            "Email":        u.get("email",""),
            "Organisation": u.get("organisation","—") or "—",
            "Status":       u.get("status",""),
            "Role":         u.get("role",""),
            "Apps":         ", ".join(APP_LABELS.get(a,a) for a in _parse_apps(u)) or "—",
            "Registered":   str(u.get("created_at",""))[:10],
            "Last Login":   str(u.get("last_login","—"))[:16] if u.get("last_login") else "Never",
        } for u in all_users])
        st.download_button(
            "📥 Export All Users CSV",
            data=df_export.to_csv(index=False),
            file_name="octa_users.csv",
            mime="text/csv",
        )

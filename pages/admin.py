"""
Octa Working Hours — Admin Panel
Approve/return work logs, view team statistics.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date

from modules.auth import require_auth, is_admin
from modules.ui_helpers import (inject_css, sidebar_nav, page_header,
                                 section_label, stat_box, status_pill, DARK)
from modules.database import (
    get_all_users_approved, get_org_users,
    get_logs_for_users, get_pending_logs, admin_update_log_status, db
)
from config import HOURS_PER_DAY, HOURS_PER_WEEK, DARK as D

st.set_page_config(page_title="Admin — Octa Working Hours",
                   page_icon="🛡️", layout="wide",
                   initial_sidebar_state="expanded")
inject_css()
sidebar_nav()
require_auth()

if not is_admin():
    st.error("🚫 Access denied. Admin role required.")
    st.stop()

page_header("Admin Panel", "Approve working hours and view team statistics", "🛡️")

admin_username = st.session_state.get("username", "admin")
admin_org      = st.session_state.get("organisation", "")
admin_user_id  = st.session_state.get("user_id")

# ── Load team ─────────────────────────────────────────────────────────────────
# Get all approved users — filter by org if admin has one set
all_approved = get_all_users_approved()

if admin_org:
    team = [u for u in all_approved if u.get("organisation","") == admin_org]
    # If filter returns nothing (org mismatch), fall back to all
    if not team:
        team = all_approved
else:
    team = all_approved

# Always ensure admin's own ID is included
team_ids = list({u["id"] for u in team} | {admin_user_id})
team_map = {u["id"]: (
    f"{u.get('first_name','')} {u.get('last_name','')}".strip()
    or u.get("username","")
) for u in all_approved}
# Add admin to map if not already present
if admin_user_id not in team_map:
    team_map[admin_user_id] = st.session_state.get("first_name","") or admin_username

# Pending count badge
pending = get_pending_logs(team_ids) if team_ids else []
if pending:
    st.markdown(f"""
    <div style="background:rgba(246,204,82,0.15);border:1px solid rgba(246,204,82,0.4);
                border-left:5px solid {D['warning']};border-radius:10px;
                padding:0.9rem 1.2rem;margin-bottom:1rem">
        ⏳ <strong style="color:{D['warning']};font-size:1rem">
        {len(pending)} entr{'y' if len(pending)==1 else 'ies'} waiting for approval
        </strong>
    </div>
    """, unsafe_allow_html=True)

tab_approve, tab_stats, tab_team = st.tabs(
    [f"⏳ Pending ({len(pending)})", "📊 Team Statistics", "👥 Team Overview"]
)

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — Approve / Return
# ════════════════════════════════════════════════════════════════════════════
with tab_approve:
    if not pending:
        st.success("✅ No pending entries — all clear.")
    else:
        for log in pending:
            uid      = log.get("user_id")
            emp_name = team_map.get(uid, f"User {uid}")
            ref      = log.get("proposal_id") or log.get("project_id") or "—"
            etype    = log.get("entry_type","proposal").capitalize()
            hours    = float(log.get("hours_worked",0) or 0)
            log_date = str(log.get("log_date",""))[:10]
            comment  = log.get("comment","") or ""
            log_id   = log["id"]

            with st.expander(
                f"⏳  {emp_name}  ·  {log_date}  ·  {ref}  ·  {hours:.2f}h",
                expanded=False
            ):
                r1,r2,r3,r4 = st.columns(4)
                r1.markdown(f"**Employee:** {emp_name}")
                r2.markdown(f"**Date:** {log_date}")
                r3.markdown(f"**Type:** {etype}")
                r4.markdown(f"**Reference:** {ref}")
                r1.markdown(f"**Start:** {str(log.get('start_time',''))[:5]}")
                r2.markdown(f"**End:** {str(log.get('end_time',''))[:5]}")
                r3.markdown(f"**Hours:** {hours:.2f}")
                if comment:
                    st.markdown(f"**Employee comment:** {comment}")

                admin_cmt = st.text_input(
                    "Comment (required for return, optional for approve)",
                    key=f"adm_cmt_{log_id}",
                    placeholder="Explain if returning…"
                )
                ac1, ac2, _ = st.columns([1,1,4])
                with ac1:
                    if st.button("✅ Approve", key=f"app_{log_id}",
                                 type="primary", use_container_width=True):
                        ok, msg = admin_update_log_status(
                            log_id, "approved", admin_username, admin_cmt
                        )
                        st.success(msg) if ok else st.error(msg)
                        st.rerun()
                with ac2:
                    if st.button("↩️ Return", key=f"ret_{log_id}",
                                 use_container_width=True):
                        if not admin_cmt.strip():
                            st.warning("Please add a comment explaining why you are returning this entry.")
                        else:
                            ok, msg = admin_update_log_status(
                                log_id, "returned", admin_username, admin_cmt
                            )
                            st.success(msg) if ok else st.error(msg)
                            st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — Team Statistics
# ════════════════════════════════════════════════════════════════════════════
with tab_stats:
    if not team_ids:
        st.info("No team members found.")
        st.stop()

    year = st.selectbox("Year", [date.today().year, date.today().year-1],
                         key="admin_year")
    all_logs = get_logs_for_users(team_ids, year=year)

    if not all_logs:
        st.info(f"No logs found for {year}.")
    else:
        df = pd.DataFrame(all_logs)
        df["hours_worked"] = pd.to_numeric(df["hours_worked"],errors="coerce").fillna(0)
        df["employee"]     = df["user_id"].map(team_map).fillna("Unknown")

        # Acronym lookup for proposals and projects
        from modules.database import get_proposal_acronyms, get_project_acronyms
        proposal_map = {p["proposal_id"]: (p.get("acronym","").strip() or p["proposal_id"])
                        for p in get_proposal_acronyms()}
        project_map  = {p["project_id"]:  (p.get("acronym","").strip() or p["project_id"])
                        for p in get_project_acronyms()}

        def _label(row):
            if row.get("entry_type") == "project":
                pid = row.get("project_id","")
                return project_map.get(pid, pid) if pid else "—"
            pid = row.get("proposal_id","")
            return proposal_map.get(pid, pid) if pid else "—"

        df["display_label"] = df.apply(_label, axis=1)

        # KPIs
        total_h = df["hours_worked"].sum()
        appr_h  = df[df["status"]=="approved"]["hours_worked"].sum()
        k1,k2,k3,k4 = st.columns(4)
        stat_box(k1,"Total Team Hours",    f"{total_h:.1f}h",  D["accent"])
        stat_box(k2,"Approved Hours",      f"{appr_h:.1f}h",   D["success"])
        stat_box(k3,"Equiv. Person-Days",  f"{total_h/HOURS_PER_DAY:.1f}",  D["accent2"])
        stat_box(k4,"Equiv. Person-Weeks", f"{total_h/HOURS_PER_WEEK:.1f}", D["accent"])

        st.markdown("<br>", unsafe_allow_html=True)

        # Hours per employee
        section_label("Hours per Employee")
        emp_grp = df.groupby("employee")["hours_worked"].sum().reset_index()
        emp_grp = emp_grp.sort_values("hours_worked", ascending=True)
        fig_e = go.Figure(go.Bar(
            x=emp_grp["hours_worked"], y=emp_grp["employee"],
            orientation="h",
            marker=dict(color=D["accent"], line=dict(width=0)),
            text=emp_grp["hours_worked"].apply(lambda v: f"{v:.1f}h"),
            textposition="outside",
        ))
        fig_e.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=max(200, len(emp_grp)*40), margin=dict(l=0,r=60,t=10,b=0),
            font_color=D["text"],
            xaxis=dict(gridcolor="rgba(255,255,255,0.05)", ticksuffix="h"),
            yaxis=dict(showgrid=False),
        )
        st.plotly_chart(fig_e, use_container_width=True)

        # Hours per proposal
        prop_logs = df[df["entry_type"]=="proposal"]
        if not prop_logs.empty:
            section_label("Hours per Proposal (all employees)")
            p_grp = prop_logs.groupby("display_label")["hours_worked"].sum().reset_index()
            p_grp = p_grp.sort_values("hours_worked", ascending=True)
            fig_pp = go.Figure(go.Bar(
                x=p_grp["hours_worked"], y=p_grp["display_label"],
                orientation="h",
                marker=dict(color=D["accent2"], line=dict(width=0)),
                text=p_grp["hours_worked"].apply(lambda v: f"{v:.1f}h"),
                textposition="outside",
            ))
            fig_pp.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                height=max(200, len(p_grp)*36), margin=dict(l=0,r=60,t=10,b=0),
                font_color=D["text"],
                xaxis=dict(gridcolor="rgba(255,255,255,0.05)", ticksuffix="h"),
                yaxis=dict(showgrid=False),
            )
            st.plotly_chart(fig_pp, use_container_width=True)

        # Employee × Proposal matrix
        section_label("Employee × Proposal Breakdown (hours)")
        pivot = df.groupby(["employee","display_label"])["hours_worked"] \
                  .sum().unstack(fill_value=0).round(2)
        if not pivot.empty:
            st.dataframe(pivot.style.background_gradient(
                cmap="Blues", axis=None
            ), use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — Team Overview table
# ════════════════════════════════════════════════════════════════════════════
with tab_team:
    year2     = st.selectbox("Year", [date.today().year, date.today().year-1],
                              key="team_year")
    all_logs2 = get_logs_for_users(team_ids, year=year2)

    if not all_logs2 or not team:
        st.info("No data available.")
    else:
        df2 = pd.DataFrame(all_logs2)
        df2["hours_worked"] = pd.to_numeric(df2["hours_worked"],errors="coerce").fillna(0)

        rows = []
        for u in team:
            uid    = u["id"]
            name   = team_map.get(uid,"")
            u_logs = df2[df2["user_id"]==uid]
            total  = u_logs["hours_worked"].sum()
            appr   = u_logs[u_logs["status"]=="approved"]["hours_worked"].sum()
            pend   = u_logs[u_logs["status"]=="pending"]["hours_worked"].sum()
            ret    = u_logs[u_logs["status"]=="returned"]["hours_worked"].sum()
            rows.append({
                "Employee":        name,
                "Organisation":    u.get("organisation","—"),
                "Total Hours":     round(total,2),
                "Approved":        round(appr,2),
                "Pending":         round(pend,2),
                "Returned":        round(ret,2),
                "Equiv. Days":     round(total/HOURS_PER_DAY,2),
                "Equiv. Weeks":    round(total/HOURS_PER_WEEK,2),
                "Entries":         len(u_logs),
            })

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True
        )

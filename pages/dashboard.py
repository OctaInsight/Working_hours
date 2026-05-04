"""
Octa Working Hours — User Dashboard
Personal statistics: hours per proposal/project, totals, weeks, days.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

from modules.auth import require_auth
from modules.ui_helpers import (inject_css, sidebar_nav, page_header,
                                 section_label, stat_box, DARK)
from modules.database import get_user_logs, get_proposal_acronyms, get_project_acronyms
from config import HOURS_PER_DAY, HOURS_PER_WEEK, DARK as D

st.set_page_config(page_title="My Dashboard — Octa Hours",
                   page_icon="📊", layout="wide",
                   initial_sidebar_state="expanded")
inject_css()
sidebar_nav()
require_auth()

user_id = st.session_state.user_id
uname   = st.session_state.get("first_name") or st.session_state.get("username","")
page_header(f"{uname}'s Working Hours", "Your personal time tracking summary", "📊")

# ── Year filter ───────────────────────────────────────────────────────────────
current_year = date.today().year
year = st.selectbox("Year", [current_year, current_year-1], key="dash_year")

logs = get_user_logs(user_id, year=year)

if not logs:
    st.info(f"No working hours logged for {year} yet. "
            "Go to **Add Working Hours** to start logging.")
    st.stop()

df = pd.DataFrame(logs)
df["hours_worked"] = pd.to_numeric(df["hours_worked"], errors="coerce").fillna(0)
df["log_date"]     = pd.to_datetime(df["log_date"])

# ── Build acronym lookup: proposal_id / project_id → display label ───────────
proposal_map = {
    p["proposal_id"]: (p.get("acronym","").strip() or p["proposal_id"])
    for p in get_proposal_acronyms()
}
project_map = {
    p["project_id"]: (p.get("acronym","").strip() or p["project_id"])
    for p in get_project_acronyms()
}

def _display_label(row):
    """Return acronym if available, else the ID — for both proposals and projects."""
    if row.get("entry_type") == "project":
        pid = row.get("project_id","")
        return project_map.get(pid, pid) if pid else "—"
    else:
        pid = row.get("proposal_id","")
        return proposal_map.get(pid, pid) if pid else "—"

df["display_label"] = df.apply(_display_label, axis=1)

# ── KPI strip ─────────────────────────────────────────────────────────────────
total_h    = df["hours_worked"].sum()
approved_h = df[df["status"]=="approved"]["hours_worked"].sum()
pending_h  = df[df["status"]=="pending"]["hours_worked"].sum()
returned_h = df[df["status"]=="returned"]["hours_worked"].sum()
total_days = total_h / HOURS_PER_DAY
total_wks  = total_h / HOURS_PER_WEEK
unique_days = df["log_date"].dt.date.nunique()

k1,k2,k3,k4,k5,k6 = st.columns(6)
stat_box(k1, "Total Hours",           f"{total_h:.1f}h",   D["accent"])
stat_box(k2, "Approved Hours",        f"{approved_h:.1f}h",D["success"])
stat_box(k3, "Pending Hours",         f"{pending_h:.1f}h", D["warning"])
stat_box(k4, "Equivalent Days",       f"{total_days:.1f}", D["accent2"])
stat_box(k5, "Equivalent Weeks",      f"{total_wks:.1f}",  D["accent"])
stat_box(k6, "Days with Entries",     str(unique_days),    D["muted"])

st.markdown("<br>", unsafe_allow_html=True)

# ── Hours by proposal ─────────────────────────────────────────────────────────
section_label("Hours per Proposal")
prop_df = df[df["entry_type"]=="proposal"].copy()
if not prop_df.empty:
    grp = prop_df.groupby("display_label")["hours_worked"].sum().reset_index()
    grp = grp.sort_values("hours_worked", ascending=True)
    grp["days"] = (grp["hours_worked"] / HOURS_PER_DAY).round(2)

    fig_p = go.Figure(go.Bar(
        x=grp["hours_worked"], y=grp["display_label"],
        orientation="h",
        marker=dict(color=D["accent"], line=dict(width=0)),
        text=grp["hours_worked"].apply(lambda v: f"{v:.1f}h"),
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Hours: %{x:.2f}<extra></extra>",
    ))
    fig_p.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=max(200, len(grp)*36), margin=dict(l=0,r=60,t=10,b=0),
        font_color=D["text"],
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)", ticksuffix="h"),
        yaxis=dict(showgrid=False),
    )
    st.plotly_chart(fig_p, use_container_width=True)
else:
    st.info("No proposal hours logged yet.")

# ── Hours by project ──────────────────────────────────────────────────────────
proj_df = df[df["entry_type"]=="project"].copy()
if not proj_df.empty:
    section_label("Hours per Project")
    grp2 = proj_df.groupby("display_label")["hours_worked"].sum().reset_index()
    grp2 = grp2.sort_values("hours_worked", ascending=True)
    fig_pj = go.Figure(go.Bar(
        x=grp2["hours_worked"], y=grp2["display_label"],
        orientation="h",
        marker=dict(color=D["accent2"], line=dict(width=0)),
        text=grp2["hours_worked"].apply(lambda v: f"{v:.1f}h"),
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Hours: %{x:.2f}<extra></extra>",
    ))
    fig_pj.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=max(200, len(grp2)*36), margin=dict(l=0,r=60,t=10,b=0),
        font_color=D["text"],
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)", ticksuffix="h"),
        yaxis=dict(showgrid=False),
    )
    st.plotly_chart(fig_pj, use_container_width=True)

# ── Hours per month timeline ──────────────────────────────────────────────────
section_label("Monthly Overview")
df["month"] = df["log_date"].dt.to_period("M").astype(str)
monthly     = df.groupby("month")["hours_worked"].sum().reset_index()
monthly     = monthly.sort_values("month")

fig_m = px.bar(
    monthly, x="month", y="hours_worked",
    template="plotly_dark",
    labels={"month":"Month","hours_worked":"Hours"},
    color_discrete_sequence=[D["accent"]],
)
# Add 37.5h/week reference line (monthly ≈ 37.5 * 4.33 = ~162h)
fig_m.add_hline(y=162, line_dash="dash",
                line_color=D["warning"],
                annotation_text="~Full month (162h)",
                annotation_font_color=D["warning"])
fig_m.update_layout(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    height=280, margin=dict(l=0,r=0,t=10,b=0),
    font_color=D["text"],
    xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.05)", ticksuffix="h"),
    showlegend=False,
)
fig_m.update_traces(marker_line_width=0)
st.plotly_chart(fig_m, use_container_width=True)

# ── Approval status breakdown ─────────────────────────────────────────────────
section_label("Approval Status")
status_counts = df.groupby("status")["hours_worked"].agg(
    count="count", hours="sum"
).reset_index()

s1, s2, s3 = st.columns(3)
colors = {"approved": D["success"], "pending": D["warning"], "returned": D["danger"]}
icons  = {"approved": "✅", "pending": "⏳", "returned": "↩️"}
for _, srow in status_counts.iterrows():
    st_key  = srow["status"]
    col     = {"approved":s1,"pending":s2,"returned":s3}.get(st_key, s1)
    bg      = DARK["bg2"]
    border  = colors.get(st_key, DARK["border"])
    txt_col = colors.get(st_key, DARK["text"])
    muted   = DARK["muted"]
    icon    = icons.get(st_key, "")
    hrs_val = float(srow["hours"])
    cnt_val = int(srow["count"])
    lbl     = st_key.capitalize()
    html_str = (
        f"<div style='background:{bg};border:1px solid {border}44;"
        f"border-left:4px solid {border};border-radius:10px;padding:1rem;text-align:center'>"
        f"<div style='font-size:1.5rem'>{icon}</div>"
        f"<div style='color:{txt_col};font-size:1.3rem;font-weight:700'>{hrs_val:.1f}h</div>"
        f"<div style='color:{muted};font-size:0.8rem'>{lbl} · {cnt_val} entries</div>"
        "</div>"
    )
    col.markdown(html_str, unsafe_allow_html=True)

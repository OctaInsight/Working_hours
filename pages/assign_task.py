"""
Octa Platform — Assign Task
Unified page — copy to pages/assign_task.py in every app.
No changes needed. APP_ORIGIN is auto-detected.
"""
import streamlit as st
from datetime import date, datetime, timezone

from modules.auth import require_auth
from modules.database import db
from modules.ui_helpers import inject_css, sidebar_nav, page_header, section_label, DARK

st.set_page_config(page_title="Assign Task — Octa Platform",
                   page_icon="📌", layout="wide",
                   initial_sidebar_state="expanded")
inject_css()
sidebar_nav()
require_auth()

# Detect which app is running
try:
    from modules.auth import APP_NAME as APP_ORIGIN
except Exception:
    APP_ORIGIN = "octa_platform"

user_id   = st.session_state.user_id
uname     = st.session_state.get("first_name") or st.session_state.get("username","")
is_admin  = st.session_state.get("role") == "admin"

page_header("Assign Task", "Create and assign tasks to team members", "📌")

# ── Load reference data ───────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_users():
    try:
        resp = db().table("octa_users").select(
            "id,first_name,last_name,username,organisation"
        ).eq("status","approved").order("first_name").execute()
        return resp.data or []
    except Exception:
        return []

@st.cache_data(ttl=60)
def load_proposals():
    try:
        resp = db().table("proposals").select(
            "proposal_id,acronym,proposal_title"
        ).order("proposal_id", desc=True).execute()
        return resp.data or []
    except Exception:
        return []

@st.cache_data(ttl=60)
def load_projects():
    try:
        resp = db().table("projects").select(
            "project_id,acronym,title"
        ).order("project_id").execute()
        return resp.data or []
    except Exception:
        return []

all_users  = load_users()
proposals  = load_proposals()
projects   = load_projects()

def _user_label(u):
    name = f"{u.get('first_name','')} {u.get('last_name','')}".strip() or u.get("username","")
    org  = u.get("organisation","") or ""
    return f"{name} — {org}" if org else name

user_opts = {_user_label(u): u["id"] for u in all_users}

prop_opts = {"— None —": ""}
for p in proposals:
    acr   = p.get("acronym","").strip() or p["proposal_id"]
    title = str(p.get("proposal_title",""))[:40]
    prop_opts[f"{acr} — {title}"] = p["proposal_id"]

proj_opts = {"— None —": ""}
for p in projects:
    acr   = p.get("acronym","").strip() or p["project_id"]
    title = str(p.get("title",""))[:40]
    proj_opts[f"{acr} — {title}"] = p["project_id"]

PRIORITY_ICONS = {"low":"🔵","normal":"🟡","high":"🟠","urgent":"🔴"}

# ── Check if editing ──────────────────────────────────────────────────────────
edit_task_id = st.session_state.get("edit_task_id")
edit_row = None
if edit_task_id:
    try:
        resp = db().table("tasks").select("*").eq("id", edit_task_id).execute()
        edit_row = resp.data[0] if resp.data else None
    except Exception:
        pass

def _v(field, default=None):
    return edit_row.get(field, default) if edit_row else default

if edit_row:
    st.info(f"✏️ Editing task: **{edit_row.get('task','')}**")

# ── Form ──────────────────────────────────────────────────────────────────────
section_label("📋 Task Details")

task_text = st.text_input(
    "Task *",
    value=_v("task",""),
    placeholder="Describe the task clearly…",
    key="task_text"
)
description = st.text_area(
    "Additional description / context",
    value=_v("description",""),
    height=100,
    placeholder="Optional — add context, links, or details…",
    key="task_desc"
)

tc1, tc2 = st.columns(2)
with tc1:
    priority = st.selectbox(
        "Priority *",
        ["low","normal","high","urgent"],
        index=["low","normal","high","urgent"].index(_v("priority","normal")),
        format_func=lambda k: f"{PRIORITY_ICONS[k]} {k.capitalize()}",
        key="task_priority"
    )
with tc2:
    deadline = st.date_input(
        "Deadline",
        value=datetime.strptime(_v("deadline", date.today().isoformat())[:10],
                                 "%Y-%m-%d").date() if _v("deadline") else None,
        format="YYYY-MM-DD",
        key="task_deadline"
    )

section_label("👤 Assign To")

# Assigned to
if not user_opts:
    st.warning("No approved users found.")
    assigned_to_id = None
else:
    default_to = 0
    if edit_row and edit_row.get("assigned_to"):
        for i, uid in enumerate(user_opts.values()):
            if uid == edit_row["assigned_to"]:
                default_to = i
                break
    sel_user = st.selectbox(
        "Assign to *",
        list(user_opts.keys()),
        index=default_to,
        key="task_assign_to"
    )
    assigned_to_id = user_opts[sel_user]

assigner_note = st.text_input(
    "Note to assignee",
    value=_v("assigner_note",""),
    placeholder="Any specific instructions…",
    key="assigner_note"
)

section_label("🔗 Link to Proposal / Project (optional)")
lc1, lc2 = st.columns(2)
with lc1:
    sel_prop  = st.selectbox("Related Proposal", list(prop_opts.keys()),
                              key="task_proposal")
    prop_id   = prop_opts[sel_prop]
with lc2:
    sel_proj  = st.selectbox("Related Project", list(proj_opts.keys()),
                              key="task_project")
    proj_id   = proj_opts[sel_proj]

st.markdown("<br>", unsafe_allow_html=True)

# ── Submit ────────────────────────────────────────────────────────────────────
col_save, col_cancel, _ = st.columns([1,1,5])
with col_save:
    if st.button("📌 Assign Task" if not edit_row else "💾 Save Changes",
                 type="primary", use_container_width=True, key="btn_save_task"):
        if not task_text.strip():
            st.error("❌ Task description is required.")
        elif not assigned_to_id:
            st.error("❌ Please select a user to assign this task to.")
        else:
            data = {
                "task":          task_text.strip(),
                "description":   description.strip(),
                "priority":      priority,
                "assigned_by":   user_id,
                "assigned_to":   assigned_to_id,
                "proposal_id":   prop_id,
                "project_id":    proj_id,
                "deadline":      deadline.isoformat() if deadline else None,
                "app_origin":    APP_ORIGIN,
                "assigner_note": assigner_note.strip(),
                "status":        "pending",
                "updated_at":    datetime.now(timezone.utc).isoformat(),
            }
            try:
                if edit_row:
                    db().table("tasks").update(data) \
                        .eq("id", edit_task_id).execute()
                    st.success("✅ Task updated!")
                    st.session_state.pop("edit_task_id", None)
                else:
                    db().table("tasks").insert(data).execute()
                    st.success(
                        f"✅ Task assigned to **{sel_user.split(' —')[0]}**!"
                    )
                    st.balloons()
                # Clear cache so task lists refresh
                load_users.clear()
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error: {e}")

with col_cancel:
    if edit_row:
        if st.button("✖ Cancel", use_container_width=True, key="btn_cancel"):
            st.session_state.pop("edit_task_id",None)
            st.rerun()

# ── My recent assigned tasks ──────────────────────────────────────────────────
st.markdown("---")
section_label("📋 Tasks I Recently Assigned")

try:
    recent_resp = db().table("tasks").select("*") \
                      .eq("assigned_by", user_id) \
                      .order("created_at", desc=True).limit(10).execute()
    recent = recent_resp.data or []
except Exception:
    recent = []

if not recent:
    st.markdown(
        f"<p style='color:{DARK['muted']};font-size:0.85rem'>"
        f"You haven't assigned any tasks yet.</p>",
        unsafe_allow_html=True
    )
else:
    # Build assignee name map
    uid_map = {u["id"]: _user_label(u) for u in all_users}

    STATUS_COLORS = {
        "pending":     DARK["muted"],
        "seen":        DARK["accent"],
        "in_progress": DARK["warning"],
        "achieved":    DARK["success"],
    }
    STATUS_ICONS = {
        "pending":"⏳","seen":"👁️","in_progress":"⚙️","achieved":"✅"
    }

    for task in recent:
        tid      = task["id"]
        status   = task.get("status","pending")
        assignee = uid_map.get(task.get("assigned_to"), "Unknown")
        deadline = str(task.get("deadline","—") or "—")
        priority = task.get("priority","normal")
        s_color  = STATUS_COLORS.get(status, DARK["muted"])
        s_icon   = STATUS_ICONS.get(status,"⏳")
        p_icon   = PRIORITY_ICONS.get(priority,"🟡")

        st.markdown(
            f"<div style='background:{DARK['bg2']};border:1px solid {s_color}44;"
            f"border-left:4px solid {s_color};border-radius:8px;"
            f"padding:0.7rem 1rem;margin-bottom:0.4rem;display:flex;"
            f"align-items:center;gap:0.8rem;flex-wrap:wrap'>"
            f"<span>{p_icon}</span>"
            f"<span style='color:{s_color};font-size:0.8rem;font-weight:600'>"
            f"{s_icon} {status.replace('_',' ').upper()}</span>"
            f"<span style='color:{DARK['text']};font-weight:500;flex:1'>"
            f"{task.get('task','')[:60]}</span>"
            f"<span style='color:{DARK['muted']};font-size:0.8rem'>"
            f"→ {assignee.split(' —')[0]}</span>"
            f"<span style='color:{DARK['muted']};font-size:0.78rem'>⏰ {deadline}</span>"
            f"</div>",
            unsafe_allow_html=True
        )

        # Edit/delete for pending tasks
        if task.get("assigned_by") == user_id and status == "pending":
            ea1, ea2, _ = st.columns([1,1,6])
            with ea1:
                if st.button("✏️ Edit", key=f"edit_t_{tid}",
                             use_container_width=True):
                    st.session_state["edit_task_id"] = tid
                    st.rerun()
            with ea2:
                if st.button("🗑 Delete", key=f"del_t_{tid}",
                             use_container_width=True):
                    try:
                        db().table("tasks").delete().eq("id",tid).execute()
                        st.success("Deleted.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

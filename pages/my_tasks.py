"""
Octa Platform — My Tasks
Unified page — copy to pages/my_tasks.py in every app.
No changes needed.
Shows:
  - Tasks assigned TO the logged-in user (with action buttons)
  - Tasks assigned BY the logged-in user (progress tracking)
"""
import streamlit as st
from datetime import datetime, timezone, date

from modules.auth import require_auth
from modules.database import db
from modules.ui_helpers import inject_css, sidebar_nav, page_header, section_label, DARK

st.set_page_config(page_title="My Tasks — Octa Platform",
                   page_icon="✅", layout="wide",
                   initial_sidebar_state="expanded")
inject_css()
sidebar_nav()
require_auth()

user_id = st.session_state.user_id
uname   = st.session_state.get("first_name") or st.session_state.get("username","")
page_header(f"{uname}'s Tasks", "Tasks assigned to you and tasks you assigned to others", "✅")

# ── Helpers ───────────────────────────────────────────────────────────────────
PRIORITY_ICONS = {"low":"🔵","normal":"🟡","high":"🟠","urgent":"🔴"}
PRIORITY_COLORS = {
    "low":    DARK["muted"],
    "normal": DARK["warning"],
    "high":   DARK["accent2"],
    "urgent": DARK["danger"],
}
STATUS_FLOW = ["pending","seen","in_progress","achieved"]
STATUS_LABELS = {
    "pending":     "⏳ Pending",
    "seen":        "👁️ Seen",
    "in_progress": "⚙️ In Progress",
    "achieved":    "✅ Achieved",
}
STATUS_COLORS = {
    "pending":     DARK["muted"],
    "seen":        DARK["accent"],
    "in_progress": DARK["warning"],
    "achieved":    DARK["success"],
}
STATUS_NEXT = {
    "pending":     ("seen",        "👁️ Mark as Seen"),
    "seen":        ("in_progress", "⚙️ Start Implementation"),
    "in_progress": ("achieved",    "✅ Mark as Achieved"),
    "achieved":    (None,          None),
}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _load_user_map():
    try:
        resp = db().table("octa_users").select(
            "id,first_name,last_name,username"
        ).execute()
        return {
            u["id"]: f"{u.get('first_name','')} {u.get('last_name','')}".strip()
                     or u.get("username","")
            for u in (resp.data or [])
        }
    except Exception:
        return {}


def _load_proposal_map():
    try:
        resp = db().table("proposals").select("proposal_id,acronym").execute()
        return {p["proposal_id"]: p.get("acronym","").strip() or p["proposal_id"]
                for p in (resp.data or [])}
    except Exception:
        return {}


def _load_project_map():
    try:
        resp = db().table("projects").select("project_id,acronym").execute()
        return {p["project_id"]: p.get("acronym","").strip() or p["project_id"]
                for p in (resp.data or [])}
    except Exception:
        return {}


def _ref_label(task, prop_map, proj_map):
    if task.get("proposal_id"):
        return "📋 " + prop_map.get(task["proposal_id"], task["proposal_id"])
    if task.get("project_id"):
        return "🏗️ " + proj_map.get(task["project_id"], task["project_id"])
    return "—"


def _days_left(deadline_str):
    if not deadline_str or deadline_str == "—":
        return None
    try:
        dl = datetime.strptime(str(deadline_str)[:10], "%Y-%m-%d").date()
        return (dl - date.today()).days
    except Exception:
        return None


def _deadline_badge(deadline_str):
    days = _days_left(deadline_str)
    if days is None:
        muted_col = DARK["muted"]; return f"<span style='color:{muted_col}'>No deadline</span>"
    color = (DARK["danger"]   if days < 0  else
             DARK["danger"]   if days < 3  else
             DARK["warning"]  if days < 7  else
             DARK["success"])
    label = ("OVERDUE" if days < 0 else
             f"{days}d left" if days < 30 else
             str(deadline_str)[:10])
    return (f"<span style='background:{color}22;color:{color};"
            f"border:1px solid {color}55;padding:2px 8px;"
            f"border-radius:10px;font-size:0.75rem;font-weight:600'>"
            f"⏰ {label}</span>")


def _update_task_status(task_id, new_status, note=""):
    ts_field = {
        "seen":        "seen_at",
        "in_progress": "started_at",
        "achieved":    "achieved_at",
    }.get(new_status)

    update = {
        "status":        new_status,
        "updated_at":    _now(),
    }
    if ts_field:
        update[ts_field] = _now()
    if note:
        update["assignee_note"] = note

    try:
        db().table("tasks").update(update).eq("id", task_id).execute()
        return True, "Updated!"
    except Exception as e:
        return False, str(e)


# ── Load data ─────────────────────────────────────────────────────────────────
umap      = _load_user_map()
prop_map  = _load_proposal_map()
proj_map  = _load_project_map()

try:
    my_tasks_resp = db().table("tasks").select("*") \
                        .eq("assigned_to", user_id) \
                        .order("deadline", desc=False).execute()
    my_tasks = my_tasks_resp.data or []
except Exception:
    my_tasks = []

try:
    assigned_resp = db().table("tasks").select("*") \
                        .eq("assigned_by", user_id) \
                        .order("created_at", desc=True).execute()
    assigned_by_me = assigned_resp.data or []
except Exception:
    assigned_by_me = []

# ── KPI strip ─────────────────────────────────────────────────────────────────
n_pending  = sum(1 for t in my_tasks if t.get("status")=="pending")
n_progress = sum(1 for t in my_tasks if t.get("status") in ("seen","in_progress"))
n_done     = sum(1 for t in my_tasks if t.get("status")=="achieved")
n_urgent   = sum(1 for t in my_tasks if t.get("priority")=="urgent"
                 and t.get("status")!="achieved")
overdue    = sum(1 for t in my_tasks
                 if (_days_left(t.get("deadline")) or 1) < 0
                 and t.get("status") != "achieved")

k1,k2,k3,k4,k5 = st.columns(5)
for col,label,val,color in [
    (k1,"Pending",     n_pending,  DARK["muted"]),
    (k2,"In Progress", n_progress, DARK["warning"]),
    (k3,"Achieved",    n_done,     DARK["success"]),
    (k4,"Urgent",      n_urgent,   DARK["danger"]),
    (k5,"Overdue",     overdue,    DARK["danger"]),
]:
    bg2=DARK["bg2"]; muted=DARK["muted"]
    col.markdown(
        f"<div style='background:{bg2};border-top:3px solid {color};"
        f"border:1px solid {color}44;border-radius:10px;"
        f"padding:0.9rem;text-align:center'>"
        f"<div style='font-size:1.8rem;font-weight:700;color:{color}'>{val}</div>"
        f"<div style='font-size:0.78rem;color:{muted}'>{label}</div></div>",
        unsafe_allow_html=True
    )

st.markdown("<br>", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_mine, tab_assigned = st.tabs([
    f"📥 Tasks Assigned to Me ({len(my_tasks)})",
    f"📤 Tasks I Assigned ({len(assigned_by_me)})",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Tasks assigned TO me
# ══════════════════════════════════════════════════════════════════════════════
with tab_mine:
    # Filter bar
    fc1,fc2,fc3 = st.columns(3)
    with fc1:
        f_status = st.selectbox(
            "Filter by status",
            ["All","pending","seen","in_progress","achieved"],
            format_func=lambda k: STATUS_LABELS.get(k,k.capitalize()) if k!="All" else "All",
            key="mine_status"
        )
    with fc2:
        f_priority = st.selectbox(
            "Filter by priority",
            ["All","urgent","high","normal","low"],
            format_func=lambda k: f"{PRIORITY_ICONS.get(k,'')} {k.capitalize()}" if k!="All" else "All",
            key="mine_priority"
        )
    with fc3:
        f_overdue = st.checkbox("Show overdue only", key="mine_overdue")

    filtered = my_tasks
    if f_status  != "All":  filtered = [t for t in filtered if t.get("status")==f_status]
    if f_priority!= "All":  filtered = [t for t in filtered if t.get("priority")==f_priority]
    if f_overdue:            filtered = [t for t in filtered
                                         if (_days_left(t.get("deadline")) or 1) < 0
                                         and t.get("status")!="achieved"]

    if not filtered:
        st.info("No tasks match your filter." if my_tasks else
                "🎉 No tasks assigned to you yet.")
    else:
        for task in filtered:
            tid       = task["id"]
            status    = task.get("status","pending")
            priority  = task.get("priority","normal")
            deadline  = str(task.get("deadline","") or "")
            from_user = umap.get(task.get("assigned_by"), "Unknown")
            ref       = _ref_label(task, prop_map, proj_map)
            app_orig  = task.get("app_origin","") or ""
            s_color   = STATUS_COLORS.get(status, DARK["muted"])
            p_color   = PRIORITY_COLORS.get(priority, DARK["muted"])
            p_icon    = PRIORITY_ICONS.get(priority,"🟡")
            dl_badge  = _deadline_badge(deadline)
            note      = task.get("assigner_note","") or ""
            my_note   = task.get("assignee_note","") or ""

            # Card header
            st.markdown(
                f"<div style='background:{DARK['bg2']};border:1px solid {s_color}44;"
                f"border-left:5px solid {s_color};border-radius:10px 10px 0 0;"
                f"padding:0.8rem 1.1rem;margin-top:0.6rem;margin-bottom:0'>"
                f"<div style='display:flex;align-items:center;gap:0.6rem;flex-wrap:wrap'>"
                f"<span style='color:{p_color};font-size:1rem'>{p_icon}</span>"
                f"<strong style='color:{DARK['text']};font-size:0.95rem;flex:1'>"
                f"{task.get('task','')}</strong>"
                f"<span style='background:{s_color}22;color:{s_color};font-size:0.75rem;"
                f"font-weight:600;padding:2px 8px;border-radius:10px;"
                f"border:1px solid {s_color}44'>"
                f"{STATUS_LABELS.get(status,status)}</span>"
                f"</div>"
                f"<div style='margin-top:0.4rem;display:flex;gap:1rem;flex-wrap:wrap;"
                f"font-size:0.8rem;color:{DARK["muted"]}'>"
                f"<span>From: <strong style='color:{DARK["text"]}'>{from_user}</strong></span>"
                f"<span>Ref: {ref}</span>"
                f"<span>App: {app_orig.replace('octa_','').replace('_',' ').title()}</span>"
                f"<span>{dl_badge}</span>"
                f"</div></div>",
                unsafe_allow_html=True
            )

            with st.expander("Details & Actions", expanded=(status=="pending")):
                if task.get("description"):
                    st.markdown(f"**Description:** {task['description']}")
                if note:
                    muted_c = DARK["muted"]
                    acc = DARK["accent"]
                    st.markdown(
                        f"<div style='background:rgba(0,188,212,0.08);"
                        f"border-left:3px solid {acc};border-radius:6px;"
                        f"padding:0.5rem 0.8rem;margin:0.4rem 0;font-size:0.85rem'>"
                        f"💬 <strong>Note from assigner:</strong> {note}</div>",
                        unsafe_allow_html=True
                    )

                # Timeline
                timeline = []
                if task.get("created_at"):
                    timeline.append(("📌 Assigned",   str(task["created_at"])[:16]))
                if task.get("seen_at"):
                    timeline.append(("👁️ Seen",       str(task["seen_at"])[:16]))
                if task.get("started_at"):
                    timeline.append(("⚙️ Started",    str(task["started_at"])[:16]))
                if task.get("achieved_at"):
                    timeline.append(("✅ Achieved",   str(task["achieved_at"])[:16]))
                if timeline:
                    muted_c = DARK["muted"]
                    st.markdown(
                        "<div style='display:flex;gap:1.5rem;flex-wrap:wrap;"
                        f"font-size:0.78rem;color:{muted_c};margin:0.4rem 0'>"
                        + "".join(f"<span><strong>{lbl}:</strong> {ts}</span>"
                                  for lbl,ts in timeline)
                        + "</div>",
                        unsafe_allow_html=True
                    )

                # My progress note
                my_note_val = st.text_input(
                    "Your progress note (optional)",
                    value=my_note,
                    placeholder="Add a note about your progress…",
                    key=f"my_note_{tid}"
                )

                # Action buttons
                if status != "achieved":
                    next_status, next_label = STATUS_NEXT.get(status,(None,None))
                    if next_status and next_label:
                        ac1,ac2,_ = st.columns([2,2,4])
                        with ac1:
                            if st.button(next_label, key=f"action_{tid}",
                                         type="primary", use_container_width=True):
                                ok, msg = _update_task_status(
                                    tid, next_status, my_note_val
                                )
                                if ok:
                                    st.success(f"✅ Status updated to: {next_status.replace('_',' ')}")
                                    st.rerun()
                                else:
                                    st.error(f"Error: {msg}")
                        with ac2:
                            if st.button("💾 Save Note Only", key=f"note_{tid}",
                                         use_container_width=True):
                                try:
                                    db().table("tasks").update({
                                        "assignee_note": my_note_val,
                                        "updated_at":    _now(),
                                    }).eq("id",tid).execute()
                                    st.success("Note saved.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
                else:
                    success_c = DARK["success"]
                    at = str(task.get("achieved_at",""))[:16]
                    st.markdown(
                        f"<div style='color:{success_c};font-weight:600;font-size:0.9rem'>"
                        f"✅ Task achieved at {at}</div>",
                        unsafe_allow_html=True
                    )
                    if my_note:
                        st.markdown(f"**Your note:** {my_note}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Tasks I assigned to others
# ══════════════════════════════════════════════════════════════════════════════
with tab_assigned:
    # Filter
    af1, af2 = st.columns(2)
    with af1:
        af_status = st.selectbox(
            "Filter by status",
            ["All","pending","seen","in_progress","achieved"],
            format_func=lambda k: STATUS_LABELS.get(k,k.capitalize()) if k!="All" else "All",
            key="asgn_status"
        )
    with af2:
        af_search = st.text_input("Search task", placeholder="Type to filter…",
                                   key="asgn_search")

    filtered_asgn = assigned_by_me
    if af_status != "All":
        filtered_asgn = [t for t in filtered_asgn if t.get("status")==af_status]
    if af_search:
        q = af_search.lower()
        filtered_asgn = [t for t in filtered_asgn
                         if q in (t.get("task","") or "").lower()
                         or q in (t.get("description","") or "").lower()]

    if not filtered_asgn:
        st.info("No tasks found." if assigned_by_me else
                "You haven't assigned any tasks yet.")
    else:
        for task in filtered_asgn:
            tid      = task["id"]
            status   = task.get("status","pending")
            priority = task.get("priority","normal")
            deadline = str(task.get("deadline","") or "")
            assignee = umap.get(task.get("assigned_to"), "Unknown")
            ref      = _ref_label(task, prop_map, proj_map)
            s_color  = STATUS_COLORS.get(status, DARK["muted"])
            p_icon   = PRIORITY_ICONS.get(priority,"🟡")
            dl_badge = _deadline_badge(deadline)
            my_note  = task.get("assignee_note","") or ""

            # Progress bar
            progress_pct = {
                "pending": 0, "seen": 25, "in_progress": 65, "achieved": 100
            }.get(status, 0)
            bar_color = STATUS_COLORS.get(status, DARK["muted"])

            st.markdown(
                f"<div style='background:{DARK['bg2']};border:1px solid {s_color}44;"
                f"border-left:5px solid {s_color};border-radius:10px 10px 0 0;"
                f"padding:0.8rem 1.1rem;margin-top:0.6rem;margin-bottom:0'>"
                f"<div style='display:flex;align-items:center;gap:0.6rem;flex-wrap:wrap'>"
                f"<span>{p_icon}</span>"
                f"<strong style='color:{DARK['text']};font-size:0.95rem;flex:1'>"
                f"{task.get('task','')}</strong>"
                f"<span style='background:{s_color}22;color:{s_color};font-size:0.75rem;"
                f"font-weight:600;padding:2px 8px;border-radius:10px;"
                f"border:1px solid {s_color}44'>"
                f"{STATUS_LABELS.get(status,status)}</span>"
                f"</div>"
                f"<div style='margin:0.4rem 0 0.3rem;display:flex;gap:1rem;flex-wrap:wrap;"
                f"font-size:0.8rem;color:{DARK["muted"]}'>"
                f"<span>→ <strong style='color:{DARK["text"]}'>{assignee}</strong></span>"
                f"<span>{ref}</span><span>{dl_badge}</span>"
                f"</div>"
                f"<div style='background:rgba(255,255,255,0.08);border-radius:4px;height:5px'>"
                f"<div style='background:{bar_color};border-radius:4px;height:5px;"
                f"width:{progress_pct}%'></div></div></div>",
                unsafe_allow_html=True
            )

            with st.expander("Details & Progress", expanded=False):
                d1,d2,d3 = st.columns(3)
                d1.markdown(f"**Assignee:** {assignee}")
                d2.markdown(f"**Deadline:** {deadline or '—'}")
                d3.markdown(f"**Priority:** {p_icon} {priority.capitalize()}")

                if task.get("description"):
                    st.markdown(f"**Description:** {task['description']}")

                # Progress timeline
                timeline = []
                if task.get("created_at"):
                    timeline.append(("📌 Assigned",  str(task["created_at"])[:16]))
                if task.get("seen_at"):
                    timeline.append(("👁️ Seen",      str(task["seen_at"])[:16]))
                if task.get("started_at"):
                    timeline.append(("⚙️ Started",   str(task["started_at"])[:16]))
                if task.get("achieved_at"):
                    timeline.append(("✅ Achieved",  str(task["achieved_at"])[:16]))

                if len(timeline) > 1:
                    section_label("Progress Timeline")
                    muted_c = DARK["muted"]
                    st.markdown(
                        "<div style='display:flex;gap:1.5rem;flex-wrap:wrap;"
                        f"font-size:0.8rem;color:{muted_c}'>"
                        + "".join(f"<span><strong>{lbl}:</strong> {ts}</span>"
                                  for lbl,ts in timeline)
                        + "</div>",
                        unsafe_allow_html=True
                    )

                if my_note:
                    acc = DARK["accent"]
                    st.markdown(
                        f"<div style='background:rgba(0,188,212,0.08);"
                        f"border-left:3px solid {acc};border-radius:6px;"
                        f"padding:0.5rem 0.8rem;margin-top:0.5rem;font-size:0.85rem'>"
                        f"💬 <strong>Assignee's note:</strong> {my_note}</div>",
                        unsafe_allow_html=True
                    )

                # Edit/delete (only if pending)
                if status == "pending":
                    ec1,ec2,_ = st.columns([1,1,5])
                    with ec1:
                        if st.button("✏️ Edit Task", key=f"edit_a_{tid}",
                                     use_container_width=True):
                            st.session_state["edit_task_id"] = tid
                            st.switch_page("pages/assign_task.py")
                    with ec2:
                        if st.button("🗑 Delete", key=f"del_a_{tid}",
                                     use_container_width=True):
                            try:
                                db().table("tasks").delete().eq("id",tid).execute()
                                st.success("Task deleted.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")

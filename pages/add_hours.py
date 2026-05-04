"""
Octa Working Hours — Add / Edit Working Hours Page
"""
import streamlit as st
from datetime import date, time, datetime

from modules.auth import require_auth
from modules.ui_helpers import inject_css, sidebar_nav, page_header, section_label, status_pill, DARK
from modules.database import (
    get_proposal_acronyms, get_project_acronyms,
    add_work_log, update_work_log, delete_work_log,
    get_user_logs, get_log_by_id
)

st.set_page_config(page_title="Add Hours — Octa Working Hours",
                   page_icon="➕", layout="wide",
                   initial_sidebar_state="expanded")
inject_css()
sidebar_nav()
require_auth()

user_id = st.session_state.user_id
page_header("Log Working Hours", "Record your time per proposal or project", "➕")

# ── Load reference data ───────────────────────────────────────────────────────
proposals = get_proposal_acronyms()
projects  = get_project_acronyms()

def _proposal_options() -> dict:
    """Return {display_label: proposal_id}"""
    opts = {}
    for p in proposals:
        acr   = str(p.get("acronym","")).strip()
        pid   = str(p.get("proposal_id","")).strip()
        title = str(p.get("proposal_title",""))[:40]
        label = f"{acr} — {title}" if acr else pid
        opts[label] = pid
    return opts

def _project_options() -> dict:
    opts = {}
    for p in projects:
        acr   = str(p.get("acronym","")).strip()
        pid   = str(p.get("project_id","")).strip()
        title = str(p.get("title",""))[:40]
        label = f"{acr} — {title}" if acr else pid
        opts[label] = pid
    return opts

tab_add, tab_history = st.tabs(["➕  Log Hours", "📋  My Log History"])

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — Log Hours
# ════════════════════════════════════════════════════════════════════════════
with tab_add:

    # Check if editing an existing entry
    edit_id  = st.session_state.get("edit_log_id")
    edit_row = None
    if edit_id:
        edit_row = get_log_by_id(edit_id, user_id)
        if edit_row and edit_row.get("status") == "approved":
            st.warning("⚠️ Approved entries cannot be edited.")
            st.session_state.pop("edit_log_id", None)
            edit_id = None
            edit_row = None

    if edit_row:
        st.info(f"✏️ Editing entry from {edit_row.get('log_date')} — "
                f"changes will reset status to pending.")

    def _v(field, default=None):
        return edit_row.get(field, default) if edit_row else default

    with st.form("log_form", clear_on_submit=False):

        section_label("📅 Date & Reference")
        fc1, fc2 = st.columns(2)
        with fc1:
            log_date = st.date_input(
                "Date *",
                value=datetime.strptime(_v("log_date", date.today().isoformat())[:10],
                                         "%Y-%m-%d").date(),
                format="YYYY-MM-DD"
            )
        with fc2:
            entry_type = st.radio(
                "Log type *",
                ["proposal", "project"],
                index=0 if _v("entry_type","proposal") == "proposal" else 1,
                horizontal=True,
            )

        # Proposal or project selector
        section_label("🔗 Proposal / Project")
        if entry_type == "proposal":
            prop_opts = _proposal_options()
            if not prop_opts:
                st.warning("No proposals found in the database.")
                ref_id = ""
            else:
                # Pre-select current value if editing
                current_pid = _v("proposal_id", "")
                default_idx = 0
                keys = list(prop_opts.keys())
                for i, (label, pid) in enumerate(prop_opts.items()):
                    if pid == current_pid:
                        default_idx = i
                        break
                selected = st.selectbox("Select Proposal *", keys,
                                         index=default_idx)
                ref_id = prop_opts[selected]
        else:
            proj_opts = _project_options()
            if not proj_opts:
                st.info("No projects in the database yet. Projects will be added later.")
                ref_id = ""
            else:
                current_prid = _v("project_id", "")
                default_idx  = 0
                keys         = list(proj_opts.keys())
                for i, (label, pid) in enumerate(proj_opts.items()):
                    if pid == current_prid:
                        default_idx = i
                        break
                selected = st.selectbox("Select Project *", keys, index=default_idx)
                ref_id   = proj_opts[selected]

        section_label("⏰ Working Hours")

        # Use selectboxes — st.time_input causes React errors in some Streamlit versions
        HOURS   = [f"{h:02d}" for h in range(0, 24)]
        MINUTES = ["00", "15", "30", "45"]

        def _parse_hm(v, default_h, default_m):
            """Extract (hour_str, minute_str) from a stored time string."""
            try:
                parts = str(v)[:5].split(":")
                h = f"{int(parts[0]):02d}"
                m_raw = int(parts[1])
                # Round to nearest 15
                m = f"{(m_raw // 15) * 15:02d}"
                return h, m
            except Exception:
                return f"{default_h:02d}", f"{default_m:02d}"

        s_h, s_m = _parse_hm(_v("start_time"), 9,  0)
        e_h, e_m = _parse_hm(_v("end_time"),   17, 0)

        tc1, tc2, tc3 = st.columns(3)
        with tc1:
            st.markdown("**Start time \\***")
            sc1, sc2 = st.columns(2)
            with sc1:
                sh = st.selectbox("Hour",   HOURS,   index=HOURS.index(s_h),
                                  key="start_h", label_visibility="collapsed")
            with sc2:
                sm = st.selectbox("Min",    MINUTES, index=MINUTES.index(s_m) if s_m in MINUTES else 0,
                                  key="start_m", label_visibility="collapsed")
            start_time = time(int(sh), int(sm))

        with tc2:
            st.markdown("**End time \\***")
            ec1, ec2 = st.columns(2)
            with ec1:
                eh = st.selectbox("Hour",   HOURS,   index=HOURS.index(e_h),
                                  key="end_h", label_visibility="collapsed")
            with ec2:
                em = st.selectbox("Min",    MINUTES, index=MINUTES.index(e_m) if e_m in MINUTES else 0,
                                  key="end_m", label_visibility="collapsed")
            end_time = time(int(eh), int(em))

        with tc3:
            # Live hours preview
            st.markdown("**Hours worked**")
            if end_time > start_time:
                mins = (end_time.hour*60 + end_time.minute) - \
                       (start_time.hour*60 + start_time.minute)
                hrs  = mins / 60
                accent = DARK["accent"]
                muted  = DARK["muted"]
                bg2    = DARK["bg2"]
                st.markdown(
                    f"<div style='background:{bg2};border:1px solid {accent}44;"
                    f"border-radius:8px;padding:0.7rem;text-align:center'>"
                    f"<div style='color:{muted};font-size:0.72rem'>TOTAL</div>"
                    f"<div style='color:{accent};font-size:1.8rem;font-weight:700'>"
                    f"{hrs:.2f}h</div></div>",
                    unsafe_allow_html=True
                )
            else:
                danger = DARK["danger"]
                st.markdown(
                    f"<div style='color:{danger};font-size:0.85rem'>"
                    f"⚠️ End must be after start</div>",
                    unsafe_allow_html=True
                )

        section_label("💬 Comment")
        comment = st.text_area(
            "What did you work on?",
            value=_v("comment", ""),
            height=100,
            placeholder="Brief description of the work done today…"
        )

        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button(
            "💾 Save Entry" if edit_row else "➕ Add Entry",
            type="primary", use_container_width=True
        )

    if submitted:
        if not ref_id:
            st.error("❌ Please select a proposal or project.")
        elif end_time <= start_time:
            st.error("❌ End time must be after start time.")
        else:
            if edit_row:
                ok, msg = update_work_log(
                    edit_id, user_id, log_date, entry_type,
                    ref_id, start_time, end_time, comment
                )
            else:
                ok, msg, _ = add_work_log(
                    user_id, log_date, entry_type,
                    ref_id, start_time, end_time, comment
                )

            if ok:
                st.success(f"✅ {msg}")
                st.session_state.pop("edit_log_id", None)
                st.rerun()
            else:
                st.error(f"❌ {msg}")

    # Cancel edit
    if edit_row:
        if st.button("✖ Cancel Edit", use_container_width=False):
            st.session_state.pop("edit_log_id", None)
            st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — History
# ════════════════════════════════════════════════════════════════════════════
with tab_history:
    from datetime import date as date_cls
    year_filter = st.selectbox(
        "Filter by year",
        [date_cls.today().year, date_cls.today().year - 1],
        key="hist_year"
    )

    logs = get_user_logs(user_id, year=year_filter)

    if not logs:
        st.info("No working hours logged yet for this period.")
    else:
        total_h = sum(float(l.get("hours_worked",0) or 0) for l in logs)
        st.markdown(
            f"<p style='color:{DARK['muted']};font-size:0.85rem'>"
            f"<strong style='color:{DARK['text']}'>{len(logs)}</strong> entries · "
            f"Total: <strong style='color:{DARK['accent']}'>{total_h:.2f} hours</strong>"
            f"</p>",
            unsafe_allow_html=True
        )

        for log in logs:
            log_id   = log["id"]
            ref      = log.get("proposal_id") or log.get("project_id") or "—"
            etype    = log.get("entry_type", "proposal")
            hours    = float(log.get("hours_worked",0) or 0)
            log_date = log.get("log_date","")[:10]
            status   = log.get("status","pending")
            cmt      = log.get("comment","") or ""
            adm_cmt  = log.get("admin_comment","") or ""

            status_html = status_pill(status)

            with st.expander(
                f"📅 {log_date}  ·  {ref}  ·  {hours:.2f}h  ·  "
                f"{log.get('start_time','')[:5]}–{log.get('end_time','')[:5]}"
            ):
                r1, r2, r3, r4 = st.columns(4)
                r1.markdown(f"**Date:** {log_date}")
                r2.markdown(f"**Type:** {etype.capitalize()}")
                r3.markdown(f"**Reference:** {ref}")
                r4.markdown(f"**Hours:** {hours:.2f}")
                st.markdown(f"**Status:** {status_html}", unsafe_allow_html=True)

                if cmt:
                    st.markdown(f"**Your comment:** {cmt}")
                if adm_cmt:
                    st.markdown(
                        f"<div style='background:rgba(252,129,129,0.1);"
                        f"border-left:3px solid {DARK['danger']};border-radius:6px;"
                        f"padding:0.5rem 0.8rem;margin-top:0.5rem;font-size:0.85rem'>"
                        f"<strong style='color:{DARK['danger']}'>Admin comment:</strong> {adm_cmt}"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                if status != "approved":
                    bc1, bc2, _ = st.columns([1,1,4])
                    with bc1:
                        if st.button("✏️ Edit", key=f"edit_{log_id}",
                                     use_container_width=True):
                            st.session_state["edit_log_id"] = log_id
                            st.rerun()
                    with bc2:
                        if st.button("🗑 Delete", key=f"del_{log_id}",
                                     use_container_width=True):
                            ok, msg = delete_work_log(log_id, user_id)
                            if ok:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                else:
                    st.markdown(
                        f"<span style='color:{DARK['muted']};font-size:0.8rem'>"
                        f"✅ Approved entries cannot be edited or deleted.</span>",
                        unsafe_allow_html=True
                    )

"""Octa Working Hours — Supabase database layer."""
import streamlit as st
from supabase import create_client, Client
from datetime import datetime, date, time


@st.cache_resource
def _client() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)


def db() -> Client:
    return _client()


# ── Partners (read-only, shared table) ───────────────────────────────────────

def get_all_partners() -> list:
    """Return all partners ordered by name — used for organisation dropdown."""
    try:
        resp = db().table("partners").select("full_name").order("full_name").execute()
        return resp.data or []
    except Exception:
        return []


# ── Proposals (read-only, from shared table) ──────────────────────────────────

def get_proposal_acronyms() -> list:
    """Return list of (proposal_id, acronym, title) for dropdown."""
    try:
        resp = db().table("proposals").select(
            "proposal_id,acronym,proposal_title"
        ).order("proposal_id").execute()
        return resp.data or []
    except Exception:
        return []


# ── Projects (read-only, from shared table) ───────────────────────────────────

def get_project_acronyms() -> list:
    """Return list of (project_id, acronym, title) for dropdown."""
    try:
        resp = db().table("projects").select(
            "project_id,acronym,title"
        ).order("project_id").execute()
        return resp.data or []
    except Exception:
        return []


# ── Work Logs ─────────────────────────────────────────────────────────────────

def _calc_hours(start: time, end: time) -> float:
    """Calculate decimal hours between two time objects."""
    start_mins = start.hour * 60 + start.minute
    end_mins   = end.hour   * 60 + end.minute
    diff_mins  = end_mins - start_mins
    return round(max(diff_mins / 60, 0), 2)


def add_work_log(user_id: int, log_date: date, entry_type: str,
                 ref_id: str, start_time: time, end_time: time,
                 comment: str = "") -> tuple:
    """
    Insert a new work log entry.
    ref_id = proposal_id or project_id depending on entry_type.
    Returns (ok, message, log_id|None).
    """
    if end_time <= start_time:
        return False, "End time must be after start time.", None

    hours = _calc_hours(start_time, end_time)
    if hours <= 0:
        return False, "Working hours must be greater than 0.", None

    data = {
        "user_id":      user_id,
        "log_date":     log_date.isoformat(),
        "entry_type":   entry_type,
        "proposal_id":  ref_id if entry_type == "proposal" else "",
        "project_id":   ref_id if entry_type == "project"  else "",
        "start_time":   start_time.strftime("%H:%M"),
        "end_time":     end_time.strftime("%H:%M"),
        "hours_worked": hours,
        "comment":      comment.strip(),
        "status":       "pending",
    }
    try:
        resp = db().table("work_logs").insert(data).execute()
        log_id = resp.data[0]["id"] if resp.data else None
        return True, f"Logged {hours:.2f} hours successfully.", log_id
    except Exception as e:
        return False, f"Error saving log: {e}", None


def update_work_log(log_id: int, user_id: int, log_date: date,
                    entry_type: str, ref_id: str,
                    start_time: time, end_time: time,
                    comment: str = "") -> tuple:
    """Update an existing log (only if still pending)."""
    if end_time <= start_time:
        return False, "End time must be after start time."

    hours = _calc_hours(start_time, end_time)
    try:
        db().table("work_logs").update({
            "log_date":     log_date.isoformat(),
            "entry_type":   entry_type,
            "proposal_id":  ref_id if entry_type == "proposal" else "",
            "project_id":   ref_id if entry_type == "project"  else "",
            "start_time":   start_time.strftime("%H:%M"),
            "end_time":     end_time.strftime("%H:%M"),
            "hours_worked": hours,
            "comment":      comment.strip(),
            "status":       "pending",   # reset to pending on edit
            "updated_at":   datetime.now().isoformat(),
        }).eq("id", log_id).eq("user_id", user_id).execute()
        return True, f"Updated — {hours:.2f} hours logged."
    except Exception as e:
        return False, f"Update error: {e}"


def delete_work_log(log_id: int, user_id: int) -> tuple:
    """Delete a log entry (only pending entries)."""
    try:
        db().table("work_logs").delete() \
            .eq("id", log_id).eq("user_id", user_id) \
            .eq("status", "pending").execute()
        return True, "Entry deleted."
    except Exception as e:
        return False, f"Delete error: {e}"


def get_user_logs(user_id: int, year: int = None) -> list:
    """All logs for a user, optionally filtered by year."""
    q = db().table("work_logs").select("*") \
        .eq("user_id", user_id).order("log_date", desc=True)
    if year:
        q = q.gte("log_date", f"{year}-01-01").lte("log_date", f"{year}-12-31")
    return q.execute().data or []


def get_log_by_id(log_id: int, user_id: int) -> dict | None:
    resp = db().table("work_logs").select("*") \
        .eq("id", log_id).eq("user_id", user_id).execute()
    return resp.data[0] if resp.data else None


# ── Admin queries ─────────────────────────────────────────────────────────────

def get_org_users(organisation: str) -> list:
    """All approved users in the same organisation as the admin."""
    resp = db().table("octa_users").select("id,first_name,last_name,username,email") \
        .eq("organisation", organisation).eq("status", "approved").execute()
    return resp.data or []


def get_all_users_approved() -> list:
    resp = db().table("octa_users").select(
        "id,first_name,last_name,username,email,organisation"
    ).eq("status", "approved").order("first_name").execute()
    return resp.data or []


def get_logs_for_users(user_ids: list, year: int = None) -> list:
    """Get all work logs for a list of user IDs."""
    if not user_ids:
        return []
    q = db().table("work_logs").select("*").in_("user_id", user_ids) \
        .order("log_date", desc=True)
    if year:
        q = q.gte("log_date", f"{year}-01-01").lte("log_date", f"{year}-12-31")
    return q.execute().data or []


def get_pending_logs(user_ids: list = None) -> list:
    """Pending logs — for all users or specific users."""
    q = db().table("work_logs").select("*").eq("status", "pending") \
        .order("log_date", desc=True)
    if user_ids:
        q = q.in_("user_id", user_ids)
    return q.execute().data or []


def admin_update_log_status(log_id: int, status: str,
                             admin_username: str,
                             admin_comment: str = "") -> tuple:
    """Admin approves or returns a work log."""
    if status not in ("approved", "returned"):
        return False, "Invalid status."
    try:
        update = {
            "status":        status,
            "approved_by":   admin_username,
            "admin_comment": admin_comment.strip(),
            "approved_at":   datetime.now().isoformat(),
            "updated_at":    datetime.now().isoformat(),
        }
        db().table("work_logs").update(update).eq("id", log_id).execute()
        return True, f"Log {status}."
    except Exception as e:
        return False, f"Error: {e}"

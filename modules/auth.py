"""
Octa Platform — Unified Authentication Module
Copy this file to modules/auth.py in every app.
Only change APP_NAME to match the app identifier.

Password reset is admin-assisted (secure):
  User submits a reset REQUEST → stored in DB
  Admin sees the request → generates a temp password → shares it out-of-band
  User logs in with temp password → must change it immediately
"""
import bcrypt
import streamlit as st
from datetime import datetime, timezone
from modules.database import db   # each app provides its own db() function

# ── Change this per app ───────────────────────────────────────────────────────
APP_NAME = "octa_hours"   # octa_proposals | octa_hours | octa_writer | ...


# ── Password helpers ──────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False


# ── User lookups ──────────────────────────────────────────────────────────────

def get_user_by_email(email: str) -> dict | None:
    try:
        resp = db().table("octa_users").select("*") \
                   .eq("email", email.strip().lower()).execute()
        return resp.data[0] if resp.data else None
    except Exception:
        return None


def get_user_by_username(username: str) -> dict | None:
    try:
        resp = db().table("octa_users").select("*") \
                   .eq("username", username.strip()).execute()
        return resp.data[0] if resp.data else None
    except Exception:
        return None


def get_user_by_id(uid: int) -> dict | None:
    try:
        resp = db().table("octa_users").select("*").eq("id", uid).execute()
        return resp.data[0] if resp.data else None
    except Exception:
        return None


# ── Registration ──────────────────────────────────────────────────────────────

def register_user(email: str, username: str, first_name: str,
                  last_name: str, password: str,
                  organisation: str = "") -> tuple:
    """
    Create a new pending user.
    Returns (ok: bool, message: str, user: dict | None).
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters.", None
    if "@" not in email:
        return False, "Invalid email address.", None
    if len(username.strip()) < 3:
        return False, "Username must be at least 3 characters.", None
    if get_user_by_email(email):
        return False, "This email is already registered.", None
    if get_user_by_username(username):
        return False, "This username is already taken.", None

    try:
        resp = db().table("octa_users").insert({
            "email":         email.strip().lower(),
            "username":      username.strip(),
            "first_name":    first_name.strip(),
            "last_name":     last_name.strip(),
            "password_hash": hash_password(password),
            "status":        "pending",
            "apps_access":   [],
            "role":          "user",
            "organisation":  organisation.strip(),
        }).execute()
        user = resp.data[0] if resp.data else None
        return True, "Registration submitted successfully.", user
    except Exception as e:
        return False, f"Registration failed: {e}", None


# ── Login ─────────────────────────────────────────────────────────────────────

def login_user(email: str, password: str) -> tuple:
    """
    Authenticate a user. Returns (ok: bool, message: str, user: dict | None).
    """
    user = get_user_by_email(email)
    if not user:
        return False, "No account found with this email.", None

    # Check for temp password first (admin-assisted reset)
    temp_pw = user.get("temp_password", "")
    if temp_pw and password == temp_pw:
        # Clear temp password on use
        try:
            db().table("octa_users").update({
                "temp_password": None,
                "force_password_change": True,
            }).eq("id", user["id"]).execute()
        except Exception:
            pass
        # Re-fetch updated user
        user = get_user_by_id(user["id"]) or user
        _update_last_login(user["id"])
        return True, "⚠️ Logged in with temporary password. Please change your password.", user

    status = user.get("status")
    if status == "pending":
        return False, (
            "⏳ Your account is pending admin approval. "
            "Please check back later."
        ), None
    if status == "disabled":
        return False, "🚫 Your account has been disabled. Contact your admin.", None

    if not verify_password(password, user.get("password_hash", "")):
        return False, "Incorrect password.", None

    # Check app access (admins bypass)
    if user.get("role") != "admin":
        apps = _parse_apps(user.get("apps_access"))
        if APP_NAME not in apps:
            return False, "Your account does not have access to this application.", None

    _update_last_login(user["id"])
    name = user.get("first_name") or user.get("username", "")
    return True, f"Welcome back, {name}!", user


def _update_last_login(user_id: int):  # also exported
    try:
        db().table("octa_users") \
            .update({"last_login": datetime.now(timezone.utc).isoformat()}) \
            .eq("id", user_id).execute()
    except Exception:
        pass


# ── Password change (after temp password login) ───────────────────────────────

def change_password(user_id: int, new_password: str) -> tuple:
    """User changes their own password. Returns (ok, message)."""
    if len(new_password) < 8:
        return False, "Password must be at least 8 characters."
    try:
        db().table("octa_users").update({
            "password_hash":         hash_password(new_password),
            "force_password_change": False,
            "temp_password":         None,
        }).eq("id", user_id).execute()
        return True, "Password changed successfully."
    except Exception as e:
        return False, f"Error: {e}"


# ── Password reset (admin-assisted, secure) ───────────────────────────────────

def request_password_reset(email: str) -> tuple:
    """
    User submits a reset request — NO token shown to user.
    Admin sees the request in the Admin Panel and generates a temp password.
    Returns (ok, message).
    """
    user = get_user_by_email(email)
    if not user:
        # Don't reveal whether email exists
        return True, ("Reset request submitted. If your email is registered, "
                       "an admin will contact you with a temporary password.")
    try:
        # Check for existing pending request
        existing = db().table("password_reset_requests").select("id") \
                       .eq("user_id", user["id"]).eq("status","pending").execute()
        if existing.data:
            return True, ("A reset request is already pending. "
                          "Please wait for an admin to process it.")

        db().table("password_reset_requests").insert({
            "user_id": user["id"],
            "status":  "pending",
        }).execute()
        return True, ("✅ Reset request submitted. "
                       "An admin will provide you with a temporary password. "
                       "Contact your admin directly to confirm your identity.")
    except Exception as e:
        return False, f"Error submitting request: {e}"


# ── Session ───────────────────────────────────────────────────────────────────

def _parse_apps(apps_val) -> list:
    if isinstance(apps_val, list):
        return apps_val
    if isinstance(apps_val, str):
        import json
        try:    return json.loads(apps_val)
        except: return []
    return []


def set_session(user: dict):
    st.session_state.authenticated        = True
    st.session_state.user_id             = user["id"]
    st.session_state.username            = user.get("username", "")
    st.session_state.first_name          = user.get("first_name", "")
    st.session_state.last_name           = user.get("last_name", "")
    st.session_state.email               = user.get("email", "")
    st.session_state.role                = user.get("role", "user")
    st.session_state.organisation        = user.get("organisation", "")
    st.session_state.apps_access         = _parse_apps(user.get("apps_access"))
    st.session_state.force_password_change = bool(user.get("force_password_change"))


def clear_session():
    for k in ["authenticated", "user_id", "username", "first_name", "last_name",
              "email", "role", "organisation", "apps_access", "force_password_change"]:
        st.session_state.pop(k, None)


def is_authenticated() -> bool:
    return bool(st.session_state.get("authenticated"))


def require_auth():
    """
    Check authentication. Tries URL token (SSO) first, then session state.
    Redirects to login if neither is valid.
    """
    if is_authenticated():
        return
    # Try SSO token from URL
    try:
        from modules.sso import auto_login_from_url
        if auto_login_from_url():
            return
    except ImportError:
        pass  # sso module not present in this app yet
    st.switch_page("pages/login.py")


def is_admin() -> bool:
    return st.session_state.get("role") == "admin"


def needs_password_change() -> bool:
    return bool(st.session_state.get("force_password_change"))

# =============================================================
# SECURE BANK — BRANCH NETWORK SYSTEM
# Streamlit Frontend
#
# This file is a UI layer only. Security rules live in the backend:
#   - database/database.py, database/store.py   (persistence / SQL)
#   - database/migrations.py                    (upgrades an existing bank.db)
#   - modules/auth_service.py   (sign-in, lockout, 2FA step)
#   - modules/two_factor.py, modules/totp.py    (TOTP authenticator codes)
#   - modules/password_policy.py                (strength meter, change password)
#   - modules/messaging_service.py              (encrypted subject/body, threads)
#   - modules/encryption.py, key_management.py  (AES-256-GCM, key versions)
#   - modules/audit_chain.py                    (tamper-evident audit log)
#   - modules/alerts.py, analytics.py, reports.py  (admin monitoring)
#   - modules/session_timeout.py                (inactivity limit)
#
# Run from the project root:
#     streamlit run streamlit_app.py
# =============================================================

import html
import os
import sys
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))  # so "database/bank.db" etc. resolve

from database.database import (
    create_database,
    check_branches_table,
    create_messages_table,
    create_activity_logs_table,
    create_login_security_table,
    create_admins_table,
    create_admin_activity_logs_table,
    create_admin_login_security_table,
    insert_branch,
    branch_exists,
    get_all_branches,
    get_branch_by_id,
    get_branch_profile,
    log_activity,
    insert_admin,
    admin_exists,
    get_admin_by_username,
    get_all_branches_admin,
    get_all_messages_admin,
    get_all_activities_admin,
    get_all_login_security_admin,
    get_all_admin_login_security_details,
    reset_branch_login_security,
    reset_admin_login_security,
    log_admin_activity,
    get_activities_for_branch,
)
from database.migrations import run_migrations
from database import store

from modules.security import hash_password
from modules.encryption import generate_encryption_key
from modules.register import validate_password
from modules.admin_setup import validate_admin_password
from modules.login import validate_branch_code

from modules.auth_service import (
    PENDING_2FA_SECONDS,
    authenticate_branch,
    complete_branch_2fa,
    authenticate_admin,
    complete_admin_2fa,
)
from modules import two_factor, totp, analytics, reports
from modules import alerts as alert_engine
from modules.password_policy import (
    TEMP_PASSWORD_HOURS,
    change_password,
    force_password_change,
    issue_temporary_password,
    password_strength,
)
from modules.session_timeout import is_expired, SESSION_TIMEOUT_MINUTES
from modules.messaging_service import (
    MAX_BODY,
    MAX_SUBJECT,
    NO_SUBJECT,
    PRIORITIES,
    MessageIntegrityError,
    MessagingError,
    get_thread,
    list_box,
    open_message,
    send_message,
    set_status,
)
from modules.audit_chain import verify_all
from modules.key_management import key_status, reencrypt_all_messages, rotate_key

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


# =============================================================
# ONE-TIME DATABASE INITIALIZATION
# =============================================================

@st.cache_resource
def init_database():
    create_database()
    check_branches_table()
    create_messages_table()
    create_activity_logs_table()
    create_login_security_table()
    create_admins_table()
    create_admin_activity_logs_table()
    create_admin_login_security_table()
    try:
        generate_encryption_key()      # only creates a key if none exists
    except Exception:
        pass
    run_migrations()
    return True


init_database()


# =============================================================
# SMALL HELPERS
# =============================================================

def now_str():
    return datetime.now().strftime(DATETIME_FORMAT)


def branch_code_fmt(branch_id):
    return f"SB{branch_id:03d}"


def fmt_lock_wait(remaining_seconds):
    minutes = remaining_seconds // 60
    seconds = remaining_seconds % 60
    if minutes > 0:
        return f"{minutes} minute(s) and {seconds} second(s)"
    return f"{seconds} second(s)"


def badge(text, kind="neutral"):
    return f'<span class="sb-badge sb-badge-{kind}">{text}</span>'


# =============================================================
# PAGE CONFIG + PREMIUM BANKING THEME
# =============================================================

st.set_page_config(
    page_title="Secure Bank | Branch Network",
    page_icon="\U0001F3E6",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700;800&family=Inter:wght@400;500;600;700&display=swap');

/* LIGHT THEME: change these variables to re-colour the whole app */
:root{
    --sb-bg-1:#f7f9fd;          /* page background (top)     */
    --sb-bg-2:#e9eff8;          /* page background (bottom)  */
    --sb-panel:#ffffff;         /* cards, inputs             */
    --sb-panel-soft:#f1f5fb;    /* message box, sidebar      */
    --sb-line:#d5deec;          /* borders                   */
    --sb-navy:#14213d;
    --sb-gold:#c9a227;
    --sb-gold-soft:#e9cf7a;
    --sb-gold-dark:#8a6d12;
    --sb-text:#14213d;
    --sb-text-dim:#5b6b88;
    --sb-green:#12805a;
    --sb-red:#c0392b;
    --sb-amber:#9a6a00;
}

html, body, [class*="css"]  { font-family:'Inter', sans-serif; }

.stApp {
    background:
        radial-gradient(1100px 480px at 8% -10%, #dfe9fb 0%, transparent 60%),
        radial-gradient(900px 520px at 108% 8%, #f6ecd0 0%, transparent 55%),
        linear-gradient(180deg, var(--sb-bg-1) 0%, var(--sb-bg-2) 100%);
    color: var(--sb-text);
}

h1, h2, h3 { font-family:'Playfair Display', serif !important; letter-spacing:.3px; color: var(--sb-navy); }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #ffffff 0%, var(--sb-panel-soft) 100%);
    border-right: 1px solid var(--sb-line);
}
section[data-testid="stSidebar"] * { color: var(--sb-text) !important; }

/* Cards */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--sb-panel);
    border: 1px solid var(--sb-line) !important;
    border-radius: 16px !important;
    box-shadow: 0 6px 22px rgba(20,33,61,0.08);
}

/* Buttons */
.stButton>button, .stFormSubmitButton>button {
    background: linear-gradient(135deg, var(--sb-gold-soft) 0%, var(--sb-gold) 100%);
    color: #1a1204;
    border: none;
    border-radius: 10px;
    font-weight: 700;
    padding: 0.55em 1.4em;
    transition: all .15s ease;
    box-shadow: 0 4px 12px rgba(201,162,39,0.28);
}
.stButton>button:hover, .stFormSubmitButton>button:hover {
    transform: translateY(-1px);
    box-shadow: 0 8px 18px rgba(201,162,39,0.38);
    color: #1a1204;
}
.stButton>button:disabled, .stFormSubmitButton>button:disabled {
    background: #e3e8f1; color: #8e9bb3; box-shadow: none; transform: none;
}
.stButton>button[kind="secondary"]{
    background: transparent;
    color: var(--sb-gold-dark) !important;
    border: 1px solid var(--sb-gold);
    box-shadow:none;
}

/* Inputs */
.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div,
.stDateInput input, .stNumberInput input {
    background: var(--sb-panel) !important;
    color: var(--sb-text) !important;
    border: 1px solid var(--sb-line) !important;
    border-radius: 10px !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: var(--sb-gold) !important;
    box-shadow: 0 0 0 1px var(--sb-gold) !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid var(--sb-line); }
.stTabs [data-baseweb="tab"] {
    color: var(--sb-text-dim);
    font-weight: 600;
    padding: 10px 18px;
}
.stTabs [aria-selected="true"] {
    color: var(--sb-gold-dark) !important;
    border-bottom: 2px solid var(--sb-gold) !important;
}

/* Hero */
.sb-hero {
    padding: 46px 42px;
    border-radius: 22px;
    background: linear-gradient(135deg, #ffffff 0%, #eef3fc 100%);
    border: 1px solid var(--sb-line);
    box-shadow: 0 16px 44px rgba(20,33,61,0.10);
    margin-bottom: 28px;
}
.sb-eyebrow {
    display:inline-block;
    letter-spacing: 3px;
    font-size: 12px;
    color: var(--sb-gold-dark);
    text-transform: uppercase;
    border: 1px solid var(--sb-gold);
    border-radius: 999px;
    padding: 5px 14px;
    margin-bottom: 16px;
}
.sb-hero h1 { font-size: 44px; margin: 0 0 6px 0; color: var(--sb-navy); }
.sb-hero p.sub { color: var(--sb-text-dim); font-size: 17px; max-width: 620px; }

/* Badges */
.sb-badge {
    display:inline-block; padding: 3px 12px; border-radius: 999px;
    font-size: 12px; font-weight: 700; letter-spacing: .4px;
}
.sb-badge-success { background: rgba(18,128,90,0.10); color: var(--sb-green); border:1px solid rgba(18,128,90,0.40);}
.sb-badge-warning  { background: rgba(154,106,0,0.10); color: var(--sb-amber); border:1px solid rgba(154,106,0,0.40);}
.sb-badge-danger  { background: rgba(192,57,43,0.10); color: var(--sb-red); border:1px solid rgba(192,57,43,0.40);}
.sb-badge-neutral { background: rgba(91,107,136,0.10); color: var(--sb-text-dim); border:1px solid rgba(91,107,136,0.35);}

/* Message bubble */
.sb-message-box {
    background: var(--sb-panel-soft);
    border: 1px solid var(--sb-line);
    border-left: 4px solid var(--sb-gold);
    border-radius: 14px;
    padding: 18px 20px;
    font-size: 15.5px;
    line-height: 1.55;
    color: var(--sb-text);
    white-space: pre-wrap;
}

.sb-divider { height:1px; background: linear-gradient(90deg, transparent, var(--sb-line), transparent); margin: 18px 0; border:none;}

.sb-footnote { color: var(--sb-text-dim); font-size: 13px; }

/* Metric-like small stat */
.sb-stat { text-align:center; padding: 10px 0; }
.sb-stat .n { font-family:'Playfair Display', serif; font-size: 30px; color: var(--sb-gold-dark); font-weight:700;}
.sb-stat .l { color: var(--sb-text-dim); font-size: 12.5px; letter-spacing:1px; text-transform:uppercase;}

table { color: var(--sb-text) !important; }
</style>
""",
    unsafe_allow_html=True,
)


# =============================================================
# SESSION STATE DEFAULTS
# =============================================================

defaults = {
    "page": "home",
    "branch_session": None,
    "admin_session": None,
    "profile_logged_this_session": False,
    "pending_2fa": None,       # password accepted, waiting for the 2FA code
    "view_msg": None,          # message currently opened in the detail view
    "form_nonce": 0,           # changing it gives widgets fresh (empty) keys
    "flash": None,             # (level, text) shown once on the next run
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def go(page):
    st.session_state["page"] = page


def flash(level, text):
    """Show a message once after the next st.rerun()."""
    st.session_state["flash"] = (level, text)


def show_flash():
    item = st.session_state["flash"]
    if item:
        level, text = item
        getattr(st, level)(text)
        st.session_state["flash"] = None


def bump_nonce():
    """Clears every nonce-keyed input (passwords etc.) on the next run."""
    st.session_state["form_nonce"] += 1


def nk(name):
    return f"{name}_{st.session_state['form_nonce']}"


# =============================================================
# SESSIONS: START, END, INACTIVITY TIMEOUT
# =============================================================

def start_branch_session(result):
    now = datetime.now()
    st.session_state["branch_session"] = {
        "branch_id": result.account_id,
        "branch_code": branch_code_fmt(result.account_id),
        "branch_name": result.account_name,
        "login_time": now.strftime(DATETIME_FORMAT),
        "last_activity": now,
        "must_change_password": result.must_change_password,
    }
    st.session_state["profile_logged_this_session"] = False
    st.session_state["view_msg"] = None
    st.session_state["pending_2fa"] = None


def start_admin_session(result):
    now = datetime.now()
    st.session_state["admin_session"] = {
        "admin_id": result.account_id,
        "username": result.account_name,
        "login_time": now.strftime(DATETIME_FORMAT),
        "last_activity": now,
        "must_change_password": result.must_change_password,
    }
    st.session_state["pending_2fa"] = None


def end_session(kind, event, description):
    """Writes the audit entry and clears the session."""
    if kind == "branch":
        session = st.session_state["branch_session"]
        if session:
            log_activity(session["branch_id"], event, description, now_str())
        st.session_state["branch_session"] = None
        st.session_state["profile_logged_this_session"] = False
        st.session_state["view_msg"] = None
    else:
        session = st.session_state["admin_session"]
        if session:
            log_admin_activity(session["admin_id"], event, description,
                               now_str())
        st.session_state["admin_session"] = None


def enforce_session_timeouts():
    """Runs at the top of every script run. Any interaction counts as
    activity; a session idle for longer than the limit is closed (and
    logged) before anything is shown."""

    now = datetime.now()

    for kind, key, event in (
        ("branch", "branch_session", "SESSION_TIMEOUT"),
        ("admin", "admin_session", "ADMIN_SESSION_TIMEOUT"),
    ):
        session = st.session_state[key]
        if session is None:
            continue

        if is_expired(session["last_activity"], now):
            end_session(
                kind, event,
                f"Signed out automatically after {SESSION_TIMEOUT_MINUTES} "
                "minutes of inactivity",
            )
            flash(
                "warning",
                f"You were signed out after {SESSION_TIMEOUT_MINUTES} "
                "minutes of inactivity. Please sign in again.",
            )
        else:
            session["last_activity"] = now

    pending = st.session_state["pending_2fa"]
    if pending and (now - pending["started"]).total_seconds() \
            > PENDING_2FA_SECONDS:
        st.session_state["pending_2fa"] = None
        flash("warning", "The verification step timed out. "
                         "Please sign in again.")


enforce_session_timeouts()


# =============================================================
# SHARED UI COMPONENTS
# =============================================================

def strength_meter(password, context_words=()):
    info = password_strength(password, context_words)
    st.progress(info["score"] / 4,
                text=f"Password strength: {info['label']}")
    columns = st.columns(2)
    for index, (text, passed) in enumerate(info["rules"]):
        columns[index % 2].caption(("\u2705 " if passed else "\u2B1C ") + text)
    for hint in info["feedback"]:
        st.caption("\U0001F4A1 " + hint)
    return info


def show_auth_failure(result):
    if result.status == "LOCKED":
        st.error(
            f"{result.message}\n\n"
            f"Try again in approximately "
            f"{fmt_lock_wait(result.remaining_seconds)}.\n\n"
            "Maximum failed attempts: 3 \u00B7 Lockout duration: 5 minutes."
        )
    else:
        st.error(result.message)


def render_2fa_challenge(pending):
    """Second login step: the 6-digit code from the authenticator app."""

    with st.container(border=True):
        st.markdown("#### \U0001F510 Two-Factor Verification")
        st.caption(
            f"Signing in as **{pending['label']}**. Open your authenticator "
            "app and enter the current 6-digit code."
        )
        with st.form("two_factor_form", clear_on_submit=True):
            code = st.text_input("Authentication code", max_chars=6,
                                 placeholder="123456")
            col_a, col_b = st.columns(2)
            verify = col_a.form_submit_button("Verify & Sign In",
                                              use_container_width=True)
            cancel = col_b.form_submit_button("Cancel",
                                              use_container_width=True)

    if cancel:
        st.session_state["pending_2fa"] = None
        st.rerun()

    if verify:
        code = code.strip()
        if pending["kind"] == "branch":
            result = complete_branch_2fa(pending["account_id"], code,
                                         pending["name"])
        else:
            result = complete_admin_2fa(pending["account_id"], code,
                                        pending["name"])

        if result.ok:
            if pending["kind"] == "branch":
                start_branch_session(result)
            else:
                start_admin_session(result)
            st.rerun()
        else:
            if result.status == "LOCKED":
                st.session_state["pending_2fa"] = None
            show_auth_failure(result)


def render_change_password(kind, account_id, name):
    """Change-password card (also used for the forced change)."""

    with st.container(border=True):
        st.markdown("#### \U0001F511 Change Password")
        current = st.text_input("Current password", type="password",
                                key=nk(f"{kind}_cp_current"))
        new = st.text_input("New password", type="password",
                            key=nk(f"{kind}_cp_new"))
        strength_meter(new, context_words=(name,))
        confirm = st.text_input("Confirm new password", type="password",
                                key=nk(f"{kind}_cp_confirm"))

        if st.button("Update Password", use_container_width=True,
                     key=nk(f"{kind}_cp_button")):
            ok, message = change_password(kind, account_id, current, new,
                                          confirm)
            if ok:
                session_key = "branch_session" if kind == "branch" \
                    else "admin_session"
                st.session_state[session_key]["must_change_password"] = False
                bump_nonce()
                flash("success", message)
                st.rerun()
            else:
                st.error(message)


def render_two_factor_panel(kind, account_id, label):
    """Enable / disable authenticator-app (TOTP) two-factor login."""

    with st.container(border=True):
        st.markdown("#### \U0001F6E1\uFE0F Two-Factor Authentication (TOTP)")

        # ---- already enabled -----------------------------------
        if two_factor.is_enabled(kind, account_id):
            st.markdown(badge("2FA ENABLED", "success"),
                        unsafe_allow_html=True)
            st.caption(
                "To turn it off, confirm your password and a current "
                "authenticator code."
            )
            with st.form(f"{kind}_2fa_disable_form", clear_on_submit=True):
                password = st.text_input("Password", type="password")
                code = st.text_input("Current authentication code",
                                     max_chars=6)
                disable_clicked = st.form_submit_button(
                    "Disable Two-Factor Authentication",
                    use_container_width=True)
            if disable_clicked:
                ok, message = two_factor.disable(kind, account_id, password,
                                                 code.strip())
                if ok:
                    flash("success", message)
                    st.rerun()
                else:
                    st.error(message)
            return

        # ---- enrolment started, waiting for the first code -------
        secret = two_factor.get_pending_secret(kind, account_id)

        if secret is None:
            st.markdown(badge("2FA OFF", "warning"), unsafe_allow_html=True)
            st.caption(
                "Add a second step to sign-in: a 6-digit code from an "
                "authenticator app (Google Authenticator, Microsoft "
                "Authenticator, Authy)."
            )
            if st.button("Set Up Two-Factor Authentication",
                         key=f"{kind}_2fa_start", use_container_width=True):
                two_factor.start_enrollment(kind, account_id)
                st.rerun()
            return

        uri = totp.provisioning_uri(secret, label)
        qr = totp.qr_png_bytes(uri)
        col_qr, col_key = st.columns([1, 2])

        if qr:
            col_qr.image(qr, caption="Scan with your authenticator app",
                         width=200)
        else:
            col_qr.info("QR image unavailable (optional package "
                        "`qrcode[pil]` is not installed). Use the key.")

        col_key.markdown("Can't scan? Enter this key manually "
                         "(time-based, 6 digits):")
        col_key.code(secret, language=None)
        col_key.caption("Then enter the code the app shows to finish.")

        with st.form(f"{kind}_2fa_confirm_form", clear_on_submit=True):
            code = st.text_input("Code from the app", max_chars=6,
                                 placeholder="123456")
            col_a, col_b = st.columns(2)
            confirm_clicked = col_a.form_submit_button(
                "Confirm & Enable", use_container_width=True)
            cancel_clicked = col_b.form_submit_button(
                "Cancel Setup", use_container_width=True)

        if cancel_clicked:
            two_factor.cancel_enrollment(kind, account_id)
            st.rerun()

        if confirm_clicked:
            if two_factor.confirm_enrollment(kind, account_id, code.strip()):
                flash("success", "Two-factor authentication is now enabled.")
                st.rerun()
            else:
                st.error("That code is not correct. Check the time on your "
                         "phone and try again.")


def priority_badge(priority):
    kind = {"URGENT": "danger", "CONFIDENTIAL": "warning"}.get(priority,
                                                               "neutral")
    return badge(priority, kind)


def branch_display(branch_id):
    branch = get_branch_by_id(branch_id)
    if branch is None:
        return branch_code_fmt(branch_id)
    return f"{branch[1]} ({branch_code_fmt(branch_id)})"


# =============================================================
# SIDEBAR
# =============================================================

with st.sidebar:
    st.markdown(
        "<div style='text-align:center;padding:6px 0 2px 0;'>"
        "<span style='font-size:38px;'>\U0001F3E6</span>"
        "<h2 style='margin:6px 0 0 0;color:var(--sb-text);'>SECURE BANK</h2>"
        "<div style='color:var(--sb-gold-dark);letter-spacing:2px;font-size:12px;'>BRANCH NETWORK SYSTEM</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<hr class='sb-divider'/>", unsafe_allow_html=True)

    nav_choice = st.radio(
        "Navigate",
        ["Home", "Branch Portal", "Admin Portal"],
        index=["home", "branch", "admin"].index(st.session_state["page"]) if st.session_state["page"] in ["home", "branch", "admin"] else 0,
        label_visibility="collapsed",
    )
    st.session_state["page"] = {"Home": "home", "Branch Portal": "branch", "Admin Portal": "admin"}[nav_choice]

    st.markdown("<hr class='sb-divider'/>", unsafe_allow_html=True)

    if st.session_state["branch_session"]:
        b = st.session_state["branch_session"]
        st.markdown(f"**Branch signed in**  \n{b['branch_name']} ({b['branch_code']})")
        st.caption(f"Login time: {b['login_time']}")

    if st.session_state["admin_session"]:
        a = st.session_state["admin_session"]
        st.markdown(f"**Admin signed in**  \n{a['username']}")
        st.caption(f"Login time: {a['login_time']}")

    if st.session_state["branch_session"] or st.session_state["admin_session"]:
        st.caption(f"Auto sign-out after {SESSION_TIMEOUT_MINUTES} minutes "
                   "of inactivity")

    st.markdown("<hr class='sb-divider'/>", unsafe_allow_html=True)
    st.caption("AES-256-GCM encrypted messaging (versioned keys)")
    st.caption("PBKDF2-SHA256 (600,000 iterations) password hashing")
    st.caption("Optional TOTP two-factor authentication")
    st.caption("Admin-issued temporary password recovery")
    st.caption("Tamper-evident audit log (HMAC chain)")
    st.caption("Automatic lockout after 3 failed attempts")


# =============================================================
# HOME PAGE
# =============================================================

def render_home():
    branches = get_all_branches()

    st.markdown(
        f"""
<div class="sb-hero">
    <div class="sb-eyebrow">Inter-Branch Secure Network</div>
    <h1>Secure Bank Branch Network</h1>
    <p class="sub">A protected channel for Secure Bank branches to authenticate, exchange
    end-to-end encrypted messages, and give administrators full oversight —
    without ever exposing message contents or credentials.</p>
</div>
""",
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        with st.container(border=True):
            st.markdown(f"<div class='sb-stat'><div class='n'>{len(branches)}</div><div class='l'>Registered Branches</div></div>", unsafe_allow_html=True)
    with c2:
        with st.container(border=True):
            st.markdown("<div class='sb-stat'><div class='n'>AES-256</div><div class='l'>Message Encryption</div></div>", unsafe_allow_html=True)
    with c3:
        with st.container(border=True):
            st.markdown("<div class='sb-stat'><div class='n'>SQLite</div><div class='l'>Secure Local Storage</div></div>", unsafe_allow_html=True)

    st.write("")
    col1, col2 = st.columns(2, gap="large")

    with col1:
        with st.container(border=True):
            st.subheader("\U0001F3E6 Branch Portal")
            st.write(
                "Register your branch, sign in with your Secure Bank branch code, "
                "and exchange encrypted messages with other branches."
            )
            if st.button("Enter Branch Portal", key="home_branch_btn", use_container_width=True):
                go("branch")
                st.rerun()

    with col2:
        with st.container(border=True):
            st.subheader("\U0001F6E1\uFE0F Admin Portal")
            st.write(
                "Monitor branches, review message metadata, audit system activity, "
                "and manage login-security lockouts."
            )
            if st.button("Enter Admin Portal", key="home_admin_btn", use_container_width=True):
                go("admin")
                st.rerun()

    st.write("")
    with st.expander("About this project"):
        st.markdown(
            """
- **Project** : Secure Bank Branch Network
- **Bank**    : Secure Bank
- **Language**: Python (backend) + Streamlit (frontend)
- **Database**: SQLite
- **Security**:
    - Branch & admin passwords hashed with PBKDF2-HMAC-SHA256, 600,000 iterations, random salt
    - Messages encrypted with AES-256-GCM (authenticated encryption — tampering is detected on decrypt)
    - Login lockout after 3 failed attempts, 5-minute cool-down, per branch and per admin
    - Every login, logout, message, and admin action is written to an activity log
"""
        )


# =============================================================
# BRANCH PORTAL — AUTH
# =============================================================

def render_branch_login_form():
    with st.container(border=True):
        st.markdown("#### Branch Sign In")
        with st.form("branch_login_form", clear_on_submit=True):
            branch_code_input = st.text_input("Branch Code", placeholder="e.g. SB001").strip().upper()
            password_input = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)

        if submitted:
            result = authenticate_branch(branch_code_input, password_input)

            if result.ok:
                start_branch_session(result)
                st.rerun()
            elif result.status == "NEEDS_2FA":
                st.session_state["pending_2fa"] = {
                    "kind": "branch",
                    "account_id": result.account_id,
                    "name": result.account_name,
                    "label": f"{result.account_name} ({branch_code_fmt(result.account_id)})",
                    "started": datetime.now(),
                }
                st.rerun()
            else:
                show_auth_failure(result)

        st.caption(
            "\U0001F511 Forgot your password? Contact your administrator: they can issue a "
            "temporary password that you must change at your next sign-in."
        )


def render_branch_register():
    with st.container(border=True):
        st.markdown("#### Register a New Branch")
        st.caption(
            "Password must be at least 10 characters and include an uppercase letter, "
            "a lowercase letter, a digit, and a special character."
        )

        branch_name_input = st.text_input("Branch Name", placeholder="e.g. Bangalore", key=nk("reg_name"))
        new_password = st.text_input("Password", type="password", key=nk("reg_password"))
        strength_meter(new_password, context_words=(branch_name_input,))
        confirm_password = st.text_input("Confirm Password", type="password", key=nk("reg_confirm"))

        if st.button("Register Branch", use_container_width=True, key=nk("reg_button")):
            name = branch_name_input.strip()

            if name == "":
                st.error("Branch name cannot be empty.")
            elif len(name) < 3:
                st.error("Branch name must contain at least 3 characters.")
            elif len(name) > 50:
                st.error("Branch name cannot exceed 50 characters.")
            elif branch_exists(name):
                st.error(f"Branch '{name}' already exists. Please choose a different name.")
            elif not validate_password(new_password):
                st.error(
                    "Password does not meet security requirements: at least 10 characters, "
                    "one uppercase, one lowercase, one digit, one special character, "
                    "and not a common weak password."
                )
            elif new_password != confirm_password:
                st.error("Passwords do not match.")
            else:
                password_hash, password_salt = hash_password(new_password)
                branch_id = insert_branch(name, password_hash, password_salt, now_str())
                code = branch_code_fmt(branch_id)
                bump_nonce()

                # Keep the result, then rerun so the input fields come back empty
                st.session_state["reg_success"] = {"id": branch_id, "code": code, "name": name}
                st.rerun()

        done = st.session_state.pop("reg_success", None)
        if done:
            st.success("Registration successful!")
            with st.container(border=True):
                st.markdown(f"**Branch ID**  \n{done['id']}")
                st.markdown(f"**Branch Code**  \n`{done['code']}`")
                st.markdown(f"**Branch Name**  \n{done['name']}")
            st.info("Save your branch code — you'll need it to sign in. "
                    "You can enable two-factor authentication from "
                    "Profile & Security after signing in.")


def render_branch_auth():
    st.markdown("## \U0001F3E6 Branch Portal")

    # st.tabs forgets the chosen tab on every rerun, so a keyed radio is used
    auth_sections = ["Sign In", "Register New Branch"]
    auth_choice = st.radio("Branch portal section", auth_sections, horizontal=True,
                           key="auth_section", label_visibility="collapsed")

    if auth_choice == auth_sections[0]:
        pending = st.session_state["pending_2fa"]
        if pending and pending["kind"] == "branch":
            render_2fa_challenge(pending)
        else:
            render_branch_login_form()
    else:
        render_branch_register()


# =============================================================
# BRANCH PORTAL — MESSAGING
# =============================================================

def render_message_detail(branch_id, message_id, box, status, prefix):
    """One opened message: body, conversation, reply and actions."""

    if st.button("\u2190 Back to list", key=f"{prefix}_back"):
        st.session_state["view_msg"] = None
        st.rerun()

    try:
        message = open_message(message_id, branch_id)
    except MessageIntegrityError:
        st.error("Unable to decrypt this message. It may have been modified or corrupted.")
        return
    except (MessagingError, PermissionError) as error:
        st.error(str(error))
        return

    sender_id = message["sender_branch_id"]
    receiver_id = message["receiver_branch_id"]
    is_receiver = receiver_id == branch_id
    other_id = sender_id if is_receiver else receiver_id

    with st.container(border=True):
        st.markdown(
            f"<h4 style='margin-bottom:4px;'>{html.escape(message['subject'])}</h4>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"{'From' if is_receiver else 'To'} **{html.escape(branch_display(other_id))}** "
            f"\u00B7 <span class='sb-footnote'>{message['sent_date']}</span> "
            f"{priority_badge(message['priority'])}",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div class='sb-message-box'>{html.escape(message['body'])}</div>",
            unsafe_allow_html=True,
        )
        st.caption(f"Encrypted with key version {message['key_id']} (AES-256-GCM)")

    # ---- conversation ------------------------------------------
    try:
        thread = get_thread(message_id, branch_id)
    except (MessagingError, PermissionError):
        thread = []

    if len(thread) > 1:
        with st.expander(f"Conversation ({len(thread)} messages)"):
            for item in thread:
                who = "You" if item["direction"] == "sent" else branch_display(item["sender_branch_id"])
                st.markdown(
                    f"**{html.escape(who)}** \u00B7 "
                    f"<span class='sb-footnote'>{item['sent_date']}</span>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<div class='sb-message-box'>{html.escape(item['body'])}</div>",
                    unsafe_allow_html=True,
                )

    # ---- reply (only to a message you received) -----------------
    if is_receiver:
        with st.form(f"{prefix}_reply_form", clear_on_submit=True):
            st.markdown("##### Reply")
            reply_text = st.text_area("Your reply", max_chars=MAX_BODY, height=110,
                                      placeholder=f"Type your reply (max {MAX_BODY} characters)...")
            reply_priority = st.selectbox("Priority", list(PRIORITIES))
            send_reply = st.form_submit_button("Encrypt & Send Reply", use_container_width=True)

        if send_reply:
            original = message["subject"]
            if original == NO_SUBJECT:
                reply_subject = ""
            elif original.lower().startswith("re:"):
                reply_subject = original
            else:
                reply_subject = f"Re: {original}"[:MAX_SUBJECT]

            try:
                new_id = send_message(branch_id, other_id, reply_text,
                                      subject=reply_subject, priority=reply_priority,
                                      parent_id=message_id)
            except MessagingError as error:
                st.error(str(error))
            else:
                flash("success", f"Reply #{new_id} sent securely to {branch_display(other_id)}.")
                st.rerun()

    # ---- archive / delete / restore -----------------------------
    st.markdown("##### Manage")
    col_a, col_b, col_c = st.columns(3)

    if status == "ACTIVE":
        if col_a.button("\U0001F5C4\uFE0F Archive", key=f"{prefix}_archive", use_container_width=True):
            set_status(message_id, branch_id, "ARCHIVED")
            st.session_state["view_msg"] = None
            flash("success", f"Message #{message_id} archived.")
            st.rerun()
    else:
        if col_a.button("\u21A9\uFE0F Restore", key=f"{prefix}_restore", use_container_width=True):
            set_status(message_id, branch_id, "ACTIVE")
            st.session_state["view_msg"] = None
            flash("success", f"Message #{message_id} restored.")
            st.rerun()

    confirm_delete = col_c.checkbox("Confirm delete", key=f"{prefix}_confirm_delete")
    if col_b.button("\U0001F5D1\uFE0F Delete", key=f"{prefix}_delete",
                    disabled=not confirm_delete, use_container_width=True):
        set_status(message_id, branch_id, "DELETED")
        st.session_state["view_msg"] = None
        flash("success", f"Message #{message_id} deleted from your view.")
        st.rerun()

    st.caption("Deleting removes the message from your mailbox only. The other branch "
               "keeps its copy and the record is retained for auditing.")


def render_message_box(branch_id, box, status, prefix, title):
    """List (with search & filters) or, when one is opened, its detail."""

    view = st.session_state["view_msg"]
    if view and view["box"] == prefix:
        render_message_detail(branch_id, view["id"], box, status, prefix)
        return

    other_label_text = "From" if box == "inbox" else "To"
    other_options = {"All branches": None}
    for (bid, bname, _created) in get_all_branches():
        if bid != branch_id:
            other_options[f"{bname} ({branch_code_fmt(bid)})"] = bid

    with st.expander("\U0001F50E Search & filter"):
        col_a, col_b, col_c = st.columns([3, 2, 2])
        keyword = col_a.text_input("Search subject or text", key=f"{prefix}_keyword")
        priority_choice = col_b.selectbox("Priority", ["All", *PRIORITIES], key=f"{prefix}_priority")
        if box == "inbox":
            unread_only = col_c.checkbox("Unread only", key=f"{prefix}_unread")
        else:
            unread_only = False

        col_d, col_e = st.columns(2)
        other_choice = col_d.selectbox(other_label_text, list(other_options), key=f"{prefix}_other")
        use_dates = col_e.checkbox("Filter by date", key=f"{prefix}_use_dates")

        date_from = date_to = None
        if use_dates:
            col_f, col_g = st.columns(2)
            date_from = col_f.date_input("From date", value=date.today() - timedelta(days=30),
                                         key=f"{prefix}_date_from")
            date_to = col_g.date_input("To date", value=date.today(), key=f"{prefix}_date_to")

    rows = list_box(
        branch_id, box, status=status,
        keyword=keyword,
        priority=None if priority_choice == "All" else priority_choice,
        other_branch_id=other_options[other_choice],
        date_from=date_from, date_to=date_to,
        unread_only=unread_only,
    )

    unread = sum(1 for r in rows if r["is_read"] == 0) if box == "inbox" else 0
    st.markdown(f"#### {title} ({len(rows)})" + (f" \u00B7 {unread} unread" if unread else ""))

    if not rows:
        st.info("No messages found.")
        return

    for row in rows:
        with st.container(border=True):
            top = st.columns([5, 3, 3])
            direction = "From" if box == "inbox" else "To"
            top[0].markdown(
                f"**#{row['message_id']} \u00B7 {html.escape(row['subject'])}**  \n"
                f"<span class='sb-footnote'>{direction} {html.escape(branch_display(row['other_branch_id']))}</span>",
                unsafe_allow_html=True,
            )
            top[1].markdown(f"<span class='sb-footnote'>{row['sent_date']}</span>", unsafe_allow_html=True)

            badges = priority_badge(row["priority"])
            if not row["intact"]:
                badges += " " + badge("INTEGRITY FAILED", "danger")
            elif box == "inbox":
                badges += " " + (badge("READ", "neutral") if row["is_read"] == 1 else badge("NEW", "success"))
            else:
                badges += " " + (badge("READ", "success") if row["is_read"] == 1 else badge("UNREAD", "warning"))
            top[2].markdown(badges, unsafe_allow_html=True)

            if row["parent_message_id"]:
                st.caption(f"Reply to #{row['parent_message_id']}")

            if st.button("Decrypt & View", key=f"{prefix}_open_{row['message_id']}"):
                st.session_state["view_msg"] = {"box": prefix, "id": row["message_id"]}
                st.rerun()


def render_send_message(branch_id):
    with st.container(border=True):
        st.markdown("#### Send a Secure Message")

        other_branches = [
            (bid, bname) for (bid, bname, _created) in get_all_branches() if bid != branch_id
        ]

        if not other_branches:
            st.info("No other branches are available to message yet.")
            return

        options = {f"{name} ({branch_code_fmt(bid)})": bid for (bid, name) in other_branches}

        with st.form("send_message_form", clear_on_submit=True):
            receiver_label = st.selectbox("Receiver Branch", list(options.keys()))
            col_a, col_b = st.columns([3, 1])
            subject = col_a.text_input("Subject", max_chars=MAX_SUBJECT, placeholder="Short subject (optional)")
            priority = col_b.selectbox("Priority", list(PRIORITIES))
            message_text = st.text_area("Message", max_chars=MAX_BODY, height=140,
                                        placeholder=f"Type your secure message (max {MAX_BODY} characters)...")
            submitted = st.form_submit_button("Encrypt & Send", use_container_width=True)

        if submitted:
            try:
                message_id = send_message(branch_id, options[receiver_label], message_text,
                                          subject=subject, priority=priority)
            except MessagingError as error:
                st.error(str(error))
            else:
                st.success(
                    f"Message #{message_id} sent securely to {receiver_label}. "
                    "Subject and text were encrypted with AES-256-GCM before being stored."
                )


# =============================================================
# BRANCH PORTAL — DASHBOARD
# =============================================================

def render_branch_dashboard():
    session = st.session_state["branch_session"]
    branch_id = session["branch_id"]

    st.markdown(f"## \U0001F3E6 Welcome, {session['branch_name']} Branch")
    st.caption(f"Branch Code: `{session['branch_code']}` \u00B7 Signed in at {session['login_time']}")

    # An administrator can require a new password before anything else
    if session.get("must_change_password"):
        st.warning(
            "An administrator requires you to choose a new password before you continue. "
            "If you were given a temporary password, enter it as the current password."
        )
        render_change_password("branch", branch_id, session["branch_name"])
        if st.button("Sign out", key="forced_branch_logout"):
            end_session("branch", "LOGOUT", "Branch logged out")
            st.rerun()
        return

    # st.tabs jumps back to the first tab after every rerun (button click,
    # st.rerun, download...). A keyed radio remembers the chosen section.
    tab_names = [
        "\U0001F4E4 Send Message",
        "\U0001F4E5 Inbox",
        "\U0001F4EC Sent",
        "\U0001F5C4\uFE0F Archive",
        "\U0001F464 Profile & Security",
        "\U0001F4CB Activity History",
        "\U0001F6AA Logout",
    ]
    selected_tab = st.radio("Section", tab_names, horizontal=True,
                            key="branch_section", label_visibility="collapsed")

    if selected_tab == tab_names[0]:
        render_send_message(branch_id)

    if selected_tab == tab_names[1]:
        render_message_box(branch_id, "inbox", "ACTIVE", "inbox", "Inbox")

    if selected_tab == tab_names[2]:
        render_message_box(branch_id, "sent", "ACTIVE", "sent", "Sent Messages")

    if selected_tab == tab_names[3]:
        which = st.radio("Show archived", ["Received", "Sent"], horizontal=True, key="archive_which")
        if which == "Received":
            render_message_box(branch_id, "inbox", "ARCHIVED", "archive_inbox", "Archived (received)")
        else:
            render_message_box(branch_id, "sent", "ARCHIVED", "archive_sent", "Archived (sent)")

    # --------------------------------------------------
    # PROFILE & SECURITY
    # --------------------------------------------------
    if selected_tab == tab_names[4]:
        profile = get_branch_profile(branch_id)

        if profile is None:
            st.error("Unable to retrieve branch profile.")
        else:
            profile_branch_id, branch_name, created_date = profile

            if not st.session_state["profile_logged_this_session"]:
                log_activity(branch_id, "PROFILE_VIEWED", "Branch profile viewed", now_str())
                st.session_state["profile_logged_this_session"] = True

            with st.container(border=True):
                st.markdown("#### Branch Profile")
                c1, c2 = st.columns(2)
                c1.markdown(f"**Branch ID**  \n{profile_branch_id}")
                c1.markdown(f"**Branch Code**  \n`{session['branch_code']}`")
                c2.markdown(f"**Branch Name**  \n{branch_name}")
                c2.markdown(f"**Registered Date**  \n{created_date}")
                changed = store.get_password_changed_date("branch", branch_id)
                c2.markdown(f"**Password last changed**  \n{changed or 'Never'}")
                st.markdown("---")
                tfa = badge("2FA ON", "success") if two_factor.is_enabled("branch", branch_id) else badge("2FA OFF", "warning")
                st.markdown(badge("ACCOUNT ACTIVE", "success") + "&nbsp;&nbsp;" + tfa, unsafe_allow_html=True)

        render_two_factor_panel("branch", branch_id, f"{session['branch_code']}")
        render_change_password("branch", branch_id, session["branch_name"])

    # --------------------------------------------------
    # ACTIVITY HISTORY
    # --------------------------------------------------
    if selected_tab == tab_names[5]:
        st.markdown("#### Activity History")
        activities = get_activities_for_branch(branch_id)

        if not activities:
            st.info("No activity records found.")
        else:
            rows = [
                {"ID": a[0], "Activity": a[2], "Description": a[3], "Date & Time": a[4]}
                for a in activities
            ]
            st.dataframe(rows, use_container_width=True, hide_index=True)

    # --------------------------------------------------
    # LOGOUT
    # --------------------------------------------------
    if selected_tab == tab_names[6]:
        with st.container(border=True):
            st.markdown("#### Logout")
            st.write("This will end your secure session. You'll need your branch code and password to sign in again.")

            if st.button("Confirm Logout", key="branch_logout_btn"):
                end_session("branch", "LOGOUT", "Branch logged out")
                flash("success", "You have been securely logged out.")
                st.rerun()


def render_branch_portal():
    if st.session_state["branch_session"] is None:
        render_branch_auth()
    else:
        render_branch_dashboard()


# =============================================================
# ADMIN PORTAL — AUTH
# =============================================================

def render_admin_auth():
    st.markdown("## \U0001F6E1\uFE0F Admin Portal")

    pending = st.session_state["pending_2fa"]
    if pending and pending["kind"] == "admin":
        render_2fa_challenge(pending)
        return

    with st.container(border=True):
        st.markdown("#### Administrator Sign In")

        with st.form("admin_login_form", clear_on_submit=True):
            username_input = st.text_input("Username")
            password_input = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)

        if submitted:
            result = authenticate_admin(username_input, password_input)

            if result.ok:
                start_admin_session(result)
                st.rerun()
            elif result.status == "NEEDS_2FA":
                st.session_state["pending_2fa"] = {
                    "kind": "admin",
                    "account_id": result.account_id,
                    "name": result.account_name,
                    "label": result.account_name,
                    "started": datetime.now(),
                }
                st.rerun()
            else:
                show_auth_failure(result)

    st.caption(
        "\U0001F511 Forgot your password? Another administrator can issue a temporary password "
        "(Security Center > Account Recovery). If you are the only administrator, run "
        "`python -m modules.admin_recovery` on the server."
    )
    st.caption("Tip: the seed administrator account is created via modules/admin_setup.py (`python -m modules.admin_setup`).")


# =============================================================
# ADMIN PORTAL — ANALYTICS / ALERTS / SECURITY CENTER
# =============================================================

def _series_frame(series, label):
    return pd.DataFrame(series, columns=["Day", label]).set_index("Day")


def render_admin_analytics():
    days = st.select_slider("Time window (days)", options=[7, 14, 30], value=14, key="analytics_days")
    overview = analytics.overview()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Branches", overview["branches"])
    c2.metric("Messages", overview["messages"])
    c3.metric("Unread messages", overview["unread"])
    c4.metric("Urgent messages", overview["urgent"])

    c5, c6, c7 = st.columns(3)
    c5.metric("Locked accounts now", overview["locked_now"])
    c6.metric("Failed logins (24h)", overview["failed_logins_24h"])
    c7.metric("Branches with 2FA", f"{overview['branches_with_2fa']} / {overview['branches']}")

    left, right = st.columns(2)

    with left:
        st.markdown("##### Messages per day")
        st.bar_chart(_series_frame(analytics.messages_per_day(days), "Messages"))

        st.markdown("##### Messages per branch")
        per_branch = analytics.messages_per_branch()
        if per_branch:
            st.bar_chart(pd.DataFrame(per_branch).set_index("Branch"))
        else:
            st.info("No branches yet.")

    with right:
        st.markdown("##### Failed sign-ins per day")
        st.line_chart(_series_frame(analytics.failed_logins_per_day(days), "Failed sign-ins"))

        st.markdown("##### Account lockouts per day")
        st.bar_chart(_series_frame(analytics.lockouts_per_day(days), "Lockouts"))

    st.markdown("##### Messages by priority")
    st.bar_chart(pd.DataFrame(analytics.priority_breakdown()).set_index("Priority"))


def render_admin_alerts():
    st.markdown("#### Suspicious Activity Alerts")
    st.caption(
        "Rules checked: repeated lockouts, failed-login spikes, repeated administrator "
        "failures, message flooding, off-hours administrator sign-ins, administrators without 2FA, "
        "and audit-log tampering."
    )

    found = alert_engine.evaluate_alerts()

    if not found:
        st.success("No suspicious activity detected.")
    else:
        counts = {level: sum(1 for a in found if a.severity == level) for level in ("HIGH", "MEDIUM", "LOW")}
        c1, c2, c3 = st.columns(3)
        c1.metric("High", counts["HIGH"])
        c2.metric("Medium", counts["MEDIUM"])
        c3.metric("Low", counts["LOW"])

        kinds = {"HIGH": "danger", "MEDIUM": "warning", "LOW": "neutral"}
        for item in found:
            with st.container(border=True):
                st.markdown(
                    f"{badge(item.severity, kinds[item.severity])} &nbsp; **{html.escape(item.title)}**",
                    unsafe_allow_html=True,
                )
                st.caption(item.detail)

    st.download_button(
        "\u2B07\uFE0F Download alerts (CSV)",
        data=reports.alerts_report(found),
        file_name=f"alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        key="download_alerts",
    )


def render_admin_security_center(admin_id):
    # ---------------- audit log integrity ----------------
    with st.container(border=True):
        st.markdown("#### \U0001F9FE Audit Log Integrity")
        st.caption(
            "Every log entry is chained to the previous one with an HMAC. Editing, deleting or "
            "inserting rows directly in the database breaks the chain."
        )

        if st.button("Verify log integrity", key="verify_audit", use_container_width=True):
            results = verify_all()
            all_ok = all(r["ok"] for r in results)

            log_admin_activity(
                admin_id, "AUDIT_VERIFIED",
                "Audit log integrity verified: " + ("no problems found" if all_ok else "PROBLEMS FOUND"),
                now_str(),
            )

            for result in results:
                if result["ok"]:
                    st.success(f"{result['table']}: {result['checked']} entries verified \u2014 chain intact.")
                else:
                    st.error(f"{result['table']}: tampering detected "
                             f"(first bad entry: {result['first_bad_log_id']}).")
                    for problem in result["problems"][:10]:
                        st.caption(f"\u2022 {problem}")

    # ---------------- encryption keys ----------------
    with st.container(border=True):
        st.markdown("#### \U0001F5DD\uFE0F Encryption Keys")
        status = key_status()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Active key version", status["active_key_id"])
        c2.metric("Key versions", len(status["key_ids"]))
        c3.metric("Messages", status["total_messages"])
        c4.metric("Need re-encryption", status["needs_reencryption"])

        if status["messages_by_key"]:
            st.dataframe(
                [{"Key version": k, "Messages": v} for k, v in sorted(status["messages_by_key"].items())],
                use_container_width=True, hide_index=True,
            )

        st.warning("Back up the files in the config/ folder. Messages cannot be decrypted without their key version.")

        col_a, col_b = st.columns(2)

        with col_a:
            confirm_rotate = st.checkbox("I understand a new key version will be created", key=nk("confirm_rotate"))
            if st.button("Rotate encryption key", key=nk("rotate_key"), disabled=not confirm_rotate,
                         use_container_width=True):
                new_id = rotate_key(admin_id)
                bump_nonce()          # un-ticks the confirmation box again
                flash("success", f"Key version {new_id} is now active. New messages use it automatically.")
                st.rerun()

        with col_b:
            if st.button("Re-encrypt messages with active key", key="reencrypt",
                         disabled=status["needs_reencryption"] == 0, use_container_width=True):
                outcome = reencrypt_all_messages(admin_id)
                text = f"Re-encrypted {outcome['reencrypted']} message(s)."
                if outcome["skipped"]:
                    text += f" Skipped damaged message(s): {outcome['skipped']}."
                flash("success", text)
                st.rerun()

    # ---------------- account recovery ----------------
    with st.container(border=True):
        st.markdown("#### \U0001F6DF Account Recovery")
        st.caption(
            "Forgot password: Issue temporary password. Lost authenticator phone: Reset 2FA. "
            "Password may be exposed: Require password change."
        )

        with st.form("recovery_form", clear_on_submit=True):
            account_type = st.radio("Account type", ["Branch", "Administrator"], horizontal=True)
            target_text = st.text_input("Branch code (e.g. SB003) or administrator username").strip()
            col_a, col_b, col_c = st.columns(3)
            temp_pw_clicked = col_a.form_submit_button("Issue temporary password", use_container_width=True)
            reset_2fa_clicked = col_b.form_submit_button("Reset 2FA", use_container_width=True)
            force_pw_clicked = col_c.form_submit_button("Require password change", use_container_width=True)

        if temp_pw_clicked or reset_2fa_clicked or force_pw_clicked:
            target = None

            if target_text == "":
                st.error("Enter a branch code or username.")
            elif account_type == "Branch":
                if not validate_branch_code(target_text.upper()):
                    st.error("Invalid Branch Code.")
                else:
                    branch = get_branch_by_id(int(target_text[2:]))
                    if branch is None:
                        st.error("Branch not found.")
                    else:
                        target = ("branch", branch[0], f"{target_text.upper()} ({branch[1]})")
            else:
                found_admin = get_admin_by_username(target_text)
                if found_admin is None:
                    st.error("Administrator not found.")
                else:
                    target = ("admin", found_admin[0], found_admin[1])

            if target:
                kind, target_id, target_label = target

                if temp_pw_clicked:
                    try:
                        temporary = issue_temporary_password(admin_id, kind, target_id)
                    except ValueError as error:
                        st.error(str(error))
                    else:
                        st.success(f"Temporary password issued for {target_label}.")
                        st.code(temporary, language=None)
                        st.warning(
                            "Shown ONLY ONCE \u2014 it is not stored in readable form and is not in any log. "
                            f"Give it to the user through a safe channel. It works for {TEMP_PASSWORD_HOURS} hours, "
                            "the user must choose a new password at sign-in, and any lockout was cleared. "
                            "If the user also lost their authenticator phone, use Reset 2FA as well."
                        )
                elif reset_2fa_clicked:
                    if two_factor.admin_reset(kind, target_id):
                        log_admin_activity(admin_id, "ADMIN_RESET_2FA",
                                           f"Administrator reset two-factor authentication for {target_label}",
                                           now_str())
                        st.success(f"Two-factor authentication removed for {target_label}.")
                    else:
                        st.info(f"{target_label} does not have two-factor authentication enabled.")
                else:
                    force_password_change(kind, target_id)
                    log_admin_activity(admin_id, "ADMIN_FORCE_PASSWORD_CHANGE",
                                       f"Administrator required a password change for {target_label}",
                                       now_str())
                    st.success(f"{target_label} must choose a new password at the next sign-in.")


# =============================================================
# ADMIN PORTAL — DASHBOARD
# =============================================================

def render_admin_dashboard():
    admin = st.session_state["admin_session"]
    admin_id = admin["admin_id"]

    st.markdown(f"## \U0001F6E1\uFE0F Welcome, {admin['username']}")
    st.caption("Administrator Dashboard")

    if admin.get("must_change_password"):
        st.warning(
            "You must choose a new password before you continue. "
            "If you were given a temporary password, enter it as the current password."
        )
        render_change_password("admin", admin_id, admin["username"])
        if st.button("Sign out", key="forced_admin_logout"):
            end_session("admin", "ADMIN_LOGOUT", "Administrator logged out")
            st.rerun()
        return

    # st.tabs jumps back to the first tab after every rerun, so a keyed
    # radio is used: the chosen section stays selected.
    tab_names = [
        "\U0001F3E6 Branches",
        "\u2709\uFE0F Messages",
        "\U0001F4CB System Activity",
        "\U0001F510 Login Security",
        "\U0001F4CA Analytics",
        "\U0001F6A8 Alerts",
        "\U0001F6E1\uFE0F Security Center",
        "\u2795 Register Admin",
        "\U0001F464 My Account",
        "\U0001F6AA Logout",
    ]
    selected_tab = st.radio("Section", tab_names, horizontal=True,
                            key="admin_section", label_visibility="collapsed")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # --------------------------------------------------
    # BRANCHES
    # --------------------------------------------------
    if selected_tab == tab_names[0]:
        branches = get_all_branches_admin()
        st.markdown(f"#### All Branches ({len(branches)})")

        if not branches:
            st.info("No branches registered.")
        else:
            rows = [
                {
                    "Branch ID": b[0],
                    "Branch Code": branch_code_fmt(b[0]),
                    "Branch Name": b[1],
                    "Registered Date": b[2],
                    "2FA": "ON" if two_factor.is_enabled("branch", b[0]) else "OFF",
                }
                for b in branches
            ]
            st.dataframe(rows, use_container_width=True, hide_index=True)

    # --------------------------------------------------
    # MESSAGES (metadata only — content is never decrypted for admins)
    # --------------------------------------------------
    if selected_tab == tab_names[1]:
        messages = get_all_messages_admin()
        st.markdown(f"#### All Messages ({len(messages)})")
        st.caption("Administrators can view message metadata only. Message content remains encrypted and is never displayed here.")

        if not messages:
            st.info("No messages found.")
        else:
            rows = [
                {
                    "ID": m[0],
                    "From": branch_code_fmt(m[1]),
                    "To": branch_code_fmt(m[2]),
                    "Sent Date": m[3],
                    "Status": "READ" if m[4] == 1 else "UNREAD",
                    "Content": "PROTECTED (AES-256-GCM)",
                }
                for m in messages
            ]
            st.dataframe(rows, use_container_width=True, hide_index=True)

            st.download_button(
                "\u2B07\uFE0F Download message metadata (CSV)",
                data=reports.messages_report(),
                file_name=f"message_metadata_{stamp}.csv",
                mime="text/csv",
                key="download_messages",
            )

    # --------------------------------------------------
    # SYSTEM ACTIVITY
    # --------------------------------------------------
    if selected_tab == tab_names[2]:
        activities = get_all_activities_admin()

        col_a, col_b, col_c = st.columns([2, 3, 2])
        actor_filter = col_a.selectbox("Actor type", ["All", "BRANCH", "ADMIN"], key="act_actor")
        keyword = col_b.text_input("Search type, actor or description", key="act_keyword")
        use_dates = col_c.checkbox("Filter by date", key="act_use_dates")

        date_from = date_to = None
        if use_dates:
            col_d, col_e = st.columns(2)
            date_from = col_d.date_input("From date", value=date.today() - timedelta(days=7), key="act_from")
            date_to = col_e.date_input("To date", value=date.today(), key="act_to")

        needle = keyword.strip().lower()
        filtered = []
        for a in activities:
            if actor_filter != "All" and a[0] != actor_filter:
                continue
            if needle and needle not in f"{a[1]} {a[2]} {a[3]}".lower():
                continue
            if date_from and a[4][:10] < str(date_from):
                continue
            if date_to and a[4][:10] > str(date_to):
                continue
            filtered.append(a)

        st.markdown(f"#### System Activity ({len(filtered)} of {len(activities)})")

        if not filtered:
            st.info("No activity records found.")
        else:
            rows = [
                {"Type": a[0], "Actor": a[1], "Activity": a[2], "Description": a[3], "Date & Time": a[4]}
                for a in filtered
            ]
            st.dataframe(rows, use_container_width=True, hide_index=True)

        st.download_button(
            "\u2B07\uFE0F Download activity report (CSV)",
            data=reports.activity_report(date_from, date_to),
            file_name=f"activity_report_{stamp}.csv",
            mime="text/csv",
            key="download_activity",
        )

    # --------------------------------------------------
    # LOGIN SECURITY
    # --------------------------------------------------
    if selected_tab == tab_names[3]:
        st.markdown("#### Branch Login Security")

        branch_records = get_all_login_security_admin()
        current_time = datetime.now()

        if not branch_records:
            st.info("No branch security records found.")
        else:
            rows = []
            for (bid, failed_attempts, locked_until) in branch_records:
                locked = False
                if locked_until is not None:
                    try:
                        lock_time = datetime.strptime(locked_until, DATETIME_FORMAT)
                        locked = current_time < lock_time
                    except ValueError:
                        locked = False
                rows.append({
                    "Branch": branch_code_fmt(bid),
                    "Failed Attempts": failed_attempts,
                    "Status": "LOCKED" if locked else "NOT LOCKED",
                    "Locked Until": locked_until if locked else "-",
                })
            st.dataframe(rows, use_container_width=True, hide_index=True)

            st.download_button(
                "\u2B07\uFE0F Download login security (CSV)",
                data=reports.login_security_report(),
                file_name=f"login_security_{stamp}.csv",
                mime="text/csv",
                key="download_login_security",
            )

        st.markdown("##### Unlock / Reset a Branch")

        with st.form("branch_security_form", clear_on_submit=True):
            branch_code_target = st.text_input("Branch Code", placeholder="e.g. SB003").strip().upper()
            col_a, col_b = st.columns(2)
            unlock_clicked = col_a.form_submit_button("Unlock Account", use_container_width=True)
            reset_clicked = col_b.form_submit_button("Reset Failed Attempts", use_container_width=True)

        if unlock_clicked or reset_clicked:
            valid = (
                branch_code_target.startswith("SB")
                and len(branch_code_target) == 5
                and branch_code_target[2:].isdigit()
            )

            if not valid:
                st.error("Invalid Branch Code.")
            else:
                target_id = int(branch_code_target[2:])
                target_branch = get_branch_by_id(target_id)

                if target_branch is None:
                    st.error("Branch not found.")
                else:
                    target_name = target_branch[1]
                    success = reset_branch_login_security(target_id)

                    if success:
                        action = "ADMIN_UNLOCK_BRANCH" if unlock_clicked else "ADMIN_RESET_BRANCH_ATTEMPTS"
                        verb = "unlocked" if unlock_clicked else "reset failed login attempts for"
                        log_admin_activity(
                            admin_id, action,
                            f"Administrator {verb} branch {branch_code_target} ({target_name})",
                            now_str(),
                        )
                        st.success(f"Branch {branch_code_target} ({target_name}) \u2014 failed attempts reset to 0, lock status: NOT LOCKED.")
                    else:
                        st.error("Unable to update branch security record.")

        st.markdown("---")
        st.markdown("#### Administrator Login Security")

        admin_records = get_all_admin_login_security_details()

        if not admin_records:
            st.info("No administrator security records found.")
        else:
            rows = []
            for (aid, uname, failed_attempts, locked_until) in admin_records:
                locked = False
                if locked_until is not None:
                    try:
                        lock_time = datetime.strptime(locked_until, DATETIME_FORMAT)
                        locked = current_time < lock_time
                    except ValueError:
                        locked = False
                rows.append({
                    "Username": uname,
                    "Failed Attempts": failed_attempts,
                    "Status": "LOCKED" if locked else "NOT LOCKED",
                    "Locked Until": locked_until if locked else "-",
                })
            st.dataframe(rows, use_container_width=True, hide_index=True)

        st.markdown("##### Unlock / Reset an Administrator")

        with st.form("admin_security_form", clear_on_submit=True):
            username_target = st.text_input("Admin Username").strip()
            col_a, col_b = st.columns(2)
            unlock_admin_clicked = col_a.form_submit_button("Unlock Account", use_container_width=True)
            reset_admin_clicked = col_b.form_submit_button("Reset Failed Attempts", use_container_width=True)

        if unlock_admin_clicked or reset_admin_clicked:
            if username_target == "":
                st.error("Username cannot be empty.")
            else:
                target_admin = get_admin_by_username(username_target)

                if target_admin is None:
                    st.error("Administrator not found.")
                else:
                    target_admin_id, target_username = target_admin[0], target_admin[1]
                    success = reset_admin_login_security(target_admin_id)

                    if success:
                        action = "ADMIN_UNLOCK_ADMIN" if unlock_admin_clicked else "ADMIN_RESET_ADMIN_ATTEMPTS"
                        verb = "unlocked account" if unlock_admin_clicked else "reset failed login attempts for account"
                        log_admin_activity(
                            admin_id, action,
                            f"Administrator {verb} '{target_username}'",
                            now_str(),
                        )
                        st.success(f"Administrator '{target_username}' \u2014 failed attempts reset to 0, lock status: NOT LOCKED.")
                    else:
                        st.error("Unable to update administrator security record.")

    # --------------------------------------------------
    # ANALYTICS / ALERTS / SECURITY CENTER
    # --------------------------------------------------
    if selected_tab == tab_names[4]:
        render_admin_analytics()

    if selected_tab == tab_names[5]:
        render_admin_alerts()

    if selected_tab == tab_names[6]:
        render_admin_security_center(admin_id)

    # --------------------------------------------------
    # REGISTER NEW ADMIN
    # --------------------------------------------------
    if selected_tab == tab_names[7]:
        with st.container(border=True):
            st.markdown("#### Register a New Administrator")
            st.caption(
                "Password must be at least 10 characters and include an uppercase letter, "
                "a lowercase letter, a digit, and a special character."
            )

            new_username = st.text_input("Username", key=nk("adm_reg_user"))
            new_password = st.text_input("Password", type="password", key=nk("adm_reg_pw"))
            strength_meter(new_password, context_words=(new_username,))
            confirm_password = st.text_input("Confirm Password", type="password", key=nk("adm_reg_confirm"))

            if st.button("Register Administrator", use_container_width=True, key=nk("adm_reg_button")):
                username = new_username.strip()

                if username == "":
                    st.error("Username cannot be empty.")
                elif len(username) < 3:
                    st.error("Username must contain at least 3 characters.")
                elif len(username) > 30:
                    st.error("Username cannot exceed 30 characters.")
                elif not username.replace("_", "").isalnum():
                    st.error("Username can contain only letters, numbers, and underscore.")
                elif admin_exists(username):
                    st.error(f"Admin username '{username}' already exists.")
                elif not validate_admin_password(new_password):
                    st.error(
                        "Password does not meet security requirements: at least 10 characters, "
                        "one uppercase, one lowercase, one digit, and one special character."
                    )
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    password_hash, password_salt = hash_password(new_password)
                    new_admin_id = insert_admin(username, password_hash, password_salt, now_str())
                    log_admin_activity(admin_id, "ADMIN_CREATED", f"Created new administrator '{username}'", now_str())
                    bump_nonce()

                    # Keep the result, then rerun so the input fields come back empty
                    st.session_state["admin_reg_success"] = {"username": username, "id": new_admin_id}
                    st.rerun()

            done = st.session_state.pop("admin_reg_success", None)
            if done:
                st.success(f"Administrator '{done['username']}' created successfully (Admin ID {done['id']}).")

    # --------------------------------------------------
    # MY ACCOUNT
    # --------------------------------------------------
    if selected_tab == tab_names[8]:
        render_two_factor_panel("admin", admin_id, admin["username"])
        render_change_password("admin", admin_id, admin["username"])

    # --------------------------------------------------
    # LOGOUT
    # --------------------------------------------------
    if selected_tab == tab_names[9]:
        with st.container(border=True):
            st.markdown("#### Logout")

            if st.button("Confirm Logout", key="admin_logout_btn"):
                end_session("admin", "ADMIN_LOGOUT", "Administrator logged out")
                flash("success", "Administrator securely logged out.")
                st.rerun()


def render_admin_portal():
    if st.session_state["admin_session"] is None:
        render_admin_auth()
    else:
        render_admin_dashboard()


# =============================================================
# ROUTER
# =============================================================

show_flash()

page = st.session_state["page"]

if page == "home":
    render_home()
elif page == "branch":
    render_branch_portal()
elif page == "admin":
    render_admin_portal()

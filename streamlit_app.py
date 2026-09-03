# =============================================================
# SECURE BANK — BRANCH NETWORK SYSTEM
# Streamlit Frontend
#
# This file is a UI layer only. It does not re-implement any
# security logic — it calls straight into the existing backend:
#   - database/database.py   (all persistence / SQL)
#   - modules/security.py    (PBKDF2 password hashing)
#   - modules/encryption.py  (AES-256-GCM message encryption)
#   - modules/login_security.py        (branch lockout policy)
#   - modules/admin_login_security.py  (admin lockout policy)
#   - modules/register.py / admin_setup.py (password rules)
#   - modules/login.py       (branch code validation)
#
# Run from the project root:
#     streamlit run streamlit_app.py
# =============================================================

import html
import os
import sys
from datetime import datetime

import streamlit as st
from cryptography.exceptions import InvalidTag

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
    get_branch_by_code,
    get_branch_by_id,
    get_branch_profile,
    save_message,
    get_message_by_id,
    get_messages_for_branch,
    mark_message_as_read,
    get_sent_messages_for_branch,
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

from modules.security import hash_password, verify_password
from modules.encryption import encrypt_message, decrypt_message
from modules.register import validate_password
from modules.admin_setup import validate_admin_password
from modules.login import validate_branch_code
from modules.login_security import (
    check_login_lock,
    get_lock_remaining_time,
    record_failed_attempt,
    reset_login_attempts,
)
from modules.admin_login_security import (
    check_admin_login_lock,
    get_admin_lock_remaining_time,
    record_admin_failed_attempt,
    reset_admin_login_attempts,
)

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

:root{
    --sb-navy-950:#070c17;
    --sb-navy-900:#0a1223;
    --sb-navy-800:#0f1b32;
    --sb-navy-700:#152444;
    --sb-navy-600:#1c2f56;
    --sb-gold:#d4af37;
    --sb-gold-soft:#e9cf7a;
    --sb-text:#eef1f8;
    --sb-text-dim:#9fb0cc;
    --sb-green:#3ecf8e;
    --sb-red:#ef6461;
    --sb-amber:#f2b134;
}

html, body, [class*="css"]  { font-family:'Inter', sans-serif; }

.stApp {
    background:
        radial-gradient(1200px 500px at 10% -10%, #142549 0%, transparent 60%),
        radial-gradient(1000px 600px at 110% 10%, #16264a 0%, transparent 55%),
        linear-gradient(180deg, var(--sb-navy-950) 0%, var(--sb-navy-900) 100%);
    color: var(--sb-text);
}

h1, h2, h3 { font-family:'Playfair Display', serif !important; letter-spacing:.3px; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, var(--sb-navy-950) 0%, #0c1730 100%);
    border-right: 1px solid rgba(212,175,55,0.18);
}
section[data-testid="stSidebar"] * { color: var(--sb-text) !important; }

/* Cards */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: linear-gradient(180deg, rgba(21,36,68,0.65) 0%, rgba(15,27,50,0.65) 100%);
    border: 1px solid rgba(212,175,55,0.22) !important;
    border-radius: 16px !important;
    box-shadow: 0 8px 30px rgba(0,0,0,0.35);
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
    box-shadow: 0 4px 14px rgba(212,175,55,0.25);
}
.stButton>button:hover, .stFormSubmitButton>button:hover {
    transform: translateY(-1px);
    box-shadow: 0 8px 20px rgba(212,175,55,0.35);
    color: #1a1204;
}
.stButton>button[kind="secondary"]{
    background: transparent;
    color: var(--sb-gold-soft) !important;
    border: 1px solid rgba(212,175,55,0.5);
    box-shadow:none;
}

/* Inputs */
.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div {
    background: rgba(7,12,23,0.65) !important;
    color: var(--sb-text) !important;
    border: 1px solid rgba(159,176,204,0.25) !important;
    border-radius: 10px !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid rgba(212,175,55,0.2); }
.stTabs [data-baseweb="tab"] {
    color: var(--sb-text-dim);
    font-weight: 600;
    padding: 10px 18px;
}
.stTabs [aria-selected="true"] {
    color: var(--sb-gold-soft) !important;
    border-bottom: 2px solid var(--sb-gold) !important;
}

/* Hero */
.sb-hero {
    padding: 46px 42px;
    border-radius: 22px;
    background: linear-gradient(135deg, rgba(21,36,68,0.9) 0%, rgba(10,18,35,0.9) 100%);
    border: 1px solid rgba(212,175,55,0.28);
    box-shadow: 0 20px 60px rgba(0,0,0,0.45);
    margin-bottom: 28px;
}
.sb-eyebrow {
    display:inline-block;
    letter-spacing: 3px;
    font-size: 12px;
    color: var(--sb-gold-soft);
    text-transform: uppercase;
    border: 1px solid rgba(212,175,55,0.4);
    border-radius: 999px;
    padding: 5px 14px;
    margin-bottom: 16px;
}
.sb-hero h1 { font-size: 44px; margin: 0 0 6px 0; color: var(--sb-text); }
.sb-hero p.sub { color: var(--sb-text-dim); font-size: 17px; max-width: 620px; }

/* Badges */
.sb-badge {
    display:inline-block; padding: 3px 12px; border-radius: 999px;
    font-size: 12px; font-weight: 700; letter-spacing: .4px;
}
.sb-badge-success { background: rgba(62,207,142,0.15); color: var(--sb-green); border:1px solid rgba(62,207,142,0.35);}
.sb-badge-warning  { background: rgba(242,177,52,0.15); color: var(--sb-amber); border:1px solid rgba(242,177,52,0.35);}
.sb-badge-danger  { background: rgba(239,100,97,0.15); color: var(--sb-red); border:1px solid rgba(239,100,97,0.35);}
.sb-badge-neutral { background: rgba(159,176,204,0.15); color: var(--sb-text-dim); border:1px solid rgba(159,176,204,0.3);}

/* Message bubble */
.sb-message-box {
    background: rgba(7,12,23,0.55);
    border: 1px solid rgba(212,175,55,0.25);
    border-radius: 14px;
    padding: 18px 20px;
    font-size: 15.5px;
    line-height: 1.55;
    white-space: pre-wrap;
}

.sb-divider { height:1px; background: linear-gradient(90deg, transparent, rgba(212,175,55,0.4), transparent); margin: 18px 0; border:none;}

.sb-footnote { color: var(--sb-text-dim); font-size: 13px; }

/* Metric-like small stat */
.sb-stat { text-align:center; padding: 10px 0; }
.sb-stat .n { font-family:'Playfair Display', serif; font-size: 30px; color: var(--sb-gold-soft); font-weight:700;}
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
    "branch_read_logged": set(),
    "profile_logged_this_session": False,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def go(page):
    st.session_state["page"] = page


# =============================================================
# SIDEBAR
# =============================================================

with st.sidebar:
    st.markdown(
        "<div style='text-align:center;padding:6px 0 2px 0;'>"
        "<span style='font-size:38px;'>\U0001F3E6</span>"
        "<h2 style='margin:6px 0 0 0;color:#eef1f8;'>SECURE BANK</h2>"
        "<div style='color:#d4af37;letter-spacing:2px;font-size:12px;'>BRANCH NETWORK SYSTEM</div>"
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

    st.markdown("<hr class='sb-divider'/>", unsafe_allow_html=True)
    st.caption("AES-256-GCM encrypted messaging")
    st.caption("PBKDF2-SHA256 (600,000 iterations) password hashing")
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

def render_branch_auth():
    st.markdown("## \U0001F3E6 Branch Portal")
    tab_login, tab_register = st.tabs(["Sign In", "Register New Branch"])

    with tab_login:
        with st.container(border=True):
            st.markdown("#### Branch Sign In")
            with st.form("branch_login_form", clear_on_submit=True):
                branch_code_input = st.text_input("Branch Code", placeholder="e.g. SB001").strip().upper()
                password_input = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Sign In", use_container_width=True)

            if submitted:
                if not validate_branch_code(branch_code_input):
                    st.error("Invalid branch code. Expected format: SB001")
                else:
                    branch = get_branch_by_code(branch_code_input)
                    if branch is None:
                        st.error("Branch does not exist. Please check your branch code.")
                    else:
                        branch_id, branch_name, password_hash, password_salt = branch

                        if check_login_lock(branch_id):
                            remaining = get_lock_remaining_time(branch_id)
                            if remaining > 0:
                                st.error(
                                    f"Account temporarily locked. Too many failed login attempts.\n\n"
                                    f"Try again in approximately {fmt_lock_wait(remaining)}.\n\n"
                                    f"Maximum failed attempts: 3 · Lockout duration: 5 minutes."
                                )
                                st.stop()

                        if password_input == "":
                            st.error("Password cannot be empty.")
                        elif verify_password(password_input, password_hash, password_salt):
                            reset_login_attempts(branch_id)
                            login_time = now_str()
                            st.session_state["branch_session"] = {
                                "branch_id": branch_id,
                                "branch_code": branch_code_input,
                                "branch_name": branch_name,
                                "login_time": login_time,
                            }
                            st.session_state["branch_read_logged"] = set()
                            st.session_state["profile_logged_this_session"] = False
                            log_activity(branch_id, "LOGIN", "Branch logged in", login_time)
                            st.success("Login successful. Loading your dashboard...")
                            st.rerun()
                        else:
                            failed_attempts = record_failed_attempt(branch_id)
                            log_activity(branch_id, "FAILED_LOGIN", "Incorrect password", now_str())
                            if failed_attempts >= 3:
                                st.error(
                                    f"Incorrect password. Failed attempts: {failed_attempts}/3.\n\n"
                                    "Account has been temporarily locked. Please try again after 5 minutes."
                                )
                            else:
                                st.error(
                                    f"Incorrect password. Failed attempts: {failed_attempts}/3. "
                                    f"Remaining attempts: {3 - failed_attempts}."
                                )

    with tab_register:
        with st.container(border=True):
            st.markdown("#### Register a New Branch")
            st.caption(
                "Password must be at least 10 characters and include an uppercase letter, "
                "a lowercase letter, a digit, and a special character."
            )
            with st.form("branch_register_form", clear_on_submit=True):
                branch_name_input = st.text_input("Branch Name", placeholder="e.g. Bangalore")
                new_password = st.text_input("Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")
                submitted = st.form_submit_button("Register Branch", use_container_width=True)

            if submitted:
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
                    created_date = now_str()
                    branch_id = insert_branch(name, password_hash, password_salt, created_date)
                    code = branch_code_fmt(branch_id)
                    st.success("Registration successful!")
                    with st.container(border=True):
                        st.markdown(f"**Branch ID**  \n{branch_id}")
                        st.markdown(f"**Branch Code**  \n`{code}`")
                        st.markdown(f"**Branch Name**  \n{name}")
                    st.info("Save your branch code — you'll need it to sign in.")


# =============================================================
# BRANCH PORTAL — DASHBOARD
# =============================================================

def render_branch_dashboard():
    session = st.session_state["branch_session"]
    branch_id = session["branch_id"]

    st.markdown(f"## \U0001F3E6 Welcome, {session['branch_name']} Branch")
    st.caption(f"Branch Code: `{session['branch_code']}` · Signed in at {session['login_time']}")

    tabs = st.tabs(["\U0001F4E4 Send Message", "\U0001F4E5 Inbox", "\U0001F4EC Sent Messages", "\U0001F464 Profile", "\U0001F4CB Activity History", "\U0001F6AA Logout"])

    # --------------------------------------------------
    # SEND MESSAGE
    # --------------------------------------------------
    with tabs[0]:
        with st.container(border=True):
            st.markdown("#### Send a Secure Message")

            branches = get_all_branches()
            other_branches = [
                (bid, bname, branch_code_fmt(bid))
                for (bid, bname, _created) in branches
                if bid != branch_id
            ]

            if not other_branches:
                st.info("No other branches are available to message yet.")
            else:
                options = {f"{name} ({code})": bid for (bid, name, code) in other_branches}
                with st.form("send_message_form", clear_on_submit=True):
                    receiver_label = st.selectbox("Receiver Branch", list(options.keys()))
                    message_text = st.text_area("Message", max_chars=500, height=140, placeholder="Type your secure message (max 500 characters)...")
                    submitted = st.form_submit_button("Encrypt & Send", use_container_width=True)

                if submitted:
                    if not message_text.strip():
                        st.error("Message cannot be empty.")
                    elif len(message_text) > 500:
                        st.error("Message is too long. Maximum allowed length is 500 characters.")
                    else:
                        receiver_branch_id = options[receiver_label]
                        encrypted_message, nonce = encrypt_message(message_text)
                        sent_date = now_str()
                        message_id = save_message(branch_id, receiver_branch_id, encrypted_message, nonce, sent_date)
                        log_activity(
                            branch_id,
                            "MESSAGE_SENT",
                            f"Message sent to {branch_code_fmt(receiver_branch_id)}",
                            sent_date,
                        )
                        st.success(
                            f"Message #{message_id} sent securely to {receiver_label} at {sent_date}. "
                            "The message was encrypted with AES-256-GCM before being stored."
                        )

    # --------------------------------------------------
    # INBOX
    # --------------------------------------------------
    with tabs[1]:
        messages = get_messages_for_branch(branch_id)
        st.markdown(f"#### Inbox ({len(messages)})")

        if not messages:
            st.info("No messages found.")
        else:
            for msg in messages:
                (message_id, sender_branch_id, receiver_branch_id, encrypted_message, nonce, sent_date, is_read) = msg
                sender = get_branch_by_id(sender_branch_id)
                sender_name = sender[1] if sender else "Unknown"
                status_badge = badge("READ", "neutral") if is_read == 1 else badge("NEW", "success")

                with st.container(border=True):
                    top = st.columns([5, 3, 2])
                    top[0].markdown(f"**#{message_id} · From {sender_name} ({branch_code_fmt(sender_branch_id)})**")
                    top[1].markdown(f"<span class='sb-footnote'>{sent_date}</span>", unsafe_allow_html=True)
                    top[2].markdown(status_badge, unsafe_allow_html=True)

                    if st.button("Decrypt & View", key=f"open_inbox_{message_id}"):
                        try:
                            decrypted = decrypt_message(encrypted_message, nonce)
                        except InvalidTag:
                            st.error("Unable to decrypt this message. It may have been modified or corrupted.")
                        else:
                            st.markdown(f"<div class='sb-message-box'>{html.escape(decrypted)}</div>", unsafe_allow_html=True)

                            if is_read == 0 and message_id not in st.session_state["branch_read_logged"]:
                                updated_rows = mark_message_as_read(message_id, branch_id)
                                if updated_rows == 1:
                                    log_activity(
                                        branch_id,
                                        "MESSAGE_READ",
                                        f"Message read from {branch_code_fmt(sender_branch_id)}",
                                        now_str(),
                                    )
                                    st.session_state["branch_read_logged"].add(message_id)

    # --------------------------------------------------
    # SENT MESSAGES
    # --------------------------------------------------
    with tabs[2]:
        sent = get_sent_messages_for_branch(branch_id)
        st.markdown(f"#### Sent Messages ({len(sent)})")

        if not sent:
            st.info("No sent messages found.")
        else:
            for msg in sent:
                (message_id, sender_branch_id, receiver_branch_id, encrypted_message, nonce, sent_date, is_read) = msg
                receiver = get_branch_by_id(receiver_branch_id)
                receiver_name = receiver[1] if receiver else "Unknown"
                status_badge = badge("READ", "success") if is_read == 1 else badge("UNREAD", "warning")

                with st.container(border=True):
                    top = st.columns([5, 3, 2])
                    top[0].markdown(f"**#{message_id} · To {receiver_name} ({branch_code_fmt(receiver_branch_id)})**")
                    top[1].markdown(f"<span class='sb-footnote'>{sent_date}</span>", unsafe_allow_html=True)
                    top[2].markdown(status_badge, unsafe_allow_html=True)

                    if st.button("Decrypt & View", key=f"open_sent_{message_id}"):
                        try:
                            decrypted = decrypt_message(encrypted_message, nonce)
                        except InvalidTag:
                            st.error("Unable to decrypt this message. It may have been modified or corrupted.")
                        else:
                            st.markdown(f"<div class='sb-message-box'>{html.escape(decrypted)}</div>", unsafe_allow_html=True)

    # --------------------------------------------------
    # PROFILE
    # --------------------------------------------------
    with tabs[3]:
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
                st.markdown("---")
                st.markdown(badge("ACCOUNT ACTIVE", "success") + "&nbsp;&nbsp;" + badge("SECURITY PROTECTED", "success"), unsafe_allow_html=True)

    # --------------------------------------------------
    # ACTIVITY HISTORY
    # --------------------------------------------------
    with tabs[4]:
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
    with tabs[5]:
        with st.container(border=True):
            st.markdown("#### Logout")
            st.write("This will end your secure session. You'll need your branch code and password to sign in again.")
            if st.button("Confirm Logout", key="branch_logout_btn"):
                log_activity(branch_id, "LOGOUT", "Branch logged out", now_str())
                st.session_state["branch_session"] = None
                st.session_state["branch_read_logged"] = set()
                st.session_state["profile_logged_this_session"] = False
                st.success("You have been securely logged out.")
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
    with st.container(border=True):
        st.markdown("#### Administrator Sign In")
        with st.form("admin_login_form", clear_on_submit=True):
            username_input = st.text_input("Username")
            password_input = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)

        if submitted:
            username = username_input.strip()
            if username == "":
                st.error("Username cannot be empty.")
            else:
                admin = get_admin_by_username(username)
                if admin is None:
                    st.error("Invalid username or password.")
                else:
                    admin_id, stored_username, stored_hash, stored_salt = admin

                    if check_admin_login_lock(admin_id):
                        remaining = get_admin_lock_remaining_time(admin_id)
                        st.error(
                            f"Administrator account temporarily locked. Too many failed login attempts.\n\n"
                            f"Try again in approximately {fmt_lock_wait(remaining)}."
                        )
                        st.stop()

                    if password_input == "":
                        st.error("Password cannot be empty.")
                    elif verify_password(password_input, stored_hash, stored_salt):
                        reset_admin_login_attempts(admin_id)
                        st.session_state["admin_session"] = {"admin_id": admin_id, "username": stored_username}
                        log_admin_activity(admin_id, "ADMIN_LOGIN", "Administrator logged in", now_str())
                        st.success("Admin authentication successful. Loading dashboard...")
                        st.rerun()
                    else:
                        failed_attempts = record_admin_failed_attempt(admin_id)
                        log_admin_activity(admin_id, "ADMIN_FAILED_LOGIN", "Incorrect administrator password", now_str())
                        if failed_attempts >= 3:
                            st.error(
                                f"Invalid username or password. Failed attempts: {failed_attempts}/3.\n\n"
                                "Administrator account has been temporarily locked for 5 minutes."
                            )
                        else:
                            st.error(f"Invalid username or password. Failed attempts: {failed_attempts}/3.")

    st.caption("Tip: the seed administrator account is created via modules/admin_setup.py (`python -m modules.admin_setup`).")


# =============================================================
# ADMIN PORTAL — DASHBOARD
# =============================================================

def render_admin_dashboard():
    admin = st.session_state["admin_session"]
    admin_id = admin["admin_id"]

    st.markdown(f"## \U0001F6E1\uFE0F Welcome, {admin['username']}")
    st.caption("Administrator Dashboard")

    tabs = st.tabs([
        "\U0001F3E6 Branches",
        "\u2709\uFE0F Messages",
        "\U0001F4CB System Activity",
        "\U0001F510 Login Security",
        "\u2795 Register Admin",
        "\U0001F6AA Logout",
    ])

    # --------------------------------------------------
    # BRANCHES
    # --------------------------------------------------
    with tabs[0]:
        branches = get_all_branches_admin()
        st.markdown(f"#### All Branches ({len(branches)})")
        if not branches:
            st.info("No branches registered.")
        else:
            rows = [
                {"Branch ID": b[0], "Branch Code": branch_code_fmt(b[0]), "Branch Name": b[1], "Registered Date": b[2]}
                for b in branches
            ]
            st.dataframe(rows, use_container_width=True, hide_index=True)

    # --------------------------------------------------
    # MESSAGES (metadata only — content is never decrypted for admins)
    # --------------------------------------------------
    with tabs[1]:
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

    # --------------------------------------------------
    # SYSTEM ACTIVITY
    # --------------------------------------------------
    with tabs[2]:
        activities = get_all_activities_admin()
        st.markdown(f"#### System Activity ({len(activities)})")
        if not activities:
            st.info("No activity records found.")
        else:
            rows = [
                {"Type": a[0], "Actor": a[1], "Activity": a[2], "Description": a[3], "Date & Time": a[4]}
                for a in activities
            ]
            st.dataframe(rows, use_container_width=True, hide_index=True)

    # --------------------------------------------------
    # LOGIN SECURITY
    # --------------------------------------------------
    with tabs[3]:
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
                        st.success(f"Branch {branch_code_target} ({target_name}) — failed attempts reset to 0, lock status: NOT LOCKED.")
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
                        st.success(f"Administrator '{target_username}' — failed attempts reset to 0, lock status: NOT LOCKED.")
                    else:
                        st.error("Unable to update administrator security record.")

    # --------------------------------------------------
    # REGISTER NEW ADMIN
    # --------------------------------------------------
    with tabs[4]:
        with st.container(border=True):
            st.markdown("#### Register a New Administrator")
            st.caption(
                "Password must be at least 10 characters and include an uppercase letter, "
                "a lowercase letter, a digit, and a special character."
            )
            with st.form("admin_register_form", clear_on_submit=True):
                new_username = st.text_input("Username")
                new_password = st.text_input("Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")
                submitted = st.form_submit_button("Register Administrator", use_container_width=True)

            if submitted:
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
                    created_date = now_str()
                    new_admin_id = insert_admin(username, password_hash, password_salt, created_date)
                    log_admin_activity(admin_id, "ADMIN_CREATED", f"Created new administrator '{username}'", now_str())
                    st.success(f"Administrator '{username}' created successfully (Admin ID {new_admin_id}).")

    # --------------------------------------------------
    # LOGOUT
    # --------------------------------------------------
    with tabs[5]:
        with st.container(border=True):
            st.markdown("#### Logout")
            if st.button("Confirm Logout", key="admin_logout_btn"):
                log_admin_activity(admin_id, "ADMIN_LOGOUT", "Administrator logged out", now_str())
                st.session_state["admin_session"] = None
                st.success("Administrator securely logged out.")
                st.rerun()


def render_admin_portal():
    if st.session_state["admin_session"] is None:
        render_admin_auth()
    else:
        render_admin_dashboard()


# =============================================================
# ROUTER
# =============================================================

page = st.session_state["page"]

if page == "home":
    render_home()
elif page == "branch":
    render_branch_portal()
elif page == "admin":
    render_admin_portal()

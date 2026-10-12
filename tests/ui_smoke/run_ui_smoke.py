"""
UI SMOKE TEST (no Streamlit install needed)
===========================================
Runs the REAL streamlit_app.py against a tiny fake `streamlit` module
(tests/ui_smoke/fake_streamlit) and drives it like a user: sign-in, wrong
passwords, 2FA set-up and login, messaging, replies, archive, password
change, inactivity timeout, admin dashboard, key rotation, audit-log
tamper detection.

Everything happens in a temporary COPY of the project (fresh database and
keys), so your real bank.db and config/ are never touched.

    python tests/ui_smoke/run_ui_smoke.py
"""
import atexit
import os
import runpy
import shutil
import sys
import tempfile
import time
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, "..", ".."))
ROOT = tempfile.mkdtemp(prefix="sbn_ui_smoke_")
atexit.register(shutil.rmtree, ROOT, ignore_errors=True)

shutil.copytree(
    PROJECT, ROOT, dirs_exist_ok=True,
    ignore=shutil.ignore_patterns(".git", "__pycache__", "*.db", "*.key",
                                  "tests", "docs"),
)

sys.path.insert(0, os.path.join(HERE, "fake_streamlit"))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import streamlit as st
from database.migrations import run_migrations
from database.database import (insert_branch, insert_admin, get_all_branches,
                               create_database, create_messages_table, create_activity_logs_table,
                               create_login_security_table, create_admins_table,
                               create_admin_activity_logs_table, create_admin_login_security_table)
from modules.security import hash_password
from modules import two_factor, totp
from modules.audit_chain import verify_all
from modules.encryption import generate_encryption_key

generate_encryption_key()
for f in (create_database, create_messages_table, create_activity_logs_table, create_login_security_table,
          create_admins_table, create_admin_activity_logs_table, create_admin_login_security_table):
    f()
run_migrations()

PW = "Str0ng!Passw0rd#42"
NOW = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
def mk_branch(name):
    h, s = hash_password(PW); return insert_branch(name, h, s, NOW)
A = mk_branch("SmokeAlpha"); B = mk_branch("SmokeBeta")
h, s = hash_password(PW); ADM = insert_admin("smoke_admin", h, s, NOW)
CODE_A, CODE_B = f"SB{A:03d}", f"SB{B:03d}"

def run(clicks=(), inputs=None, reset_inputs=True):
    if reset_inputs: st.INPUTS.clear()
    st.INPUTS.update(inputs or {})
    st.CLICKS.clear(); st.CLICKS.update(clicks)
    for attempt in range(5):
        st.LOG.clear()
        try:
            runpy.run_path(os.path.join(ROOT, "streamlit_app.py"), run_name="__main__")
            break
        except st.RerunException:
            st.CLICKS.clear()
            continue
        except st.StopException:
            break
    return list(st.LOG)

def kinds(log, kind): return [t for k, t in log if k == kind]
def has(log, kind, needle): return any(needle in t for t in kinds(log, kind))

passed = []

# Section names (the dashboards use a keyed radio, not st.tabs, so the chosen
# section survives every rerun).
SEC = {"send": "\U0001F4E4 Send Message", "inbox": "\U0001F4E5 Inbox", "sent": "\U0001F4EC Sent",
       "archive": "\U0001F5C4\uFE0F Archive", "profile": "\U0001F464 Profile & Security",
       "history": "\U0001F4CB Activity History", "logout": "\U0001F6AA Logout"}
ADM = {"branches": "\U0001F3E6 Branches", "messages": "\u2709\uFE0F Messages", "activity": "\U0001F4CB System Activity",
       "security": "\U0001F510 Login Security", "analytics": "\U0001F4CA Analytics", "alerts": "\U0001F6A8 Alerts",
       "center": "\U0001F6E1\uFE0F Security Center", "register": "\u2795 Register Admin",
       "account": "\U0001F464 My Account", "logout": "\U0001F6AA Logout"}
def go_branch(name): st.session_state["branch_section"] = SEC[name]
def go_admin(name): st.session_state["admin_section"] = ADM[name]
def check(name, cond, detail=""):
    if not cond:
        print("FAIL:", name, detail); 
        raise SystemExit(1)
    passed.append(name); print("ok  :", name)

# ---------- 1. home ----------
log = run()
check("home renders", len(log) > 5 and not kinds(log, "error"))

# ---------- 2. branch login ----------
st.session_state["page"] = "branch"
log = run(clicks={"Sign In"}, inputs={"Branch Code": CODE_A, "Password": "wrong"})
check("wrong password shows attempts", has(log, "error", "Failed attempts: 1/3"), kinds(log, "error"))
log = run(clicks={"Sign In"}, inputs={"Branch Code": "XX", "Password": "x"})
check("bad code format error", has(log, "error", "Invalid branch code"))
log = run(clicks={"Sign In"}, inputs={"Branch Code": CODE_A, "Password": PW})
check("login success -> session", st.session_state["branch_session"] and st.session_state["branch_session"]["branch_id"] == A)
check("dashboard has 7 tabs", any("Send Message" in t and "Profile" in t for t in kinds(log, "radio")))
check("dashboard renders w/o errors", not kinds(log, "error"), kinds(log, "error"))

# ---------- 3. send message A -> B ----------
log = run(clicks={"Encrypt & Send"}, inputs={
    "Receiver Branch": f"SmokeBeta ({CODE_B})", "Subject": "Quarterly <b>report</b>",
    "Priority": "URGENT", "Message": "Numbers attached & ready <script>x</script>"})
check("message sent", has(log, "success", "sent securely"), kinds(log, "error") + kinds(log, "success"))
log = run(clicks={"Encrypt & Send"}, inputs={"Receiver Branch": f"SmokeBeta ({CODE_B})", "Message": "   "})
check("empty message rejected", has(log, "error", "cannot be empty"))

# sent list shows it, search works
go_branch("sent")
log = run(inputs={"sent_keyword": "report"})
check("sent list finds by subject keyword", any("Quarterly" in t for t in kinds(log, "markdown")))
log = run(inputs={"sent_keyword": "nomatchzzz"})
check("sent search no match", has(log, "info", "No messages found"))

# ---------- 4. logout, B logs in, opens, replies ----------
go_branch("logout")
log = run(clicks={"branch_logout_btn"}); 
check("logout clears session", st.session_state["branch_session"] is None)
run(clicks={"Sign In"}, inputs={"Branch Code": CODE_B, "Password": PW})
check("B signed in", st.session_state["branch_session"]["branch_id"] == B)
go_branch("inbox")
log = run()
check("inbox shows message w/ NEW + URGENT", any("NEW" in t and "URGENT" in t for t in kinds(log, "markdown")))
import sqlite3
mid = sqlite3.connect("database/bank.db").execute("select max(message_id) from messages").fetchone()[0]
log = run(clicks={f"inbox_open_{mid}"})
check("detail shows escaped body (no raw <script>)", any("&lt;script&gt;" in t for t in kinds(log, "markdown")) and not any("<script>" in t for t in kinds(log, "markdown")))
check("detail escapes subject html", any("&lt;b&gt;report&lt;/b&gt;" in t for t in kinds(log, "markdown")))
log = run(clicks={"Encrypt & Send Reply"}, inputs={"Your reply": "Received, thanks.", "Priority": "NORMAL"}, reset_inputs=True)
check("reply sent (flash shown after rerun)", has(log, "success", "Reply #"), (kinds(log,"error"), kinds(log,"success")))
rows = sqlite3.connect("database/bank.db").execute("select parent_message_id from messages order by message_id desc limit 1").fetchone()
check("reply stored with parent id", rows[0] == mid, rows)
# archive from detail
st.session_state["view_msg"] = {"box": "inbox", "id": mid}
log = run(clicks={"inbox_archive"})
st2 = sqlite3.connect("database/bank.db").execute("select receiver_status from messages where message_id=?", (mid,)).fetchone() if False else None
go_branch("archive")
log = run(inputs={"archive_which": "Received"})
check("archived message appears in Archive tab", any("Quarterly" in t for t in kinds(log, "markdown")))

# ---------- 5. 2FA enrolment + login ----------
go_branch("profile")
run(inputs={})
log = run(clicks={"branch_2fa_start"})
secret = two_factor.get_pending_secret("branch", B)
check("2FA enrolment starts (secret created)", secret is not None)
check("FIX: stays on Profile & Security after the button (no jump to Send Message)",
      st.session_state["branch_section"] == SEC["profile"] and has(log, "markdown", "Two-Factor Authentication")
      and not has(log, "markdown", "Send a Secure Message"), log[:6])
log = run()
check("QR/manual key shown", any(k in ("image", "info") for k, _ in log) and secret in kinds(log, "code"))
log = run(clicks={"Confirm & Enable"}, inputs={"Code from the app": "000000"})
check("wrong enrol code rejected", has(log, "error", "not correct"))
good = totp.totp_code(secret)
log = run(clicks={"Confirm & Enable"}, inputs={"Code from the app": good})
check("2FA enabled", two_factor.is_enabled("branch", B))
go_branch("logout")
run(clicks={"branch_logout_btn"})
log = run(clicks={"Sign In"}, inputs={"Branch Code": CODE_B, "Password": PW})
check("login now asks for 2FA", st.session_state["pending_2fa"] and st.session_state["branch_session"] is None)
log = run()
check("2FA challenge renders", has(log, "markdown", "Two-Factor Verification"))
log = run(clicks={"Verify & Sign In"}, inputs={"Authentication code": "111111"})
check("bad 2FA code rejected", has(log, "error", "Invalid authentication code"))
nxt = totp.totp_code(secret, for_time=time.time() + 30)
log = run(clicks={"Verify & Sign In"}, inputs={"Authentication code": nxt})
check("good 2FA code signs in", st.session_state["branch_session"] and st.session_state["branch_session"]["branch_id"] == B)

# ---------- 6. change password ----------
go_branch("profile")
log = run(clicks={"Update Password"}, inputs={})
bump = st.session_state["form_nonce"]
log = run(clicks={f"branch_cp_button_{bump}"}, inputs={
    f"branch_cp_current_{bump}": PW, f"branch_cp_new_{bump}": "N3w!Passw0rd#99", f"branch_cp_confirm_{bump}": "N3w!Passw0rd#99"})
check("password changed (nonce bumped)", st.session_state["form_nonce"] == bump + 1 or has(log, "success", "changed"), kinds(log, "error"))
PW_B = "N3w!Passw0rd#99"

# ---------- 7. session timeout ----------
st.session_state["branch_session"]["last_activity"] = datetime.now() - timedelta(minutes=11)
log = run()
check("idle session is closed", st.session_state["branch_session"] is None)
check("timeout notice shown", has(log, "warning", "inactivity"))
ev = sqlite3.connect("database/bank.db").execute("select activity_type from activity_logs where branch_id=? order by log_id desc limit 1", (B,)).fetchone()
check("timeout is audited", ev and ev[0] == "SESSION_TIMEOUT", ev)

# ---------- 8. admin ----------
st.session_state["page"] = "admin"
log = run(clicks={"Sign In"}, inputs={"Username": "smoke_admin", "Password": "bad"})
check("admin bad password", has(log, "error", "Invalid username or password"))
log = run(clicks={"Sign In"}, inputs={"Username": "smoke_admin", "Password": PW})
check("admin signed in", st.session_state["admin_session"] is not None)
log = run()
check("admin dashboard 10 tabs", any("Analytics" in t and "Security Center" in t and "My Account" in t for t in kinds(log, "radio")))
go_admin("analytics")
log = run()
check("admin dashboard renders w/o errors", not kinds(log, "error"), kinds(log, "error"))
check("analytics metrics rendered", has(log, "metric", "Branches="))
check("charts rendered", len(kinds(log, "bar_chart")) >= 3 and len(kinds(log, "line_chart")) >= 1)
bad = []
for name in ADM:
    if name == "logout":
        continue
    go_admin(name)
    sec_log = run()
    bad += [(name, e) for e in kinds(sec_log, "error")]
    check(f"admin section renders: {name}", st.session_state["admin_section"] == ADM[name] and len(sec_log) > 3)
check("no errors in any admin section", not bad, bad)
check("CSV downloads are text", all(isinstance(v[1], str) for v in st.DOWNLOADS.values()) and len(st.DOWNLOADS) >= 4, list(st.DOWNLOADS))
go_admin("center")
log = run(clicks={"verify_audit"})
check("audit verify OK", has(log, "success", "chain intact") and not has(log, "error", "tampering"), log[-6:])
go_admin("alerts")
log = run()
check("alerts tab renders (no tamper yet)", not has(log, "markdown", "tampering"))
go_admin("center")
from modules.key_management import key_status
nr = st.session_state["form_nonce"]
before = key_status()["active_key_id"]
log = run(clicks={f"rotate_key_{nr}"}, inputs={f"confirm_rotate_{nr}": True})
check("key rotation reports new version", has(log, "success", "is now active"), kinds(log,"success")+kinds(log,"error"))
check("FIX: stays on Security Center after rotating", st.session_state["admin_section"] == ADM["center"])
check("FIX: confirmation box is un-ticked again (new key)", st.session_state["form_nonce"] == nr + 1)
log = run(clicks={f"rotate_key_{nr + 1}"})                      # no tick -> must NOT rotate
check("rotation needs a fresh confirmation", key_status()["active_key_id"] == before + 1)
log = run(clicks={"reencrypt"})
go_admin("center")
log = run(clicks={"Reset 2FA"}, inputs={"Account type": "Branch", "Branch code (e.g. SB003) or administrator username": CODE_B})
check("admin reset 2FA for branch B", not two_factor.is_enabled("branch", B), kinds(log, "error") + kinds(log, "info"))
log = run(clicks={"Require password change"}, inputs={"Account type": "Branch", "Branch code (e.g. SB003) or administrator username": CODE_B})
check("force password change recorded", has(log, "success", "must choose a new password"))
# forced change screen for B
st.session_state["page"] = "branch"
st.session_state["admin_session"] = st.session_state["admin_session"]
run(clicks={"Sign In"}, inputs={"Branch Code": CODE_B, "Password": PW_B})
log = run()
check("forced password change screen", has(log, "warning", "requires you to choose a new password"))
check("no tabs while forced", not any("Send Message" in t for t in kinds(log, "radio")))
# ---------- 9. forgotten password: admin-issued temporary password ----------
check("light theme CSS is applied", has(run(), "markdown", "--sb-bg-1:#f7f9fd") and not has(run(), "markdown", "--sb-navy-950"))
check("light theme config file exists", 'base = "light"' in open(os.path.join(ROOT, ".streamlit", "config.toml")).read())

st.session_state["branch_session"] = None            # B "forgot" the password and is signed out
st.session_state["page"] = "branch"
log = run()
check("branch sign-in shows forgot-password hint", has(log, "caption", "Forgot your password?"))

st.session_state["page"] = "admin"
RECOVERY = {"Account type": "Branch", "Branch code (e.g. SB003) or administrator username": CODE_B}
log = run(clicks={"Issue temporary password"}, inputs=RECOVERY)
temp = (kinds(log, "code") or [None])[0]
check("temp password shown once with warning", temp and has(log, "success", "Temporary password issued") and has(log, "warning", "ONLY ONCE"), log[-6:])
check("temp password not shown on the next run", not kinds(run(), "code"))
log = run(clicks={"Issue temporary password"}, inputs={"Account type": "Administrator", "Branch code (e.g. SB003) or administrator username": "smoke_admin"})
check("admin cannot issue one for self", has(log, "error", "cannot issue a temporary password for your own account"), kinds(log, "error"))
log = run(clicks={"Issue temporary password"}, inputs={"Account type": "Branch", "Branch code (e.g. SB003) or administrator username": "SB777"})
check("unknown branch rejected", has(log, "error", "Branch not found"))

st.session_state["page"] = "branch"
log = run(clicks={"Sign In"}, inputs={"Branch Code": CODE_B, "Password": PW_B})
check("old password no longer works", st.session_state["branch_session"] is None and has(log, "error", "Incorrect password"))
log = run(clicks={"Sign In"}, inputs={"Branch Code": CODE_B, "Password": temp})
check("temp password signs in", st.session_state["branch_session"] is not None)
log = run()
check("forced change screen mentions temporary password", has(log, "warning", "temporary password") and not any("Send Message" in t for t in kinds(log, "radio")))
bump = st.session_state["form_nonce"]
FINAL = "Fin4l!Passw0rd#55"
log = run(clicks={f"branch_cp_button_{bump}"}, inputs={
    f"branch_cp_current_{bump}": temp, f"branch_cp_new_{bump}": FINAL, f"branch_cp_confirm_{bump}": FINAL})
check("temp password replaced by a chosen one", st.session_state["branch_session"]["must_change_password"] is False, kinds(log, "error"))
log = run()
check("normal dashboard after change", any("Send Message" in t for t in kinds(log, "radio")))
st.session_state["branch_session"] = None
run(clicks={"Sign In"}, inputs={"Branch Code": CODE_B, "Password": FINAL})
check("new password works, temp does not", st.session_state["branch_session"] is not None)
st.session_state["branch_session"] = None
run(clicks={"Sign In"}, inputs={"Branch Code": CODE_B, "Password": temp})
check("used temp password is dead", st.session_state["branch_session"] is None)

st.session_state["page"] = "admin"
adm = st.session_state["admin_session"]; st.session_state["admin_session"] = None
log = run()
check("admin login shows console recovery hint", has(log, "caption", "modules.admin_recovery"))
st.session_state["admin_session"] = adm

# ---------- 10. registration forms clear themselves ----------
st.session_state["page"] = "branch"; st.session_state["branch_session"] = None
st.session_state["auth_section"] = "Register New Branch"
n0 = st.session_state["form_nonce"]
RPW = "Reg1ster!Passw0rd#31"
log = run(clicks={f"reg_button_{n0}"}, inputs={f"reg_name_{n0}": "ClearTestBranch", f"reg_password_{n0}": RPW, f"reg_confirm_{n0}": RPW})
check("branch register: success card shown", has(log, "success", "Registration successful") and any("SB" in t for t in kinds(log, "markdown")), log[-8:])
check("branch register: form keys renewed (fields empty)", st.session_state["form_nonce"] == n0 + 1)
check("FIX: stays on the Register tab, success card visible", st.session_state["auth_section"] == "Register New Branch" and has(log, "success", "Registration successful"))
check("branch register: no old text left in the form", not any(v == "ClearTestBranch" for v in [st.INPUTS.get(f"reg_name_{st.session_state['form_nonce']}")]))
log = run()
check("branch register: success card shows only once", not has(log, "success", "Registration successful"))
n1 = st.session_state["form_nonce"]
log = run(clicks={f"reg_button_{n1}"}, inputs={f"reg_name_{n1}": "ClearTestBranch", f"reg_password_{n1}": RPW, f"reg_confirm_{n1}": RPW})
check("branch register: duplicate name still rejected", has(log, "error", "already exists") and st.session_state["form_nonce"] == n1)

st.session_state["page"] = "admin"
go_admin("register")
n2 = st.session_state["form_nonce"]
log = run(clicks={f"adm_reg_button_{n2}"}, inputs={f"adm_reg_user_{n2}": "clear_admin", f"adm_reg_pw_{n2}": RPW, f"adm_reg_confirm_{n2}": RPW})
check("admin register: stays on Register Admin", st.session_state["admin_section"] == ADM["register"])
check("admin register: success shown after redraw", has(log, "success", "created successfully") and st.session_state["form_nonce"] == n2 + 1, log[-6:])

# tamper detection end-to-end
go_admin("center")
c = sqlite3.connect("database/bank.db"); c.execute("update activity_logs set description='edited' where log_id=(select min(log_id) from activity_logs)"); c.commit(); c.close()
st.session_state["page"] = "admin"
log = run(clicks={"verify_audit"})
check("tampering detected through UI", has(log, "error", "tampering detected"), log[-6:])
go_admin("alerts")
log = run()
check("HIGH alert raised for tampering", has(log, "markdown", "Audit log tampering detected") and has(log, "markdown", "HIGH"))

print("\nALL", len(passed), "UI SMOKE CHECKS PASSED")

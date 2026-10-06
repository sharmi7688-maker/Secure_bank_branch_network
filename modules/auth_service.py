"""
AUTHENTICATION SERVICE (UI-independent)
=======================================

The complete sign-in decision logic for branches and administrators:

    password  ->  lockout check  ->  (optional) 2FA code  ->  session

Returning plain AuthResult objects keeps the Streamlit file thin and lets
the whole flow be unit-tested without a browser.
"""

from dataclasses import dataclass
from typing import Optional

from database.database import get_branch_by_code, get_admin_by_username
from database import store
from modules import two_factor
from modules.account_lock import (
    MAX_ATTEMPTS, LOCK_MINUTES, clear_failures, lock_remaining,
    log_event, record_failure,
)
from modules.login import validate_branch_code
from modules.security import verify_password
from modules.password_policy import temp_password_expired

# How long the user may take to type the 2FA code after the password step
PENDING_2FA_SECONDS = 300


@dataclass
class AuthResult:
    """
    status:
        OK                 fully signed in
        NEEDS_2FA          password correct, authenticator code required
        INVALID_CODE       branch code format wrong
        NOT_FOUND          unknown branch
        LOCKED             account temporarily locked
        EMPTY_PASSWORD     no password entered
        BAD_PASSWORD       wrong password (or wrong admin username)
        BAD_2FA            wrong authenticator code
        TEMP_EXPIRED       correct temporary password, but its time is over
    """

    status: str
    message: str = ""
    account_id: Optional[int] = None
    account_name: Optional[str] = None
    attempts: int = 0
    remaining_seconds: int = 0
    must_change_password: bool = False

    @property
    def ok(self):
        return self.status == "OK"


def _locked_result(remaining):
    return AuthResult(
        "LOCKED",
        "Account temporarily locked. Too many failed attempts.",
        remaining_seconds=remaining,
    )


def _failure_result(kind, account_id, status, label):
    attempts = record_failure(kind, account_id)
    log_event(
        kind, account_id,
        "FAILED_LOGIN" if status == "BAD_PASSWORD" else "FAILED_2FA",
        label,
    )

    if attempts >= MAX_ATTEMPTS:
        message = (
            f"Failed attempts: {attempts}/{MAX_ATTEMPTS}. The account has "
            f"been temporarily locked for {LOCK_MINUTES} minutes."
        )
    else:
        message = (
            f"Failed attempts: {attempts}/{MAX_ATTEMPTS}. "
            f"Remaining attempts: {MAX_ATTEMPTS - attempts}."
        )

    return AuthResult(status, message, account_id=account_id,
                      attempts=attempts)


def _expired_result(kind, account_id):
    log_event(kind, account_id, "TEMP_PASSWORD_EXPIRED",
              "Sign-in refused: temporary password has expired")
    return AuthResult(
        "TEMP_EXPIRED",
        "Your temporary password has expired. Ask an administrator to "
        "issue a new one.",
    )


def _finish_login(kind, account_id, name, used_2fa):
    clear_failures(kind, account_id)

    if kind == "branch":
        text = "Branch logged in" + (" (2FA verified)" if used_2fa else "")
        log_event(kind, account_id, "LOGIN", text)
    else:
        text = "Administrator logged in" + (
            " (2FA verified)" if used_2fa else "")
        log_event(kind, account_id, "LOGIN", text)

    return AuthResult(
        "OK", "Login successful.", account_id=account_id,
        account_name=name,
        must_change_password=store.get_must_change_password(kind, account_id),
    )


# ---------------------------------------------------------
# BRANCH
# ---------------------------------------------------------

def authenticate_branch(branch_code, password):
    code = (branch_code or "").strip().upper()

    if not validate_branch_code(code):
        return AuthResult(
            "INVALID_CODE", "Invalid branch code. Expected format: SB001"
        )

    branch = get_branch_by_code(code)
    if branch is None:
        return AuthResult(
            "NOT_FOUND", "Branch does not exist. Please check your branch code."
        )

    branch_id, branch_name, password_hash, password_salt = branch

    remaining = lock_remaining("branch", branch_id)
    if remaining > 0:
        return _locked_result(remaining)

    if not password:
        return AuthResult("EMPTY_PASSWORD", "Password cannot be empty.")

    if not verify_password(password, password_hash, password_salt):
        result = _failure_result(
            "branch", branch_id, "BAD_PASSWORD", "Incorrect password"
        )
        result.message = "Incorrect password. " + result.message
        return result

    if temp_password_expired("branch", branch_id):
        return _expired_result("branch", branch_id)

    if two_factor.is_enabled("branch", branch_id):
        return AuthResult(
            "NEEDS_2FA", "Enter the code from your authenticator app.",
            account_id=branch_id, account_name=branch_name,
        )

    return _finish_login("branch", branch_id, branch_name, used_2fa=False)


def complete_branch_2fa(branch_id, code, branch_name=None, now=None):
    remaining = lock_remaining("branch", branch_id)
    if remaining > 0:
        return _locked_result(remaining)

    if two_factor.verify_login_code("branch", branch_id, code, now=now):
        if branch_name is None:
            credentials = store.get_credentials("branch", branch_id)
            branch_name = credentials[0] if credentials else None
        return _finish_login("branch", branch_id, branch_name, used_2fa=True)

    result = _failure_result(
        "branch", branch_id, "BAD_2FA", "Invalid two-factor code"
    )
    result.message = "Invalid authentication code. " + result.message
    return result


# ---------------------------------------------------------
# ADMINISTRATOR
# ---------------------------------------------------------

def authenticate_admin(username, password):
    username = (username or "").strip()

    if username == "":
        return AuthResult("BAD_PASSWORD", "Username cannot be empty.")

    admin = get_admin_by_username(username)
    if admin is None:
        # Same wording as a wrong password: do not reveal valid usernames
        return AuthResult("BAD_PASSWORD", "Invalid username or password.")

    admin_id, stored_username, password_hash, password_salt = admin

    remaining = lock_remaining("admin", admin_id)
    if remaining > 0:
        return _locked_result(remaining)

    if not password:
        return AuthResult("EMPTY_PASSWORD", "Password cannot be empty.")

    if not verify_password(password, password_hash, password_salt):
        result = _failure_result(
            "admin", admin_id, "BAD_PASSWORD",
            "Incorrect administrator password",
        )
        result.message = "Invalid username or password. " + result.message
        return result

    if temp_password_expired("admin", admin_id):
        return _expired_result("admin", admin_id)

    if two_factor.is_enabled("admin", admin_id):
        return AuthResult(
            "NEEDS_2FA", "Enter the code from your authenticator app.",
            account_id=admin_id, account_name=stored_username,
        )

    return _finish_login("admin", admin_id, stored_username, used_2fa=False)


def complete_admin_2fa(admin_id, code, username=None, now=None):
    remaining = lock_remaining("admin", admin_id)
    if remaining > 0:
        return _locked_result(remaining)

    if two_factor.verify_login_code("admin", admin_id, code, now=now):
        if username is None:
            credentials = store.get_credentials("admin", admin_id)
            username = credentials[0] if credentials else None
        return _finish_login("admin", admin_id, username, used_2fa=True)

    result = _failure_result(
        "admin", admin_id, "BAD_2FA", "Invalid two-factor code"
    )
    result.message = "Invalid authentication code. " + result.message
    return result

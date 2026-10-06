"""
One small interface over the two existing lockout modules
(modules/login_security.py for branches, modules/admin_login_security.py
for administrators). The lockout POLICY itself (3 failures -> 5 minutes)
is unchanged and still lives in those modules.
"""

from datetime import datetime

from database.database import log_activity, log_admin_activity
from modules.login_security import (
    MAX_FAILED_ATTEMPTS,
    LOCKOUT_MINUTES,
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
MAX_ATTEMPTS = MAX_FAILED_ATTEMPTS
LOCK_MINUTES = LOCKOUT_MINUTES


def _check_kind(kind):
    if kind not in ("branch", "admin"):
        raise ValueError("kind must be 'branch' or 'admin'.")


def now_str():
    return datetime.now().strftime(DATETIME_FORMAT)


def log_event(kind, account_id, event, description):
    """Writes to the right audit log. Administrator events are stored with
    an ADMIN_ prefix (matching the existing naming)."""

    _check_kind(kind)
    if kind == "branch":
        log_activity(account_id, event, description, now_str())
    else:
        log_admin_activity(account_id, f"ADMIN_{event}", description, now_str())


def lock_remaining(kind, account_id):
    """Seconds left on an active lock, or 0 when the account is not locked."""

    _check_kind(kind)
    if kind == "branch":
        if check_login_lock(account_id):
            return max(get_lock_remaining_time(account_id), 0)
    else:
        if check_admin_login_lock(account_id):
            return max(get_admin_lock_remaining_time(account_id), 0)
    return 0


def record_failure(kind, account_id):
    """Counts one failed attempt (password OR 2FA code). Returns the new
    count and writes an ACCOUNT_LOCKED event when the limit is reached."""

    _check_kind(kind)
    if kind == "branch":
        attempts = record_failed_attempt(account_id)
    else:
        attempts = record_admin_failed_attempt(account_id)

    if attempts >= MAX_ATTEMPTS:
        log_event(
            kind, account_id, "ACCOUNT_LOCKED",
            f"Account locked for {LOCK_MINUTES} minutes after "
            f"{MAX_ATTEMPTS} failed attempts",
        )

    return attempts


def clear_failures(kind, account_id):
    _check_kind(kind)
    if kind == "branch":
        reset_login_attempts(account_id)
    else:
        reset_admin_login_attempts(account_id)

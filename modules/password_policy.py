"""
PASSWORD STRENGTH METER AND CHANGE-PASSWORD LOGIC
=================================================

The hard rules are the ones the project already had
(modules/register.py::validate_password for branches and
modules/admin_setup.py::validate_admin_password for administrators).
This module adds a strength score for the UI and a safe change flow.
"""

import secrets
from datetime import datetime, timedelta

from database import store
from database.database import log_admin_activity
from modules.account_lock import (
    log_event, lock_remaining, record_failure, clear_failures, now_str,
    MAX_ATTEMPTS, DATETIME_FORMAT,
)
from modules.admin_setup import validate_admin_password
from modules.register import validate_password
from modules.security import hash_password, verify_password

STRENGTH_LABELS = {
    0: "Enter a password",
    1: "Weak",
    2: "Fair",
    3: "Strong",
    4: "Very strong",
}

COMMON_FRAGMENTS = (
    "password", "welcome", "admin", "qwerty", "letmein", "secure",
    "123456", "abcdef", "iloveyou", "bank",
)


def _has_repeats_or_sequences(password):
    lowered = password.lower()
    for i in range(len(lowered) - 2):
        a, b, c = lowered[i], lowered[i + 1], lowered[i + 2]
        if a == b == c:
            return True
        if ord(b) - ord(a) == 1 and ord(c) - ord(b) == 1:
            return True
    return False


def password_strength(password, context_words=()):
    """
    Returns a dict:
        score     0-4
        label     text for the meter
        rules     list of (rule text, passed bool)  -> checklist in the UI
        feedback  list of improvement hints
    """

    password = password or ""

    rules = [
        ("At least 10 characters", len(password) >= 10),
        ("An uppercase letter", any(c.isupper() for c in password)),
        ("A lowercase letter", any(c.islower() for c in password)),
        ("A digit", any(c.isdigit() for c in password)),
        ("A special character", any(not c.isalnum() for c in password)),
    ]
    meets_policy = all(passed for _text, passed in rules)

    feedback = []
    lowered = password.lower()

    common = any(fragment in lowered for fragment in COMMON_FRAGMENTS)
    if common:
        feedback.append("Avoid common words such as 'password' or 'admin'.")

    personal = any(
        len(word) >= 3 and word.lower() in lowered for word in context_words
    )
    if personal:
        feedback.append("Do not include your branch/user name or code.")

    patterned = _has_repeats_or_sequences(password)
    if patterned and password:
        feedback.append("Avoid repeated characters or sequences (aaa, 123).")

    if not password:
        score = 0
    elif not meets_policy or common or personal:
        score = 1
    else:
        score = 2
        if len(password) >= 14 and not patterned:
            score = 3
            if len(set(password)) >= 10 and len(password) >= 16:
                score = 4

    if password and len(password) < 14 and meets_policy:
        feedback.append("Longer passwords (14+ characters) are stronger.")

    return {
        "score": score,
        "label": STRENGTH_LABELS[score],
        "rules": rules,
        "feedback": feedback,
    }


def change_password(kind, account_id, current_password,
                    new_password, confirm_password):
    """
    Changes the password of a branch or administrator.
    Returns (ok, message).

    * The current password must be correct. Wrong attempts count toward
      the normal lockout, so a hijacked session cannot be used to guess it.
    * The new password must satisfy the project's password rules, must be
      different from the old one and must not contain the account name.
    """

    credentials = store.get_credentials(kind, account_id)
    if credentials is None:
        return False, "Account not found."

    name, password_hash, password_salt = credentials

    if lock_remaining(kind, account_id) > 0:
        return False, "Account temporarily locked. Try again later."

    if not current_password:
        return False, "Current password is required."

    if not verify_password(current_password, password_hash, password_salt):
        attempts = record_failure(kind, account_id)
        log_event(kind, account_id, "FAILED_PASSWORD_CHANGE",
                  "Password change rejected: incorrect current password")
        return False, (
            f"Current password is incorrect. "
            f"Failed attempts: {attempts}/{MAX_ATTEMPTS}."
        )

    if new_password != confirm_password:
        return False, "New passwords do not match."

    validator = validate_password if kind == "branch" \
        else validate_admin_password
    if not validator(new_password):
        return False, (
            "New password does not meet the security requirements: at "
            "least 10 characters, one uppercase, one lowercase, one digit, "
            "one special character, and not a common weak password."
        )

    if verify_password(new_password, password_hash, password_salt):
        return False, "New password must be different from the current one."

    if len(name) >= 3 and name.lower() in new_password.lower():
        return False, "New password must not contain the account name."

    new_hash, new_salt = hash_password(new_password)
    store.update_password(kind, account_id, new_hash, new_salt, now_str())
    log_event(kind, account_id, "PASSWORD_CHANGED",
              "Password changed by the account holder")

    return True, "Password changed successfully."


def force_password_change(kind, account_id):
    """Administrator action: the account must choose a new password at its
    next sign-in. (The caller writes the admin audit entry.)"""

    return store.set_must_change_password(kind, account_id, True)


def must_change_password(kind, account_id):
    return store.get_must_change_password(kind, account_id)


# ---------------------------------------------------------
# FORGOTTEN PASSWORD: ADMIN-ISSUED TEMPORARY PASSWORD
# ---------------------------------------------------------
#
# There is no e-mail or SMS in this system, so a forgotten password is
# recovered by an administrator:
#   1. the administrator issues a random temporary password,
#   2. the user signs in with it and MUST choose a new password,
#   3. the temporary password stops working after TEMP_PASSWORD_HOURS.

TEMP_PASSWORD_HOURS = 24
TEMP_PASSWORD_LENGTH = 14

_UPPER = "ABCDEFGHJKLMNPQRSTUVWXYZ"        # no I, O (easy to misread)
_LOWER = "abcdefghijkmnpqrstuvwxyz"        # no l, o
_DIGITS = "23456789"                       # no 0, 1
_SPECIAL = "!@#$%&*?"


def generate_temporary_password(length=TEMP_PASSWORD_LENGTH):
    """Random password that satisfies every project rule. Uses the
    `secrets` module (cryptographically secure randomness)."""

    length = max(length, 12)
    alphabet = _UPPER + _LOWER + _DIGITS + _SPECIAL

    while True:
        chars = [
            secrets.choice(_UPPER), secrets.choice(_LOWER),
            secrets.choice(_DIGITS), secrets.choice(_SPECIAL),
        ]
        chars += [secrets.choice(alphabet) for _ in range(length - 4)]
        secrets.SystemRandom().shuffle(chars)
        candidate = "".join(chars)

        # Reject unlucky draws (sequences, repeats, common words)
        if (validate_password(candidate)
                and validate_admin_password(candidate)
                and password_strength(candidate)["score"] >= 3):
            return candidate


def _account_label(kind, account_id):
    credentials = store.get_credentials(kind, account_id)
    if credentials is None:
        return None
    name = credentials[0]
    return f"SB{account_id:03d} ({name})" if kind == "branch" else name


def _expiry_text(moment):
    return (moment + timedelta(hours=TEMP_PASSWORD_HOURS)).strftime(
        DATETIME_FORMAT)


def issue_temporary_password(admin_id, kind, target_id, now=None):
    """
    Administrator action for a user (branch or administrator) who forgot
    the password.

    * Replaces the password with a random temporary one and returns it.
      The password is NOT stored in clear text and NOT written to any log;
      the caller must show it to the administrator once.
    * The account must choose a new password at next sign-in.
    * Any lockout is cleared. Two-factor authentication (if enabled) stays
      active; use "Reset 2FA" separately if the device is lost too.
    * Both the administrator and the affected account get an audit entry.
    * An administrator cannot issue one for their own account (they are
      signed in and can use Change Password).

    Raises ValueError when the request is not allowed.
    """

    if kind not in store.ACCOUNT_TYPES:
        raise ValueError("Invalid account type.")

    if kind == "admin" and target_id == admin_id:
        raise ValueError(
            "You cannot issue a temporary password for your own account. "
            "Use Change Password instead."
        )

    label = _account_label(kind, target_id)
    if label is None:
        raise ValueError("Account not found.")

    moment = now if now is not None else datetime.now()
    when = moment.strftime(DATETIME_FORMAT)

    temporary = generate_temporary_password()
    new_hash, new_salt = hash_password(temporary)

    store.set_temporary_password(kind, target_id, new_hash, new_salt,
                                 _expiry_text(moment))
    clear_failures(kind, target_id)

    log_admin_activity(
        admin_id, "ADMIN_TEMP_PASSWORD_ISSUED",
        f"Administrator issued a temporary password for {label} "
        f"(valid {TEMP_PASSWORD_HOURS} hours)",
        when,
    )
    log_event(kind, target_id, "TEMP_PASSWORD_ISSUED",
              "Temporary password issued by an administrator")

    return temporary


def temp_password_expired(kind, account_id, now=None):
    """True when a temporary password exists and its time is over."""

    expiry = store.get_temp_password_expiry(kind, account_id)
    if not expiry:
        return False

    try:
        deadline = datetime.strptime(expiry, DATETIME_FORMAT)
    except ValueError:
        return True          # unreadable value: fail closed

    return (now if now is not None else datetime.now()) > deadline


def console_reset_admin_password(username, also_reset_2fa=False, now=None):
    """
    Last-resort recovery for the case where NO other administrator can issue
    a temporary password (for example the only administrator forgot theirs).
    Meant to be run on the server by whoever has file access to the project
    (see modules/admin_recovery.py). Returns the temporary password.
    """

    from database.database import get_admin_by_username
    from modules import two_factor

    admin = get_admin_by_username(username)
    if admin is None:
        raise ValueError("Administrator not found.")

    admin_id, name = admin[0], admin[1]
    moment = now if now is not None else datetime.now()

    temporary = generate_temporary_password()
    new_hash, new_salt = hash_password(temporary)
    store.set_temporary_password("admin", admin_id, new_hash, new_salt,
                                 _expiry_text(moment))
    clear_failures("admin", admin_id)

    text = "Temporary password issued from the server console"
    if also_reset_2fa and two_factor.admin_reset("admin", admin_id):
        text += "; two-factor authentication removed"

    log_admin_activity(admin_id, "ADMIN_CONSOLE_PASSWORD_RESET",
                       f"{text} for '{name}'",
                       moment.strftime(DATETIME_FORMAT))
    return temporary

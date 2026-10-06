"""
TWO-FACTOR AUTHENTICATION (TOTP) FOR BRANCHES AND ADMINISTRATORS
================================================================

* The shared secret is stored ENCRYPTED (AES-256-GCM, bound to the account),
  never in plain text.
* A code can be used only once (replay protection via the last used step).
* Wrong codes count toward the normal 3-strikes lockout.
"""

from database import store
from modules import totp
from modules.account_lock import (
    log_event, lock_remaining, record_failure, now_str,
)
from modules.encryption import encrypt_secret, decrypt_secret
from modules.security import verify_password


def _context(kind, account_id):
    return f"2fa|{kind}|{account_id}"


def _load_secret(record, kind, account_id):
    return decrypt_secret(
        record["secret_enc"], record["nonce"], record["key_id"],
        _context(kind, account_id),
    )


def is_enabled(kind, account_id):
    record = store.get_two_factor(kind, account_id)
    return bool(record and record["enabled"])


def start_enrollment(kind, account_id):
    """Creates a fresh secret (not active until confirmed). Returns it so
    the UI can show the QR code / manual key."""

    secret = totp.generate_secret()
    encrypted, nonce, key_id = encrypt_secret(
        secret, _context(kind, account_id)
    )
    store.save_pending_two_factor(kind, account_id, encrypted, nonce, key_id)
    return secret


def get_pending_secret(kind, account_id):
    """The secret of an enrollment that was started but not confirmed."""

    record = store.get_two_factor(kind, account_id)
    if record is None or record["enabled"]:
        return None
    return _load_secret(record, kind, account_id)


def confirm_enrollment(kind, account_id, code, now=None):
    """Turns 2FA on if `code` matches the pending secret."""

    record = store.get_two_factor(kind, account_id)
    if record is None or record["enabled"]:
        return False

    secret = _load_secret(record, kind, account_id)
    step = totp.verify_totp(secret, code, for_time=now)
    if step is None:
        return False

    store.enable_two_factor(kind, account_id, step, now_str())
    log_event(kind, account_id, "2FA_ENABLED",
              "Two-factor authentication enabled")
    return True


def verify_login_code(kind, account_id, code, now=None):
    """Validates a code for an ENABLED account. Each code works once."""

    record = store.get_two_factor(kind, account_id)
    if record is None or not record["enabled"]:
        return False

    secret = _load_secret(record, kind, account_id)
    step = totp.verify_totp(
        secret, code, for_time=now, min_step=record["last_step"]
    )
    if step is None:
        return False

    return store.consume_totp_step(kind, account_id, step)


def cancel_enrollment(kind, account_id):
    """Discards a pending (unconfirmed) enrollment."""

    record = store.get_two_factor(kind, account_id)
    if record is not None and not record["enabled"]:
        store.delete_two_factor(kind, account_id)


def disable(kind, account_id, password, code, now=None):
    """Turns 2FA off. Requires BOTH the password and a valid current code.
    Returns (ok, message)."""

    if lock_remaining(kind, account_id) > 0:
        return False, "Account temporarily locked. Try again later."

    credentials = store.get_credentials(kind, account_id)
    if credentials is None:
        return False, "Account not found."

    _name, password_hash, password_salt = credentials

    if not password or not verify_password(password, password_hash,
                                           password_salt):
        record_failure(kind, account_id)
        return False, "Incorrect password."

    if not verify_login_code(kind, account_id, code, now=now):
        record_failure(kind, account_id)
        return False, "Invalid or already used authentication code."

    store.delete_two_factor(kind, account_id)
    log_event(kind, account_id, "2FA_DISABLED",
              "Two-factor authentication disabled")
    return True, "Two-factor authentication disabled."


def admin_reset(target_kind, target_id):
    """Removes 2FA for an account whose device was lost (administrator
    action; the caller logs it)."""

    return store.delete_two_factor(target_kind, target_id) > 0

from datetime import datetime, timedelta

from database.database import (
    initialize_admin_login_security,
    get_admin_login_security,
    update_admin_login_security
)


MAX_FAILED_ATTEMPTS = 3
LOCKOUT_MINUTES = 5


def check_admin_login_lock(admin_id):
    """
    Checks whether an administrator account is currently locked.

    Returns:
        True  -> Administrator is locked.
        False -> Administrator is not locked.

    If the lock has expired or contains invalid data,
    the security record is automatically reset.
    """

    initialize_admin_login_security(admin_id)

    result = get_admin_login_security(admin_id)

    if result is None:
        return False

    failed_attempts, locked_until = result

    # --------------------------------------------------
    # NO ACTIVE LOCK
    # --------------------------------------------------

    if locked_until is None:
        return False

    current_time = datetime.now()

    # --------------------------------------------------
    # SAFELY READ LOCK TIME
    # --------------------------------------------------

    try:

        lock_time = datetime.strptime(
            locked_until,
            "%Y-%m-%d %H:%M:%S"
        )

    except (ValueError, TypeError):

        # Invalid lock time should never leave
        # the administrator permanently locked.

        update_admin_login_security(
            admin_id,
            0,
            None
        )

        return False

    # --------------------------------------------------
    # LOCK STILL ACTIVE
    # --------------------------------------------------

    if current_time < lock_time:
        return True

    # --------------------------------------------------
    # LOCK EXPIRED
    # --------------------------------------------------

    update_admin_login_security(
        admin_id,
        0,
        None
    )

    return False


def get_admin_lock_remaining_time(admin_id):
    """
    Returns the remaining administrator lockout time.

    Returns:
        Number of seconds remaining.
        0 if the account is not locked.

    Invalid or expired lock information is automatically
    cleared.
    """

    initialize_admin_login_security(admin_id)

    result = get_admin_login_security(admin_id)

    if result is None:
        return 0

    locked_until = result[1]

    # --------------------------------------------------
    # NO ACTIVE LOCK
    # --------------------------------------------------

    if locked_until is None:
        return 0

    current_time = datetime.now()

    # --------------------------------------------------
    # SAFELY READ LOCK TIME
    # --------------------------------------------------

    try:

        lock_time = datetime.strptime(
            locked_until,
            "%Y-%m-%d %H:%M:%S"
        )

    except (ValueError, TypeError):

        update_admin_login_security(
            admin_id,
            0,
            None
        )

        return 0

    # --------------------------------------------------
    # CALCULATE REMAINING TIME
    # --------------------------------------------------

    remaining_time = lock_time - current_time

    remaining_seconds = int(
        remaining_time.total_seconds()
    )

    # --------------------------------------------------
    # LOCK EXPIRED
    # --------------------------------------------------

    if remaining_seconds <= 0:

        update_admin_login_security(
            admin_id,
            0,
            None
        )

        return 0

    return remaining_seconds


def record_admin_failed_attempt(admin_id):
    """
    Records one failed administrator login attempt.

    After three failed attempts, the administrator
    account is temporarily locked for five minutes.

    Returns:
        Current number of failed attempts.
    """

    initialize_admin_login_security(admin_id)

    result = get_admin_login_security(admin_id)

    if result is None:

        failed_attempts = 0

    else:

        failed_attempts = result[0]

    # Increase failed-attempt counter
    failed_attempts += 1

    # --------------------------------------------------
    # PREVENT COUNTER FROM EXCEEDING MAXIMUM
    # --------------------------------------------------

    if failed_attempts > MAX_FAILED_ATTEMPTS:

        failed_attempts = MAX_FAILED_ATTEMPTS

    # --------------------------------------------------
    # MAXIMUM ATTEMPTS REACHED
    # --------------------------------------------------

    if failed_attempts >= MAX_FAILED_ATTEMPTS:

        locked_until = (
            datetime.now()
            + timedelta(minutes=LOCKOUT_MINUTES)
        ).strftime("%Y-%m-%d %H:%M:%S")

        update_admin_login_security(
            admin_id,
            failed_attempts,
            locked_until
        )

    # --------------------------------------------------
    # ATTEMPTS BELOW MAXIMUM
    # --------------------------------------------------

    else:

        update_admin_login_security(
            admin_id,
            failed_attempts,
            None
        )

    return failed_attempts


def reset_admin_login_attempts(admin_id):
    """
    Resets administrator failed-login attempts
    after successful authentication.
    """

    initialize_admin_login_security(admin_id)

    update_admin_login_security(
        admin_id,
        0,
        None
    )
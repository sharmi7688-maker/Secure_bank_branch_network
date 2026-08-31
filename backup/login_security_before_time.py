import sqlite3
from datetime import datetime, timedelta


DATABASE_PATH = "database/bank.db"

MAX_FAILED_ATTEMPTS = 3
LOCKOUT_MINUTES = 5


def initialize_login_security(branch_id):
    """
    Creates a login security record for a branch
    if one does not already exist.
    """

    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO login_security (
            branch_id,
            failed_attempts,
            locked_until
        )
        VALUES (?, 0, NULL)
    """, (branch_id,))

    connection.commit()
    connection.close()


def check_login_lock(branch_id):
    """
    Checks whether a branch is currently locked.

    Returns:
        True  -> branch is locked
        False -> branch is not locked
    """

    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT failed_attempts, locked_until
        FROM login_security
        WHERE branch_id = ?
    """, (branch_id,))

    result = cursor.fetchone()

    connection.close()

    if result is None:
        return False

    failed_attempts, locked_until = result

    if locked_until is None:
        return False

    current_time = datetime.now()

    lock_time = datetime.strptime(
        locked_until,
        "%Y-%m-%d %H:%M:%S"
    )

    if current_time < lock_time:
        return True

    return False


def record_failed_attempt(branch_id):
    """
    Records one failed login attempt.

    Returns:
        Current number of failed attempts.
    """

    initialize_login_security(branch_id)

    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT failed_attempts
        FROM login_security
        WHERE branch_id = ?
    """, (branch_id,))

    result = cursor.fetchone()

    failed_attempts = result[0] if result else 0

    failed_attempts += 1

    if failed_attempts >= MAX_FAILED_ATTEMPTS:

        locked_until = (
            datetime.now()
            + timedelta(minutes=LOCKOUT_MINUTES)
        ).strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            UPDATE login_security
            SET failed_attempts = ?,
                locked_until = ?
            WHERE branch_id = ?
        """, (
            failed_attempts,
            locked_until,
            branch_id
        ))

    else:

        cursor.execute("""
            UPDATE login_security
            SET failed_attempts = ?
            WHERE branch_id = ?
        """, (
            failed_attempts,
            branch_id
        ))

    connection.commit()
    connection.close()

    return failed_attempts


def reset_login_attempts(branch_id):
    """
    Resets failed login attempts after
    successful authentication.
    """

    initialize_login_security(branch_id)

    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE login_security
        SET failed_attempts = 0,
            locked_until = NULL
        WHERE branch_id = ?
    """, (branch_id,))

    connection.commit()
    connection.close()
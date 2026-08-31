import sqlite3

from datetime import datetime, timedelta


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

DATABASE_PATH = "database/bank.db"

MAX_FAILED_ATTEMPTS = 3
LOCKOUT_MINUTES = 5

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


# ---------------------------------------------------------
# DATABASE CONNECTION
# ---------------------------------------------------------

def get_connection():
    """
    Creates and returns a connection to the database.
    """

    return sqlite3.connect(
        DATABASE_PATH
    )


# ---------------------------------------------------------
# INITIALIZE LOGIN SECURITY
# ---------------------------------------------------------

def initialize_login_security(branch_id):
    """
    Creates a login-security record for a branch
    if one does not already exist.
    """

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT OR IGNORE INTO login_security (
                branch_id,
                failed_attempts,
                locked_until
            )
            VALUES (?, 0, NULL)
            """,
            (branch_id,)
        )

        connection.commit()

    finally:

        connection.close()


# ---------------------------------------------------------
# CHECK LOGIN LOCK
# ---------------------------------------------------------

def check_login_lock(branch_id):
    """
    Checks whether a branch account is currently locked.

    Returns:

        True
            Branch is currently locked.

        False
            Branch is not locked.

    If the lock has expired, the security record
    is automatically reset.
    """

    initialize_login_security(
        branch_id
    )

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                failed_attempts,
                locked_until
            FROM login_security
            WHERE branch_id = ?
            """,
            (branch_id,)
        )

        result = cursor.fetchone()

        if result is None:

            return False

        failed_attempts, locked_until = result

        # -------------------------------------------------
        # NO ACTIVE LOCK
        # -------------------------------------------------

        if locked_until is None:

            return False

        # -------------------------------------------------
        # VALIDATE LOCK TIME
        # -------------------------------------------------

        try:

            lock_time = datetime.strptime(
                locked_until,
                DATETIME_FORMAT
            )

        except (ValueError, TypeError):

            # Invalid lock information should never
            # permanently lock the account.

            cursor.execute(
                """
                UPDATE login_security
                SET
                    failed_attempts = 0,
                    locked_until = NULL
                WHERE branch_id = ?
                """,
                (branch_id,)
            )

            connection.commit()

            return False

        # -------------------------------------------------
        # CHECK ACTIVE LOCK
        # -------------------------------------------------

        current_time = datetime.now()

        if current_time < lock_time:

            return True

        # -------------------------------------------------
        # LOCK EXPIRED
        # -------------------------------------------------

        cursor.execute(
            """
            UPDATE login_security
            SET
                failed_attempts = 0,
                locked_until = NULL
            WHERE branch_id = ?
            """,
            (branch_id,)
        )

        connection.commit()

        return False

    finally:

        connection.close()


# ---------------------------------------------------------
# RECORD FAILED LOGIN ATTEMPT
# ---------------------------------------------------------

def record_failed_attempt(branch_id):
    """
    Records one failed login attempt.

    When MAX_FAILED_ATTEMPTS is reached,
    the account is temporarily locked.

    Returns:
        Current failed-attempt count.
    """

    initialize_login_security(
        branch_id
    )

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT failed_attempts
            FROM login_security
            WHERE branch_id = ?
            """,
            (branch_id,)
        )

        result = cursor.fetchone()

        if result is None:

            failed_attempts = 0

        else:

            failed_attempts = result[0]

        # Add one failed attempt
        failed_attempts += 1

        # Never allow the value to exceed
        # the configured maximum.
        failed_attempts = min(
            failed_attempts,
            MAX_FAILED_ATTEMPTS
        )

        # -------------------------------------------------
        # MAXIMUM ATTEMPTS REACHED
        # -------------------------------------------------

        if failed_attempts >= MAX_FAILED_ATTEMPTS:

            locked_until = (
                datetime.now()
                + timedelta(
                    minutes=LOCKOUT_MINUTES
                )
            ).strftime(
                DATETIME_FORMAT
            )

            cursor.execute(
                """
                UPDATE login_security
                SET
                    failed_attempts = ?,
                    locked_until = ?
                WHERE branch_id = ?
                """,
                (
                    failed_attempts,
                    locked_until,
                    branch_id
                )
            )

        # -------------------------------------------------
        # ACCOUNT NOT LOCKED
        # -------------------------------------------------

        else:

            cursor.execute(
                """
                UPDATE login_security
                SET
                    failed_attempts = ?,
                    locked_until = NULL
                WHERE branch_id = ?
                """,
                (
                    failed_attempts,
                    branch_id
                )
            )

        connection.commit()

        return failed_attempts

    finally:

        connection.close()


# ---------------------------------------------------------
# RESET LOGIN ATTEMPTS
# ---------------------------------------------------------

def reset_login_attempts(branch_id):
    """
    Resets failed login attempts.

    This is called after successful authentication.
    """

    initialize_login_security(
        branch_id
    )

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE login_security
            SET
                failed_attempts = 0,
                locked_until = NULL
            WHERE branch_id = ?
            """,
            (branch_id,)
        )

        connection.commit()

    finally:

        connection.close()


# ---------------------------------------------------------
# GET REMAINING LOCK TIME
# ---------------------------------------------------------

def get_lock_remaining_time(branch_id):
    """
    Returns the number of seconds remaining
    in the current lockout.

    Returns:

        Positive integer
            Number of seconds remaining.

        0
            Account is not locked.

    Expired or invalid locks are automatically reset.
    """

    initialize_login_security(
        branch_id
    )

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT locked_until
            FROM login_security
            WHERE branch_id = ?
            """,
            (branch_id,)
        )

        result = cursor.fetchone()

        if result is None:

            return 0

        locked_until = result[0]

        if locked_until is None:

            return 0

        try:

            lock_time = datetime.strptime(
                locked_until,
                DATETIME_FORMAT
            )

        except (ValueError, TypeError):

            cursor.execute(
                """
                UPDATE login_security
                SET
                    failed_attempts = 0,
                    locked_until = NULL
                WHERE branch_id = ?
                """,
                (branch_id,)
            )

            connection.commit()

            return 0

        current_time = datetime.now()

        remaining_time = (
            lock_time - current_time
        )

        remaining_seconds = int(
            remaining_time.total_seconds()
        )

        # -------------------------------------------------
        # LOCK EXPIRED
        # -------------------------------------------------

        if remaining_seconds <= 0:

            cursor.execute(
                """
                UPDATE login_security
                SET
                    failed_attempts = 0,
                    locked_until = NULL
                WHERE branch_id = ?
                """,
                (branch_id,)
            )

            connection.commit()

            return 0

        return remaining_seconds

    finally:

        connection.close()
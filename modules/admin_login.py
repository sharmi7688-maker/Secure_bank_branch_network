from getpass import getpass
from datetime import datetime

from database.database import (
    get_admin_by_username,
    log_admin_activity
)

from modules.security import verify_password

from modules.admin_login_security import (
    check_admin_login_lock,
    get_admin_lock_remaining_time,
    record_admin_failed_attempt,
    reset_admin_login_attempts
)
from modules.admin_session import create_admin_session

def admin_login():
    """
    Handles administrator authentication.

    Security features:
    - Password verification
    - Failed login tracking
    - Temporary account lockout
    - Login activity logging

    Returns:
        Admin information if login is successful.
        None if login fails.
    """

    print("\n" + "=" * 60)
    print("                 SECURE BANK")
    print("                 ADMIN LOGIN")
    print("=" * 60)

    username = input(
        "Enter Admin Username: "
    ).strip()

    if username == "":

        print("\nUsername cannot be empty.")
        return None

    admin = get_admin_by_username(username)

    if admin is None:

        print("\nInvalid username or password.")
        return None

    (
        admin_id,
        stored_username,
        stored_hash,
        stored_salt
    ) = admin

    # --------------------------------------------------
    # CHECK ADMIN ACCOUNT LOCK
    # --------------------------------------------------

    if check_admin_login_lock(admin_id):

        remaining_seconds = get_admin_lock_remaining_time(
            admin_id
        )

        remaining_minutes = remaining_seconds // 60

        remaining_seconds_display = (
            remaining_seconds % 60
        )

        print("\n" + "=" * 60)
        print("          ADMIN ACCOUNT TEMPORARILY LOCKED")
        print("=" * 60)

        print("\nToo many failed login attempts.")

        if remaining_minutes > 0:

            print(
                f"\nTry again in approximately "
                f"{remaining_minutes} minute(s) "
                f"and "
                f"{remaining_seconds_display} second(s)."
            )

        else:

            print(
                f"\nTry again in approximately "
                f"{remaining_seconds_display} second(s)."
            )

        print("=" * 60)

        return None

    # --------------------------------------------------
    # PASSWORD
    # --------------------------------------------------

    password = getpass(
        "Enter Admin Password: "
    )

    if password == "":

        print("\nPassword cannot be empty.")
        return None

    # --------------------------------------------------
    # PASSWORD VERIFICATION
    # --------------------------------------------------

    if verify_password(
        password,
        stored_hash,
        stored_salt
    ):

        # Reset failed attempts after successful login
        reset_admin_login_attempts(admin_id)

        # Create authenticated administrator session
        admin = {
            "admin_id": admin_id,
            "username": stored_username
        }

        create_admin_session(admin)

        print("\nAdmin authentication successful.")
        print("Admin session created.")

        current_time = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        log_admin_activity(
            admin_id,
            "ADMIN_LOGIN",
            "Administrator logged in",
            current_time
        )

        print("Admin login activity recorded.")

        return {
            "admin_id": admin_id,
            "username": stored_username
        }

    # --------------------------------------------------
    # FAILED LOGIN
    # --------------------------------------------------

    failed_attempts = record_admin_failed_attempt(
        admin_id
    )

    current_time = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    log_admin_activity(
        admin_id,
        "ADMIN_FAILED_LOGIN",
        "Incorrect administrator password",
        current_time
    )

    print("\nInvalid username or password.")

    print(
        f"Failed login attempts: "
        f"{failed_attempts}/3"
    )

    if failed_attempts >= 3:

        print(
            "\nAdministrator account has been "
            "temporarily locked."
        )

        print("Please try again after 5 minutes.")

    else:

        print(
            "Failed administrator login activity recorded."
        )

    return None


if __name__ == "__main__":

    admin = admin_login()

    if admin is not None:

        print("\nAdmin Login Test: SUCCESS")

        print(
            f"Admin ID : {admin['admin_id']}"
        )

        print(
            f"Username : {admin['username']}"
        )

    else:

        print("\nAdmin Login Test: FAILED")
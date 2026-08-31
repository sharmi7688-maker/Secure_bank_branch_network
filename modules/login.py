from getpass import getpass
from datetime import datetime

from database.database import (
    get_branch_by_code,
    log_activity
)

from modules.security import verify_password

from modules.login_security import (
    check_login_lock,
    get_lock_remaining_time,
    record_failed_attempt,
    reset_login_attempts
)

from modules.session import (
    create_session,
    is_logged_in
)


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


# ---------------------------------------------------------
# BRANCH CODE VALIDATION
# ---------------------------------------------------------

def validate_branch_code(branch_code):
    """
    Validates a Secure Bank branch code.

    Expected format:

        SB001
        SB002
        SB010

    Returns:
        True  -> Valid format
        False -> Invalid format
    """

    if not isinstance(
        branch_code,
        str
    ):
        return False

    branch_code = branch_code.strip().upper()

    # Branch code must contain exactly 5 characters
    if len(branch_code) != 5:

        return False

    # First two characters must be SB
    if branch_code[:2] != "SB":

        return False

    # Remaining three characters must be digits
    if not branch_code[2:].isdigit():

        return False

    # SB000 should not be considered a valid branch code
    if int(branch_code[2:]) <= 0:

        return False

    return True


# ---------------------------------------------------------
# GET CURRENT TIME
# ---------------------------------------------------------

def get_current_time():
    """
    Returns the current date and time
    in the application's standard format.
    """

    return datetime.now().strftime(
        DATETIME_FORMAT
    )


# ---------------------------------------------------------
# BRANCH LOGIN
# ---------------------------------------------------------

def login_branch():
    """
    Handles Secure Bank branch authentication.

    Security flow:

        Branch Code
             ↓
        Branch Exists
             ↓
        Lock Check
             ↓
        Password Verification
             ↓
        Reset Attempts
             ↓
        Create Session
             ↓
        Record Login Activity
    """

    print("\n" + "=" * 60)
    print("                 SECURE BANK BRANCH LOGIN")
    print("=" * 60)

    # -----------------------------------------------------
    # CHECK EXISTING SESSION
    # -----------------------------------------------------

    if is_logged_in():

        print("\nA branch is already logged in.")
        print(
            "Please logout before logging in again."
        )

        return None

    # -----------------------------------------------------
    # GET BRANCH CODE
    # -----------------------------------------------------

    branch_code = input(
        "Enter Branch Code: "
    ).strip().upper()

    # -----------------------------------------------------
    # VALIDATE BRANCH CODE
    # -----------------------------------------------------

    if not validate_branch_code(
        branch_code
    ):

        print("\nError: Invalid branch code.")
        print(
            "Expected format: SB001"
        )

        return None

    # -----------------------------------------------------
    # FIND BRANCH
    # -----------------------------------------------------

    try:

        branch = get_branch_by_code(
            branch_code
        )

    except Exception as error:

        print(
            "\nError: Unable to access branch information."
        )

        print(
            "Please try again later."
        )

        return None

    if branch is None:

        print(
            "\nError: Branch does not exist."
        )

        print(
            "Please check your Branch Code."
        )

        return None

    # -----------------------------------------------------
    # EXTRACT BRANCH INFORMATION
    # -----------------------------------------------------

    try:

        (
            branch_id,
            branch_name,
            password_hash,
            password_salt
        ) = branch

    except (
        TypeError,
        ValueError
    ):

        print(
            "\nError: Invalid branch information."
        )

        return None

    # -----------------------------------------------------
    # CHECK ACCOUNT LOCK
    # -----------------------------------------------------

    try:

        account_locked = check_login_lock(
            branch_id
        )

    except Exception:

        print(
            "\nError: Unable to verify account security."
        )

        print(
            "Please try again later."
        )

        return None

    if account_locked:

        remaining_seconds = (
            get_lock_remaining_time(
                branch_id
            )
        )

        # If the lock expired between the two checks,
        # allow the login process to continue.
        if remaining_seconds > 0:

            remaining_minutes = (
                remaining_seconds // 60
            )

            remaining_seconds_display = (
                remaining_seconds % 60
            )

            print(
                "\n" + "=" * 60
            )

            print(
                "              ACCOUNT TEMPORARILY LOCKED"
            )

            print(
                "=" * 60
            )

            print(
                "\nToo many failed login attempts."
            )

            if remaining_minutes > 0:

                print(
                    f"\nTry again in approximately "
                    f"{remaining_minutes} minute(s) "
                    f"and "
                    f"{remaining_seconds_display} "
                    f"second(s)."
                )

            else:

                print(
                    f"\nTry again in approximately "
                    f"{remaining_seconds} second(s)."
                )

            print(
                "\nMaximum failed attempts: 3"
            )

            print(
                "Temporary lock duration: 5 minutes"
            )

            print(
                "=" * 60
            )

            return None

    # -----------------------------------------------------
    # DISPLAY BRANCH INFORMATION
    # -----------------------------------------------------

    print(
        "\nBranch Found Successfully."
    )

    print(
        "Branch Name :",
        branch_name
    )

    # -----------------------------------------------------
    # GET PASSWORD
    # -----------------------------------------------------

    try:

        password = getpass(
            "Enter Password: "
        )

    except Exception:

        print(
            "\nError: Unable to read password."
        )

        return None

    if password == "":

        print(
            "\nError: Password cannot be empty."
        )

        return None

    # -----------------------------------------------------
    # VERIFY PASSWORD
    # -----------------------------------------------------

    try:

        password_correct = verify_password(
            password,
            password_hash,
            password_salt
        )

    except Exception:

        print(
            "\nError: Unable to verify password."
        )

        return None

    # -----------------------------------------------------
    # SUCCESSFUL LOGIN
    # -----------------------------------------------------

    if password_correct:

        try:

            # Reset previous failed attempts
            reset_login_attempts(
                branch_id
            )

            # Create branch session
            create_session({
                "branch_id": branch_id,
                "branch_code": branch_code,
                "branch_name": branch_name
            })

        except Exception:

            print(
                "\nError: Unable to create secure session."
            )

            print(
                "Login was not completed."
            )

            return None

        current_time = get_current_time()

        # Record successful login
        try:

            log_activity(
                branch_id,
                "LOGIN",
                "Branch logged in",
                current_time
            )

        except Exception:

            print(
                "\nWarning: Login activity "
                "could not be recorded."
            )

        print(
            "\nPassword verified successfully."
        )

        print(
            "Login activity recorded."
        )

        return {
            "branch_id": branch_id,
            "branch_code": branch_code,
            "branch_name": branch_name
        }

    # -----------------------------------------------------
    # FAILED LOGIN
    # -----------------------------------------------------

    try:

        failed_attempts = (
            record_failed_attempt(
                branch_id
            )
        )

    except Exception:

        print(
            "\nError: Unable to update login security."
        )

        return None

    current_time = get_current_time()

    # Record failed login
    try:

        log_activity(
            branch_id,
            "FAILED_LOGIN",
            "Incorrect password",
            current_time
        )

    except Exception:

        print(
            "\nWarning: Failed login activity "
            "could not be recorded."
        )

    print(
        "\nError: Incorrect password."
    )

    print(
        f"Failed login attempts: "
        f"{failed_attempts}/3"
    )

    # -----------------------------------------------------
    # ACCOUNT LOCKED
    # -----------------------------------------------------

    if failed_attempts >= 3:

        print(
            "\nAccount has been temporarily locked."
        )

        print(
            "Please try again after 5 minutes."
        )

    # -----------------------------------------------------
    # ACCOUNT STILL AVAILABLE
    # -----------------------------------------------------

    else:

        remaining_attempts = (
            3 - failed_attempts
        )

        print(
            f"Remaining attempts: "
            f"{remaining_attempts}"
        )

        print(
            "Failed login activity recorded."
        )

    return None


# ---------------------------------------------------------
# DIRECT TEST
# ---------------------------------------------------------

if __name__ == "__main__":

    login_branch()
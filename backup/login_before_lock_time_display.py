from getpass import getpass
from datetime import datetime

from database.database import (
    get_branch_by_code,
    log_activity
)

from modules.security import verify_password
from modules.login_security import (
    check_login_lock,
    record_failed_attempt,
    reset_login_attempts
)


def validate_branch_code(branch_code):
    """
    Validates the Secure Bank branch code format.
    Example: SB001
    """

    if len(branch_code) != 5:
        return False

    if branch_code[:2] != "SB":
        return False

    if not branch_code[2:].isdigit():
        return False

    return True


def login_branch():
    """
    Handles the branch login process.
    """

    print("\n" + "=" * 60)
    print("                 SECURE BANK BRANCH LOGIN")
    print("=" * 60)

    branch_code = input("Enter Branch Code: ").strip()

    if not validate_branch_code(branch_code):
        print("\nError: Invalid branch code.")
        print("Expected format: SB001")
        return

    branch = get_branch_by_code(branch_code)

    if branch is None:
        print("\nError: Branch does not exist.")
        print("Please check your Branch Code.")
        return

    branch_id, branch_name, password_hash, password_salt = branch

    if check_login_lock(branch_id):

        print("\nAccount temporarily locked.")
        print("Too many failed login attempts.")
        print("Please try again after the lockout period.")

        return None

    print("\nBranch Found Successfully.")
    print("Branch Name :", branch_name)

    password = getpass("Enter Password: ")

    if verify_password(password, password_hash, password_salt):

        reset_login_attempts(branch_id)

        print("\nPassword verified successfully.")

        current_time = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        log_activity(
            branch_id,
            "LOGIN",
            "Branch logged in",
            current_time
        )

        print("Login activity recorded.")

        return {
            "branch_id": branch_id,
            "branch_code": branch_code,
            "branch_name": branch_name
        }

    else:

        failed_attempts = record_failed_attempt(
            branch_id
        )

        current_time = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        log_activity(
            branch_id,
            "FAILED_LOGIN",
            "Incorrect password",
            current_time
        )

        print("\nError: Incorrect password.")

        print(
            f"Failed login attempts: "
            f"{failed_attempts}/3"
        )

        if failed_attempts >= 3:

            print("\nAccount has been temporarily locked.")
            print("Please try again after 5 minutes.")

        else:

            print("Failed login activity recorded.")

        return None

if __name__ == "__main__":
    login_branch()
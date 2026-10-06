"""
ADMINISTRATOR RECOVERY (server console)
=======================================

Use this ONLY when no other administrator can issue you a temporary
password (for example you are the only administrator and forgot the
password). It needs access to the project folder on the server, which is
why it is not available from the web interface.

Run from the project root:

    python -m modules.admin_recovery

It prints a random temporary password. Sign in with it and you will be
forced to choose a new password. The action is written to the tamper-evident
audit log (ADMIN_CONSOLE_PASSWORD_RESET).
"""

from database.migrations import run_migrations
from modules.password_policy import (
    TEMP_PASSWORD_HOURS,
    console_reset_admin_password,
)


def main():
    run_migrations()

    print("=" * 56)
    print("  SECURE BANK - ADMINISTRATOR PASSWORD RECOVERY")
    print("=" * 56)

    username = input("Administrator username: ").strip()
    if not username:
        print("Cancelled: no username entered.")
        return

    print("\nThis replaces the password of '%s'." % username)
    if input("Type RESET to continue: ").strip() != "RESET":
        print("Cancelled.")
        return

    also_2fa = input(
        "Also remove two-factor authentication (lost phone)? [y/N]: "
    ).strip().lower() == "y"

    try:
        temporary = console_reset_admin_password(username, also_2fa)
    except ValueError as error:
        print("Error:", error)
        return

    print("\nTemporary password (shown once):")
    print("\n    " + temporary + "\n")
    print("It is valid for %d hours. You must choose a new password at "
          "sign-in." % TEMP_PASSWORD_HOURS)


if __name__ == "__main__":
    main()

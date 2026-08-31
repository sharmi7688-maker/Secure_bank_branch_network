from getpass import getpass
from datetime import datetime

from database.database import (
    insert_admin,
    admin_exists
)

from modules.security import hash_password


def validate_admin_password(password):
    """
    Validates administrator password strength.

    Requirements:
    - At least 10 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """

    if len(password) < 10:
        return False

    if not any(char.isupper() for char in password):
        return False

    if not any(char.islower() for char in password):
        return False

    if not any(char.isdigit() for char in password):
        return False

    if not any(not char.isalnum() for char in password):
        return False

    weak_passwords = {
        "Password@1",
        "Password@123",
        "Welcome@123",
        "Admin@123",
        "Secure@123"
    }

    if password in weak_passwords:
        return False

    return True


def create_admin():

    print("\n" + "=" * 60)
    print("                 SECURE BANK")
    print("                 ADMIN SETUP")
    print("=" * 60)

    # --------------------------------------------------
    # USERNAME
    # --------------------------------------------------

    while True:

        username = input(
            "\nEnter Admin Username: "
        ).strip()

        if username == "":
            print("\nError: Username cannot be empty.")
            continue

        if len(username) < 3:
            print("\nError: Username must contain at least 3 characters.")
            continue

        if len(username) > 30:
            print("\nError: Username cannot exceed 30 characters.")
            continue

        if not username.replace("_", "").isalnum():
            print(
                "\nError: Username can contain only "
                "letters, numbers, and underscore."
            )
            continue

        if admin_exists(username):

            print(
                f"\nError: Admin username '{username}' "
                "already exists."
            )

            return

        break

    print("\nUsername accepted.")

    # --------------------------------------------------
    # PASSWORD
    # --------------------------------------------------

    while True:

        password = getpass(
            "Enter Admin Password: "
        )

        if not validate_admin_password(password):

            print(
                "\nError: Password does not meet "
                "the security requirements."
            )

            print("Password must contain:")
            print("- At least 10 characters")
            print("- At least one uppercase letter")
            print("- At least one lowercase letter")
            print("- At least one number")
            print("- At least one special character")

            continue

        confirm_password = getpass(
            "Confirm Admin Password: "
        )

        if password != confirm_password:

            print("\nError: Passwords do not match.")
            continue

        break

    print("\nPassword confirmed successfully.")

    # --------------------------------------------------
    # PASSWORD HASHING
    # --------------------------------------------------

    password_hash, password_salt = hash_password(
        password
    )

    created_date = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    # --------------------------------------------------
    # STORE ADMIN
    # --------------------------------------------------

    admin_id = insert_admin(
        username,
        password_hash,
        password_salt,
        created_date
    )

    print("\n" + "=" * 60)
    print("             ADMIN REGISTRATION SUCCESSFUL")
    print("=" * 60)

    print(f"Admin ID      : {admin_id}")
    print(f"Username      : {username}")
    print(f"Created Date  : {created_date}")

    print("\nPassword stored securely as a hash.")
    print("The original password is not stored.")

    print("=" * 60)


if __name__ == "__main__":
    create_admin()
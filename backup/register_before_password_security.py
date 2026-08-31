from getpass import getpass
from datetime import datetime

from database.database import insert_branch, branch_exists
from modules.security import hash_password


def validate_password(password):
    """
    Validates the strength of a password.
    Returns True if the password is valid.
    """

    if len(password) < 8:
        return False

    if not any(char.isupper() for char in password):
        return False

    if not any(char.islower() for char in password):
        return False

    if not any(char.isdigit() for char in password):
        return False

    if not any(not char.isalnum() for char in password):
        return False

    return True


def register_branch():
    """
    Handles the branch registration process.
    """

    print("\n" + "=" * 60)
    print("             SECURE BANK BRANCH REGISTRATION")
    print("=" * 60)

    while True:

        branch_name = input("Enter Branch Name: ")

        branch_name = branch_name.strip()

        if branch_name == "":
            print("\nError: Branch name cannot be empty.")
            print("Please try again.\n")
            continue

        if len(branch_name) < 3:
            print("\nError: Branch name must contain at least 3 characters.")
            print("Please try again.\n")
            continue

        if len(branch_name) > 50:
            print("\nError: Branch name cannot exceed 50 characters.")
            print("Please try again.\n")
            continue

        if branch_exists(branch_name):
            print(f"\nError: Branch '{branch_name}' already exists.")
            print("Please enter a different branch name.\n")
            continue

        # Branch name is valid
        break

    print("\nBranch Name Accepted:", branch_name)


    # ----------------------------------------------------------
    # PASSWORD VALIDATION
    # ----------------------------------------------------------

    while True:

        password = getpass("Enter Password: ")

        if not validate_password(password):
            print("\nError: Password does not meet the security requirements.")
            print("Password must contain:")
            print("- At least 8 characters")
            print("- At least one uppercase letter")
            print("- At least one lowercase letter")
            print("- At least one number")
            print("- At least one special character")
            print("Please try again.\n")
            continue

        confirm_password = getpass("Confirm Password: ")

        if password != confirm_password:
            print("\nError: Passwords do not match.")
            print("Please try again.\n")
            continue

        # Password is valid and confirmed
        break

    print("\nPassword confirmed successfully.")
    
    password_hash, password_salt = hash_password(password)

    created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    branch_id = insert_branch(
        branch_name,
        password_hash,
        password_salt,
        created_date
    )

    branch_code = f"SB{branch_id:03d}"

    print("\n" + "=" * 60)
    print("             REGISTRATION SUCCESSFUL")
    print("=" * 60)
    print(f"Branch ID   : {branch_id}")
    print(f"Branch Code : {branch_code}")
    print(f"Branch Name : {branch_name}")
    print("=" * 60)


if __name__ == "__main__":
    register_branch()
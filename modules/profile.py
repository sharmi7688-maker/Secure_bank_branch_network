from datetime import datetime

from database.database import (
    get_branch_profile,
    log_activity
)
from modules.session import (
    require_login,
    get_current_session
)


def show_profile():

    if not require_login():
        return

    current_session = get_current_session()

    if current_session is None:
        print("\nError: Unable to retrieve session.")
        print("Please login again.")
        return

    branch_id = current_session["branch_id"]
    branch_code = current_session["branch_code"]

    profile = get_branch_profile(branch_id)

    if profile is None:

        print("\nUnable to retrieve branch profile.")
        return

    current_time = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    log_activity(
        branch_id,
        "PROFILE_VIEWED",
        "Branch profile viewed",
        current_time
    )

    (
        profile_branch_id,
        branch_name,
        created_date
    ) = profile

    print("\n" + "=" * 60)
    print("                     SECURE BANK")
    print("                   BRANCH PROFILE")
    print("=" * 60)

    print(f"\nBranch ID       : {profile_branch_id}")
    print(f"Branch Code     : {branch_code}")
    print(f"Branch Name     : {branch_name}")
    print(f"Registered Date : {created_date}")

    print("\nAccount Status  : ACTIVE")
    print("Security Status : PROTECTED")

    print("\n" + "=" * 60)

    input("\nPress Enter to return to dashboard...")

if __name__ == "__main__":

    show_profile()

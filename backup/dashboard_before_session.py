from datetime import datetime

from database.database import log_activity
from modules.messaging import messaging_menu
from modules.profile import show_profile
from modules.activity_history import show_activity_history

def show_dashboard(branch):
    """
    Displays the dashboard for the logged-in branch.
    """

    branch_id = branch["branch_id"]
    branch_code = branch["branch_code"]
    branch_name = branch["branch_name"]

    while True:

        print("\n" + "=" * 60)
        print("                     SECURE BANK")
        print("                  BRANCH DASHBOARD")
        print("=" * 60)

        print(f"\nWelcome, {branch_name} Branch")
        print(f"Branch Code : {branch_code}")

        print("\n" + "-" * 60)
        print("1. Secure Messaging")
        print("2. Branch Profile")
        print("3. Activity History")
        print("4. Logout")
        print("-" * 60)

        choice = input("Enter your choice (1-4): ").strip()

        if choice == "1":
            messaging_menu(branch)

        elif choice == "2":
            show_profile(branch)

        elif choice == "3":
            show_activity_history(branch)

        elif choice == "4":
            current_time = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            log_activity(
                branch_id,
                "LOGOUT",
                "Branch logged out",
                current_time
            )

            print("\nLogout activity recorded.")
            print("Logging out...")
            break

        else:
            print("\nInvalid choice. Please select 1-4.")

if __name__ == "__main__":

    test_branch = {
        "branch_id": 1,
        "branch_code": "SB001",
        "branch_name": "Bangalore"
    }

    show_dashboard(test_branch)        
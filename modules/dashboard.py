from datetime import datetime

from database.database import log_activity
from modules.messaging import messaging_menu
from modules.profile import show_profile
from modules.activity_history import show_activity_history
from modules.session import (
    get_current_session,
    is_logged_in,
    destroy_session
)

def show_dashboard():

    if not is_logged_in():

        print("\nError: No active session.")
        print("Please login first.")
        return

    current_session = get_current_session()

    if current_session is None:

        print("\nError: Unable to retrieve session.")
        print("Please login again.")
        return

    branch_id = current_session["branch_id"]
    branch_code = current_session["branch_code"]
    branch_name = current_session["branch_name"]
    login_time = current_session["login_time"]

    while True:

        print("\n" + "=" * 60)
        print("                     SECURE BANK")
        print("                  BRANCH DASHBOARD")
        print("=" * 60)

        print(f"\nWelcome, {branch_name} Branch")
        print(f"Branch Code : {branch_code}")
        print(f"Login Time  : {login_time}")

        print("\n" + "-" * 60)
        print("1. Secure Messaging")
        print("2. Branch Profile")
        print("3. Activity History")
        print("4. Logout")
        print("-" * 60)

        choice = input("Enter your choice (1-4): ").strip()

        if choice == "1":
            messaging_menu(current_session)

        elif choice == "2":
            show_profile()

        elif choice == "3":
            show_activity_history()

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
            destroy_session()
            print("Session destroyed.")
            print("You have been securely logged out.")

            break

        else:
            print("\nInvalid choice. Please select 1-4.")

if __name__ == "__main__":
    show_dashboard()       
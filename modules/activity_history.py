from database.database import get_activities_for_branch
from modules.session import (
    require_login,
    get_current_session
)


def show_activity_history():

    if not require_login():
        return

    current_session = get_current_session()

    if current_session is None:

        print("\nError: Unable to retrieve active session.")
        print("Please login again.")
        return

    # Get branch information from authenticated session
    branch_id = current_session["branch_id"]
    branch_name = current_session["branch_name"]
    branch_code = current_session["branch_code"]

    while True:

        print("\n" + "=" * 70)
        print("                     SECURE BANK")
        print("                  ACTIVITY HISTORY")
        print("=" * 70)

        print(f"\nBranch : {branch_name}")
        print(f"Code   : {branch_code}")

        activities = get_activities_for_branch(
            branch_id
        )

        if len(activities) == 0:

            print("\nNo activity records found.")

            print("\n" + "-" * 60)
            print("1. Refresh")
            print("2. Back")
            print("-" * 60)

            choice = input(
                "Enter your choice (1-2): "
            ).strip()

            if choice == "1":

                print(
                    "\nRefreshing Activity History..."
                )

                continue

            elif choice == "2":

                print("\nReturning...")
                return

            else:

                print("\nInvalid choice.")

                continue

        print("\n" + "-" * 100)

        print(
            f"{'ID':<6}"
            f"{'Activity':<20}"
            f"{'Description':<40}"
            f"{'Date & Time':<24}"
        )

        print("-" * 100)

        for activity in activities:

            (
                log_id,
                activity_branch_id,
                activity_type,
                description,
                activity_date
            ) = activity

            print(
                f"{log_id:<6}"
                f"{activity_type:<20}"
                f"{description:<40}"
                f"{activity_date:<24}"
            )

        print("-" * 100)

        print("\n1. Refresh")
        print("2. Back")

        choice = input(
            "Enter your choice (1-2): "
        ).strip()

        if choice == "1":

            print(
                "\nRefreshing Activity History..."
            )

        elif choice == "2":

            print("\nReturning...")
            return

        else:

            print("\nInvalid choice.")


if __name__ == "__main__":

    

    show_activity_history()
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
        print("1. Send Secure Message")
        print("2. Inbox")
        print("3. Sent Messages")
        print("4. Branch Profile")
        print("5. Activity History")
        print("6. Logout")
        print("-" * 60)

        choice = input("Enter your choice (1-6): ").strip()

        if choice == "1":
            print("\nSend Secure Message - Coming Soon")

        elif choice == "2":
            print("\nInbox - Coming Soon")

        elif choice == "3":
            print("\nSent Messages - Coming Soon")

        elif choice == "4":
            print("\nBranch Profile - Coming Soon")

        elif choice == "5":
            print("\nActivity History - Coming Soon")

        elif choice == "6":
            print("\nLogging out...")
            break

        else:
            print("\nInvalid choice. Please select 1-6.")

if __name__ == "__main__":

    test_branch = {
        "branch_id": 1,
        "branch_code": "SB001",
        "branch_name": "Bangalore"
    }

    show_dashboard(test_branch)        
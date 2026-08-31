from modules.utilities import print_header, clear_screen
from database.database import (
    create_database,
    check_branches_table,
    create_messages_table,
    create_activity_logs_table,
    create_login_security_table
)
from modules.register import register_branch
from modules.login import login_branch
from modules.dashboard import show_dashboard
from modules.admin_login import admin_login

def show_menu():
    print("\nMain Menu")
    print("-" * 60)
    print("1. Register Branch")
    print("2. Login Branch")
    print("3. Admin Login")
    print("4. About Project")
    print("5. Exit")
    print("-" * 60)


def main():

    create_database()
    check_branches_table()

    create_messages_table()
    create_activity_logs_table()
    create_login_security_table()

    while True:

        
        print_header()
        show_menu()

        choice = input("Enter your choice (1-5): ")

        if choice == "1":
            register_branch()

        elif choice == "2":

            logged_in_branch = login_branch()

            if logged_in_branch is not None:
                show_dashboard(logged_in_branch)

        elif choice == "3":

            admin = admin_login()

            if admin is not None:

                print("\nWelcome, Administrator.")
                print("Admin login completed successfully.")

                input("\nPress Enter to return to main menu...")

        elif choice == "4":
            print("\nAbout Project")
            print("-" * 60)
            print("Project : Secure Bank Branch Network")
            print("Bank    : Secure Bank")
            print("Language: Python")
            print("Database: SQLite")
            print("Security: Message Encryption")
            print("-" * 60)

        elif choice == "5":
            print("\nThank you for using Secure Bank.")
            print("Application Closed.")
            break

        else:
            print("\nInvalid Choice! Please try again.\n")


if __name__ == "__main__":
    main()
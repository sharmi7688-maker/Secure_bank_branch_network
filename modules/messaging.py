from modules.send_message import send_secure_message
from modules.inbox import show_inbox
from modules.sent_messages import show_sent_messages
from modules.session import require_login

def messaging_menu(branch):

    if not require_login():
        return

    while True:

        print("\n" + "=" * 60)
        print("                  SECURE MESSAGING")
        print("=" * 60)

        print(f"\nBranch : {branch['branch_name']}")
        print(f"Code   : {branch['branch_code']}")

        print("\n" + "-" * 60)

        print("1. Send Secure Message")
        print("2. Inbox")
        print("3. Sent Messages")
        print("4. Back")

        print("-" * 60)

        choice = input(
            "Enter your choice (1-4): "
        ).strip()

        if choice == "1":

            send_secure_message(branch)

        elif choice == "2":

            show_inbox(branch)

        elif choice == "3":

            show_sent_messages(branch)

        elif choice == "4":

            print("\nReturning to branch dashboard...")
            return

        else:

            print("\nInvalid choice.")
            print("Please enter a number from 1 to 4.")

if __name__ == "__main__":

    test_branch = {
        "branch_id": 1,
        "branch_code": "SB001",
        "branch_name": "Bangalore"
    }

    messaging_menu(test_branch)

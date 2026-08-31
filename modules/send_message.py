from datetime import datetime

from database.database import (
    get_all_branches,
    save_message,
    log_activity
)

from modules.encryption import encrypt_message
from modules.session import require_login, get_current_session


def send_secure_message(branch):

    if not require_login():
        return

    current_branch_id = branch["branch_id"]
    current_branch_name = branch["branch_name"]
    current_branch_code = branch["branch_code"]

    print("\n" + "=" * 60)
    print("                 SEND SECURE MESSAGE")
    print("=" * 60)

    print(f"\nYour Branch : {current_branch_name}")
    print(f"Branch Code : {current_branch_code}")

    branches = get_all_branches()

    print("\nAvailable Branches")
    print("-" * 60)

    available_branches = []

    for branch_id, branch_name, created_date in branches:

        if branch_id != current_branch_id:

            branch_code = f"SB{branch_id:03d}"

            available_branches.append(
                (branch_id, branch_name, branch_code)
            )

    if len(available_branches) == 0:

        print("No other branches are available.")
        print("=" * 60)

        return

    for index, (
        branch_id,
        branch_name,
        branch_code
    ) in enumerate(available_branches, start=1):

        print(
            f"{index}. "
            f"{branch_name} ({branch_code})"
        )

    print("0. Cancel")

    print("-" * 60)

    choice = input("Select receiver: ").strip()

    if choice == "0":

        print("\nMessage cancelled.")
        return

    if not choice.isdigit():

        print("\nInvalid selection.")
        return

    choice_number = int(choice)

    if choice_number < 1 or choice_number > len(available_branches):

        print("\nInvalid receiver selection.")
        return

    selected_branch = available_branches[
        choice_number - 1
    ]

    receiver_branch_id = selected_branch[0]
    receiver_branch_name = selected_branch[1]
    receiver_branch_code = selected_branch[2]

    print("\n" + "-" * 60)
    print("Receiver Selected")
    print("-" * 60)

    print(f"Branch Name : {receiver_branch_name}")
    print(f"Branch Code : {receiver_branch_code}")

    print("-" * 60)

    print("\nEnter your message.")
    print("Maximum 500 characters.")
    print("Type CANCEL to cancel sending.")

    message = input("\nMessage: ")

    if message.strip().upper() == "CANCEL":

        print("\nMessage cancelled.")
        return

    if not message.strip():

        print("\nMessage cannot be empty.")
        return

    if len(message) > 500:

        print("\nMessage is too long.")
        print("Maximum allowed length is 500 characters.")
        return

    print("\n" + "=" * 60)
    print("             MESSAGE READY TO SEND")
    print("=" * 60)

    print(f"\nReceiver : {receiver_branch_name}")
    print(f"Code     : {receiver_branch_code}")

    print("\nMessage validation successful.")
    print("=" * 60)

    print("\nEncrypting message...")

    encrypted_message, nonce = encrypt_message(message)

    sent_date = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    message_id = save_message(
        current_branch_id,
        receiver_branch_id,
        encrypted_message,
        nonce,
        sent_date
    )

    log_activity(
        current_branch_id,
        "MESSAGE_SENT",
        f"Message sent to {receiver_branch_code}",
        sent_date
    )

    print("\n" + "=" * 60)
    print("             MESSAGE SENT SUCCESSFULLY")
    print("=" * 60)

    print(f"\nMessage ID : {message_id}")
    print(
        f"From       : "
        f"{current_branch_name} ({current_branch_code})"
    )
    print(
        f"To         : "
        f"{receiver_branch_name} ({receiver_branch_code})"
    )
    print(f"Time       : {sent_date}")

    print("\nThe message has been encrypted")
    print("and securely stored in the database.")

    print("=" * 60)

if __name__ == "__main__":

    test_branch = {
        "branch_id": 1,
        "branch_code": "SB001",
        "branch_name": "Bangalore"
    }

    send_secure_message(test_branch)    
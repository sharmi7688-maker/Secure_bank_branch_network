from cryptography.exceptions import InvalidTag
from database.database import (
    get_sent_messages_for_branch,
    get_message_by_id,
    get_branch_by_id
)

from modules.encryption import decrypt_message
from modules.session import require_login

def get_branch_code(branch_id):
    return f"SB{branch_id:03d}"

def open_sent_message(branch):

    if not require_login():
        return

    branch_id = branch["branch_id"]

    message_id_input = input(
        "\nEnter Message ID to open: "
    ).strip()

    if not message_id_input.isdigit():

        print("\nInvalid Message ID.")
        return

    message_id = int(message_id_input)

    message = get_message_by_id(message_id)

    if message is None:

        print("\nMessage not found.")
        return

    (
        message_id,
        sender_branch_id,
        receiver_branch_id,
        encrypted_message,
        nonce,
        sent_date,
        is_read
    ) = message

    if sender_branch_id != branch_id:

        print("\nAccess denied.")
        print("This message was not sent by your branch.")
        return

    try:

        decrypted_message = decrypt_message(
            encrypted_message,
            nonce
        )

    except InvalidTag:

        print("\nUnable to decrypt this message.")
        print("The message may have been modified or corrupted.")
        return

    sender_branch = get_branch_by_id(
        sender_branch_id
    )

    receiver_branch = get_branch_by_id(
        receiver_branch_id
    )

    sender_name = (
        sender_branch[1]
        if sender_branch
        else "Unknown"
    )

    receiver_name = (
        receiver_branch[1]
        if receiver_branch
        else "Unknown"
    )

    sender_code = get_branch_code(
        sender_branch_id
    )

    receiver_code = get_branch_code(
        receiver_branch_id
    )

    print("\n" + "=" * 60)
    print("                 SENT MESSAGE")
    print("=" * 60)

    print(f"\nMessage ID : {message_id}")

    print(
        f"From       : "
        f"{sender_name} ({sender_code})"
    )

    print(
        f"To         : "
        f"{receiver_name} ({receiver_code})"
    )

    print(f"Date       : {sent_date}")

    print("\n" + "-" * 60)
    print("Message:")
    print("-" * 60)

    print(decrypted_message)

    print("-" * 60)

    if is_read == 1:

        print("\nReceiver Status: READ")

    else:

        print("\nReceiver Status: UNREAD")

    print("=" * 60)
    input("\nPress Enter to return to Sent Messages...")

def show_sent_messages(branch):

    if not require_login():
        return

    branch_id = branch["branch_id"]
    branch_name = branch["branch_name"]
    branch_code = branch["branch_code"]

    while True:

        print("\n" + "=" * 70)
        print("                    SECURE BANK")
        print("                  SENT MESSAGES")
        print("=" * 70)

        print(f"\nYour Branch : {branch_name}")
        print(f"Branch Code : {branch_code}")

        messages = get_sent_messages_for_branch(
            branch_id
        )

        if len(messages) == 0:

            print("\nNo sent messages found.")

            print("\n" + "-" * 60)
            print("1. Back")
            print("-" * 60)

            choice = input(
                "Enter your choice: "
            ).strip()

            if choice == "1":
                return

            print("\nInvalid choice.")
            continue

        print("\n" + "-" * 80)

        print(
            f"{'ID':<6}"
            f"{'To':<22}"
            f"{'Date':<24}"
            f"{'Status':<10}"
        )

        print("-" * 80)

        for message in messages:

            (
                message_id,
                sender_branch_id,
                receiver_branch_id,
                encrypted_message,
                nonce,
                sent_date,
                is_read
            ) = message

            receiver_branch = get_branch_by_id(
                receiver_branch_id
            )

            if receiver_branch:

                receiver_name = receiver_branch[1]

            else:

                receiver_name = "Unknown"

            receiver_code = get_branch_code(
                receiver_branch_id
            )

            receiver_display = (
                f"{receiver_name} ({receiver_code})"
            )

            status = (
                "READ"
                if is_read == 1
                else "UNREAD"
            )

            print(
                f"{message_id:<6}"
                f"{receiver_display:<22}"
                f"{sent_date:<24}"
                f"{status:<10}"
            )

        print("-" * 80)

        print("\n1. Open Sent Message")
        print("2. Refresh Sent Messages")
        print("3. Back")

        choice = input(
            "\nEnter your choice (1-3): "
        ).strip()

        if choice == "1":

            open_sent_message(branch)

        elif choice == "2":

            print("\nRefreshing Sent Messages...")

        elif choice == "3":

            print("\nReturning...")
            return

        else:

            print("\nInvalid choice.")

if __name__ == "__main__":

    test_branch = {
        "branch_id": 1,
        "branch_code": "SB001",
        "branch_name": "Bangalore"
    }

    show_sent_messages(test_branch)            
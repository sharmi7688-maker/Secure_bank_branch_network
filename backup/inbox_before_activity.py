from database.database import (
    get_messages_for_branch,
    get_message_by_id,
    mark_message_as_read,
    get_branch_by_id
)

from modules.encryption import decrypt_message

def get_branch_code(branch_id):
    return f"SB{branch_id:03d}"

def open_message(branch):

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

    if receiver_branch_id != branch_id:

        print("\nAccess denied.")
        print("This message does not belong to your branch.")
        return

    try:

        decrypted_message = decrypt_message(
            encrypted_message,
            nonce
        )

    except Exception:

        print("\nUnable to decrypt this message.")
        print("The message may have been corrupted.")
        return

    sender_branch = get_branch_by_id(
        sender_branch_id
    )

    receiver_branch = get_branch_by_id(
        receiver_branch_id
    )

    sender_branch_name = (
        sender_branch[1]
        if sender_branch
        else "Unknown"
    )

    receiver_branch_name = (
        receiver_branch[1]
        if receiver_branch
        else "Unknown"
    )

    sender_branch_code = (
        get_branch_code(sender_branch_id)
    )

    receiver_branch_code = (
        get_branch_code(receiver_branch_id)
    )

    print("\n" + "=" * 60)
    print("                    SECURE MESSAGE")
    print("=" * 60)

    print(f"\nMessage ID : {message_id}")

    print(
        f"From       : "
        f"{sender_branch_name} "
        f"({sender_branch_code})"
    )

    print(
        f"To         : "
        f"{receiver_branch_name} "
        f"({receiver_branch_code})"
    )

    print(f"Date       : {sent_date}")

    print("\n" + "-" * 60)
    print("Message:")
    print("-" * 60)

    print(decrypted_message)

    print("-" * 60)

    if is_read == 0:

        updated_rows = mark_message_as_read(
            message_id,
            branch_id
        )

        if updated_rows == 1:

            print("\nMessage Status: READ")

        else:

            print("\nMessage Status: UNCHANGED")

    else:

        print("\nMessage Status: READ")

    print("=" * 60)
    input("\nPress Enter to return to Inbox...")

def show_inbox(branch):

    branch_id = branch["branch_id"]
    branch_name = branch["branch_name"]
    branch_code = branch["branch_code"]

    while True:

        print("\n" + "=" * 60)
        print("                     SECURE BANK")
        print("                         INBOX")
        print("=" * 60)

        print(f"\nYour Branch : {branch_name}")
        print(f"Branch Code : {branch_code}")

        messages = get_messages_for_branch(branch_id)

        if len(messages) == 0:

            print("\nNo messages found.")

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

        print("\n" + "-" * 70)

        print(
            f"{'ID':<6}"
            f"{'From':<18}"
            f"{'Date':<24}"
            f"{'Status':<10}"
        )

        print("-" * 70)

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

            status = "READ" if is_read == 1 else "NEW"

            sender_code = get_branch_code(
                sender_branch_id
            )

            sender_display = sender_code

            print(
                f"{message_id:<6}"
                f"{sender_display:<18}"
                f"{sent_date:<24}"
                f"{status:<10}"
            )

        print("-" * 70)

        print("\n1. Open Message")
        print("2. Refresh Inbox")
        print("3. Back")

        choice = input(
            "\nEnter your choice (1-3): "
        ).strip()

        if choice == "1":

            open_message(branch)

        elif choice == "2":

            print("\nRefreshing Inbox...")

        elif choice == "3":

            print("\nReturning...")
            return

        else:

            print("\nInvalid choice.")

if __name__ == "__main__":

    test_branch = {
        "branch_id": 2,
        "branch_code": "SB002",
        "branch_name": "Mysore"
    }

    show_inbox(test_branch)

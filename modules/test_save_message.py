from datetime import datetime

from modules.encryption import encrypt_message

from database.database import (
    save_message,
    get_message_by_id
)


def test_save_message():

    sender_branch_id = 1
    receiver_branch_id = 2

    original_message = (
        "Please verify today's transaction report."
    )

    # Encrypt the message
    encrypted_message, nonce = encrypt_message(
        original_message
    )

    # Get current date and time
    sent_date = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    # Save encrypted message
    message_id = save_message(
        sender_branch_id,
        receiver_branch_id,
        encrypted_message,
        nonce,
        sent_date
    )
    saved_message = get_message_by_id(message_id)
    

    print("\n" + "=" * 60)
    print("             MESSAGE SAVE TEST")
    print("=" * 60)

    print("\nSender Branch ID   :", sender_branch_id)
    print("Receiver Branch ID :", receiver_branch_id)
    print("Message ID         :", message_id)
    print("Sent Date          :", sent_date)

    print("\nEncrypted message saved successfully.")
    print("=" * 60)

    print("\nDatabase Record:")
    print(saved_message)


if __name__ == "__main__":
    test_save_message()
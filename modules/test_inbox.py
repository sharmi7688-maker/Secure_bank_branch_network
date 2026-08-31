from database.database import get_messages_for_branch
from modules.encryption import decrypt_message


def test_inbox():

    branch_id = 2

    messages = get_messages_for_branch(branch_id)

    print("\n" + "=" * 70)
    print("                    INBOX TEST")
    print("=" * 70)

    print("\nBranch ID:", branch_id)
    print("Number of messages:", len(messages))

    print("\n" + "-" * 70)

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

        print("\nMessage ID        :", message_id)
        print("Sender Branch ID  :", sender_branch_id)
        print("Receiver Branch ID:", receiver_branch_id)
        print("Encrypted Message :", encrypted_message)
        print("Nonce             :", nonce)
        print("Sent Date         :", sent_date)
        print("Read Status       :", is_read)

        try:

            decrypted_message = decrypt_message(
                encrypted_message,
                nonce
            )

            print("Decrypted Message :", decrypted_message)

        except Exception:

            print("Decrypted Message : Unable to decrypt")

        print("-" * 70)    


if __name__ == "__main__":
    test_inbox()
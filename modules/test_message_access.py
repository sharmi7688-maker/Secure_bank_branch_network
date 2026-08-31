from database.database import get_message_by_id


def test_message_access():

    message_id = 17

    attacker_branch_id = 3

    message = get_message_by_id(message_id)

    print("\n" + "=" * 60)
    print("       MESSAGE ACCESS SECURITY TEST")
    print("=" * 60)

    if message is None:

        print("\nMessage does not exist.")
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

    print("\nMessage ID:", message_id)
    print("Actual Receiver Branch ID:", receiver_branch_id)
    print("Testing Branch ID:", attacker_branch_id)

    if receiver_branch_id != attacker_branch_id:

        print("\nACCESS DENIED")
        print("The branch cannot access this message.")

    else:

        print("\nSECURITY ERROR")
        print("Unauthorized branch was allowed to access the message.")

    print("=" * 60)


if __name__ == "__main__":

    test_message_access()
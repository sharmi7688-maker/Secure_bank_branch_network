from modules.encryption import encrypt_message, decrypt_message


def test_encryption():

    original_message = "Urgent: Please review the branch transaction summary."

    print("\n" + "=" * 60)
    print("              AES-256-GCM ENCRYPTION TEST")
    print("=" * 60)

    print("\nOriginal Message:")
    print(original_message)

    encrypted_message, nonce = encrypt_message(original_message)

    print("\nEncrypted Message:")
    print(encrypted_message)

    print("\nNonce:")
    print(nonce)

    decrypted_message = decrypt_message(
        encrypted_message,
        nonce
    )

    print("\nDecrypted Message:")
    print(decrypted_message)

    print("\n" + "-" * 60)

    if decrypted_message == original_message:
        print("ENCRYPTION TEST: SUCCESS")
        print("Original and decrypted messages are identical.")
    else:
        print("ENCRYPTION TEST: FAILED")

    print("-" * 60)


if __name__ == "__main__":
    test_encryption()
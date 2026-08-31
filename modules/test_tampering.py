from modules.encryption import (
    encrypt_message,
    decrypt_message
)

from cryptography.exceptions import InvalidTag


def test_message_tampering():

    print("\n" + "=" * 60)
    print("           MESSAGE TAMPERING TEST")
    print("=" * 60)

    original_message = (
        "This is a confidential banking message."
    )

    print("\nOriginal Message:")
    print(original_message)

    print("\nEncrypting message...")

    encrypted_message, nonce = encrypt_message(
        original_message
    )

    print("Message encrypted successfully.")

    print("\nEncrypted Message:")
    print(encrypted_message)

    print("\nNonce:")
    print(nonce)

    print("\nTesting normal decryption...")

    try:

        decrypted_message = decrypt_message(
            encrypted_message,
            nonce
        )

        print("\nNormal decryption successful.")

        print("Decrypted Message:")
        print(decrypted_message)

    except Exception as error:

        print("\nUnexpected error:")
        print(error)

        return

    print("\n" + "-" * 60)
    print("Now modifying the encrypted message...")
    print("-" * 60)

    encrypted_bytes = bytearray(
        __import__("base64").b64decode(
            encrypted_message
        )
    )

    encrypted_bytes[0] ^= 1

    tampered_encrypted_message = (
        __import__("base64").b64encode(
            encrypted_bytes
        ).decode("utf-8")
    )

    print("\nEncrypted message has been tampered with.")

    print("\nAttempting to decrypt tampered message...")

    try:

        decrypt_message(
            tampered_encrypted_message,
            nonce
        )

        print("\nSECURITY ERROR")
        print("Tampered message was decrypted.")

    except InvalidTag:

        print("\nTAMPERING DETECTED")
        print("AES-256-GCM rejected the modified message.")
        print("Message integrity protection is working.")

    except Exception as error:

        print("\nUnexpected error:")
        print(error)

    print("\n" + "=" * 60)
    print("             TEST COMPLETED")
    print("=" * 60)


if __name__ == "__main__":

    test_message_tampering()
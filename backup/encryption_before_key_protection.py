import os
import base64

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


KEY_FILE = "config/encryption.key"


def generate_encryption_key():
    """
    Generates a secure 256-bit AES encryption key.
    """

    key = AESGCM.generate_key(bit_length=256)

    key_text = base64.b64encode(key).decode("utf-8")

    with open(KEY_FILE, "w") as file:
        file.write(key_text)

    return key_text

def load_encryption_key():
    """
    Loads the AES encryption key from the key file.
    """

    if not os.path.exists(KEY_FILE):
        raise FileNotFoundError(
            "Encryption key not found. "
            "Please generate the encryption key first."
        )

    with open(KEY_FILE, "r") as file:
        key_text = file.read().strip()

    return base64.b64decode(key_text)

def encrypt_message(message):
    """
    Encrypts a message using AES-256-GCM.

    Returns:
        encrypted_message
        nonce
    """

    key = load_encryption_key()

    aes_gcm = AESGCM(key)

    nonce = os.urandom(12)

    message_bytes = message.encode("utf-8")

    encrypted_data = aes_gcm.encrypt(
        nonce,
        message_bytes,
        None
    )

    encrypted_text = base64.b64encode(
        encrypted_data
    ).decode("utf-8")

    nonce_text = base64.b64encode(
        nonce
    ).decode("utf-8")

    return encrypted_text, nonce_text

def decrypt_message(encrypted_text, nonce_text):
    """
    Decrypts an AES-256-GCM encrypted message.
    """

    key = load_encryption_key()

    aes_gcm = AESGCM(key)

    encrypted_data = base64.b64decode(
        encrypted_text
    )

    nonce = base64.b64decode(
        nonce_text
    )

    decrypted_data = aes_gcm.decrypt(
        nonce,
        encrypted_data,
        None
    )

    return decrypted_data.decode("utf-8")

if __name__ == "__main__":

    key = generate_encryption_key()

    print("\nEncryption key generated successfully.")
    print("Key saved to:", KEY_FILE)
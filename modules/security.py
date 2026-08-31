import os
import base64

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.exceptions import InvalidKey


def hash_password(password):
    """
    Creates a secure password hash and random salt.
    Returns hash and salt as Base64 text.
    """

    # Generate a random 16-byte salt
    salt = os.urandom(16)

    # Create PBKDF2
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600000
    )

    # Convert password into bytes
    password_bytes = password.encode("utf-8")

    # Generate password hash
    password_hash = kdf.derive(password_bytes)

    # Convert binary values into text
    salt_text = base64.b64encode(salt).decode("utf-8")
    hash_text = base64.b64encode(password_hash).decode("utf-8")

    return hash_text, salt_text


def verify_password(password, stored_hash, stored_salt):
    """
    Verifies a password using the stored hash and salt.

    Returns:
        True  -> Password is correct
        False -> Password is incorrect
    """

    # Convert stored salt from text back to bytes
    salt = base64.b64decode(stored_salt)

    # Convert stored hash from text back to bytes
    expected_hash = base64.b64decode(stored_hash)

    # Create the same PBKDF2 configuration
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600000
    )

    # Convert entered password into bytes
    password_bytes = password.encode("utf-8")

    try:
        # Verify the entered password
        kdf.verify(password_bytes, expected_hash)

        return True

    except InvalidKey:
        return False
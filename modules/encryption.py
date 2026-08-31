import os
import base64

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

KEY_FILE = os.path.join(
    "config",
    "encryption.key"
)

KEY_SIZE = 32          # 32 bytes = 256 bits
NONCE_SIZE = 12        # Recommended GCM nonce size


# ---------------------------------------------------------
# GENERATE ENCRYPTION KEY
# ---------------------------------------------------------

def generate_encryption_key():
    """
    Generates a secure 256-bit AES encryption key.

    A new key is generated only if the key file
    does not already exist.
    """

    # Create config directory if it does not exist
    os.makedirs(
        os.path.dirname(KEY_FILE),
        exist_ok=True
    )

    # Never overwrite an existing encryption key
    if os.path.exists(KEY_FILE):

        raise FileExistsError(
            "Encryption key already exists. "
            "A new key was not generated."
        )

    # Generate secure 256-bit AES key
    key = AESGCM.generate_key(
        bit_length=256
    )

    # Convert binary key to Base64 text
    key_text = base64.b64encode(
        key
    ).decode("utf-8")

    # Store key
    with open(
        KEY_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(key_text)

    return key_text


# ---------------------------------------------------------
# LOAD ENCRYPTION KEY
# ---------------------------------------------------------

def load_encryption_key():
    """
    Loads and validates the AES-256 encryption key.

    Returns:
        bytes: 32-byte AES-256 key
    """

    if not os.path.exists(KEY_FILE):

        raise FileNotFoundError(
            "Encryption key not found.\n"
            "Please generate the encryption key first."
        )

    try:

        with open(
            KEY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            key_text = file.read().strip()

    except OSError as error:

        raise OSError(
            "Unable to read the encryption key file."
        ) from error

    if not key_text:

        raise ValueError(
            "Encryption key file is empty."
        )

    # Decode Base64
    try:

        key = base64.b64decode(
            key_text,
            validate=True
        )

    except Exception as error:

        raise ValueError(
            "Encryption key file contains "
            "invalid Base64 data."
        ) from error

    # AES-256 requires exactly 32 bytes
    if len(key) != KEY_SIZE:

        raise ValueError(
            "Invalid encryption key length.\n"
            "AES-256 requires a 32-byte key."
        )

    return key


# ---------------------------------------------------------
# ENCRYPT MESSAGE
# ---------------------------------------------------------

def encrypt_message(message):
    """
    Encrypts a message using AES-256-GCM.

    Returns:
        encrypted_message: Base64 encoded encrypted data
        nonce: Base64 encoded nonce
    """

    if not isinstance(message, str):

        raise TypeError(
            "Message must be a string."
        )

    if message == "":

        raise ValueError(
            "Message cannot be empty."
        )

    # Load AES-256 key
    key = load_encryption_key()

    # Create AES-GCM object
    aes_gcm = AESGCM(key)

    # Generate a fresh random nonce
    nonce = os.urandom(
        NONCE_SIZE
    )

    # Convert message to bytes
    message_bytes = message.encode(
        "utf-8"
    )

    # Encrypt message
    #
    # AES-GCM automatically creates
    # authentication data (authentication tag).
    encrypted_data = aes_gcm.encrypt(
        nonce,
        message_bytes,
        None
    )

    # Convert encrypted data to Base64
    encrypted_text = base64.b64encode(
        encrypted_data
    ).decode("utf-8")

    # Convert nonce to Base64
    nonce_text = base64.b64encode(
        nonce
    ).decode("utf-8")

    return encrypted_text, nonce_text


# ---------------------------------------------------------
# DECRYPT MESSAGE
# ---------------------------------------------------------

def decrypt_message(
    encrypted_text,
    nonce_text
):
    """
    Decrypts an AES-256-GCM encrypted message.

    Returns:
        str: Original plaintext message

    Raises:
        ValueError:
            If encrypted data or nonce is invalid.
        cryptography.exceptions.InvalidTag:
            If the message has been modified or
            the encryption key is incorrect.
    """

    if not isinstance(
        encrypted_text,
        str
    ):

        raise TypeError(
            "Encrypted message must be a string."
        )

    if not isinstance(
        nonce_text,
        str
    ):

        raise TypeError(
            "Nonce must be a string."
        )

    if not encrypted_text:

        raise ValueError(
            "Encrypted message cannot be empty."
        )

    if not nonce_text:

        raise ValueError(
            "Nonce cannot be empty."
        )

    # Load AES-256 key
    key = load_encryption_key()

    # Decode encrypted message
    try:

        encrypted_data = base64.b64decode(
            encrypted_text,
            validate=True
        )

    except Exception as error:

        raise ValueError(
            "Encrypted message contains "
            "invalid Base64 data."
        ) from error

    # Decode nonce
    try:

        nonce = base64.b64decode(
            nonce_text,
            validate=True
        )

    except Exception as error:

        raise ValueError(
            "Nonce contains invalid Base64 data."
        ) from error

    # Validate nonce length
    if len(nonce) != NONCE_SIZE:

        raise ValueError(
            "Invalid nonce length."
        )

    # Create AES-GCM object
    aes_gcm = AESGCM(key)

    # Decrypt and authenticate
    decrypted_data = aes_gcm.decrypt(
        nonce,
        encrypted_data,
        None
    )

    # Convert bytes back to text
    return decrypted_data.decode(
        "utf-8"
    )


# ---------------------------------------------------------
# TEST / KEY GENERATION
# ---------------------------------------------------------

if __name__ == "__main__":

    try:

        key = generate_encryption_key()

        print("\n" + "=" * 60)
        print("          ENCRYPTION KEY GENERATION")
        print("=" * 60)

        print(
            "\nEncryption key generated successfully."
        )

        print(
            f"Key saved to: {KEY_FILE}"
        )

        print(
            "Algorithm   : AES-256-GCM"
        )

        print(
            "Key size    : 256 bits"
        )

        print("=" * 60)

    except FileExistsError as error:

        print("\nSecurity Notice:")
        print(error)
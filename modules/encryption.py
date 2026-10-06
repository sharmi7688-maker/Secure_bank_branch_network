import os
import re
import json
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


# =========================================================
# ENHANCED ENCRYPTION (key versioning + authenticated context)
# =========================================================
#
# The functions above (encrypt_message / decrypt_message) are the original
# v1 implementation: ONE key (config/encryption.key), no associated data.
# They are kept unchanged so existing data and scripts keep working.
#
# The functions below add:
#
#   1. KEY VERSIONING / ROTATION
#        key id 1 -> config/encryption.key            (the original key)
#        key id N -> config/encryption_key_vN.key     (created by rotation)
#      The highest id is the ACTIVE key used for new data. Old keys stay on
#      disk so older messages can still be decrypted.
#
#   2. AUTHENTICATED CONTEXT (AES-GCM "associated data")
#      A new message is bound to its sender, receiver and timestamp. If
#      someone copies the ciphertext into another branch's row, decryption
#      fails with InvalidTag, because the context no longer matches.

_KEY_FILE_PATTERN = re.compile(r"^encryption_key_v(\d+)\.key$")


def _config_dir():
    return os.path.dirname(KEY_FILE) or "."


def _key_path(key_id):
    if key_id == 1:
        return KEY_FILE
    return os.path.join(_config_dir(), f"encryption_key_v{key_id}.key")


def list_key_ids():
    """Returns all available key ids in ascending order."""

    ids = set()

    if os.path.exists(KEY_FILE):
        ids.add(1)

    if os.path.isdir(_config_dir()):
        for name in os.listdir(_config_dir()):
            match = _KEY_FILE_PATTERN.match(name)
            if match and int(match.group(1)) >= 2:
                ids.add(int(match.group(1)))

    return sorted(ids)


def get_active_key_id():
    """Id of the key used to encrypt NEW data."""

    ids = list_key_ids()

    if not ids:
        raise FileNotFoundError(
            "No encryption key found. Run key setup first."
        )

    return ids[-1]


def ensure_key_exists():
    """Creates the first key if none exists. Returns the active key id."""

    if not list_key_ids():
        generate_encryption_key()

    return get_active_key_id()


def load_key_by_id(key_id):
    """Loads and validates the AES-256 key with the given id."""

    path = _key_path(key_id)

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Encryption key version {key_id} was not found."
        )

    with open(path, "r", encoding="utf-8") as file:
        key_text = file.read().strip()

    try:
        key = base64.b64decode(key_text, validate=True)
    except Exception:
        raise ValueError(f"Encryption key version {key_id} is corrupted.")

    if len(key) != KEY_SIZE:
        raise ValueError(
            f"Encryption key version {key_id} has an invalid length."
        )

    return key


def rotate_encryption_key():
    """Creates a NEW key version and makes it active. Existing messages stay
    readable (they remember which key id encrypted them).
    Returns the new key id."""

    ids = list_key_ids()
    new_id = (ids[-1] + 1) if ids else 1

    if new_id == 1:
        generate_encryption_key()
        return 1

    key_text = base64.b64encode(
        AESGCM.generate_key(bit_length=256)
    ).decode("utf-8")

    fd = os.open(
        _key_path(new_id),
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    with os.fdopen(fd, "w", encoding="utf-8") as file:
        file.write(key_text)

    return new_id


def build_message_aad(sender_branch_id, receiver_branch_id, sent_date):
    """Context that every v2 message is cryptographically bound to."""

    return (
        f"SBN-MSG|2|{sender_branch_id}|{receiver_branch_id}|{sent_date}"
    ).encode("utf-8")


def encrypt_payload(plaintext, aad=None, key_id=None):
    """
    AES-256-GCM encryption with a chosen key version and optional
    associated data.

    Returns (encrypted_text_b64, nonce_b64, key_id_used).
    """

    if not isinstance(plaintext, str) or plaintext == "":
        raise ValueError("Nothing to encrypt.")

    if key_id is None:
        key_id = get_active_key_id()

    nonce = os.urandom(NONCE_SIZE)

    encrypted = AESGCM(load_key_by_id(key_id)).encrypt(
        nonce, plaintext.encode("utf-8"), aad
    )

    return (
        base64.b64encode(encrypted).decode("utf-8"),
        base64.b64encode(nonce).decode("utf-8"),
        key_id,
    )


def decrypt_payload(encrypted_text, nonce_text, key_id, aad=None):
    """
    Reverse of encrypt_payload.
    Raises cryptography.exceptions.InvalidTag when the data, the key or the
    associated data (sender / receiver / date) do not match.
    """

    encrypted = base64.b64decode(encrypted_text, validate=True)
    nonce = base64.b64decode(nonce_text, validate=True)

    plaintext = AESGCM(load_key_by_id(key_id)).decrypt(
        nonce, encrypted, aad
    )

    return plaintext.decode("utf-8")


def pack_message(subject, body):
    """v2 messages encrypt subject AND body together."""
    return json.dumps({"s": subject, "b": body}, ensure_ascii=False)


def unpack_message(plaintext):
    data = json.loads(plaintext)
    return data["s"], data["b"]


def encrypt_secret(secret_text, context):
    """Encrypts a small secret (e.g. a 2FA seed) for storage in the DB.
    Returns (encrypted_b64, nonce_b64, key_id)."""

    return encrypt_payload(
        secret_text, aad=f"SBN-SECRET|{context}".encode("utf-8")
    )


def decrypt_secret(encrypted_text, nonce_text, key_id, context):
    return decrypt_payload(
        encrypted_text, nonce_text, key_id,
        aad=f"SBN-SECRET|{context}".encode("utf-8"),
    )

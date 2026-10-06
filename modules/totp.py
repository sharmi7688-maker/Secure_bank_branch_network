"""
TIME-BASED ONE-TIME PASSWORDS (RFC 6238) — standard library only.

Compatible with Google Authenticator, Microsoft Authenticator, Authy, etc.
(HMAC-SHA1, 6 digits, 30-second step).
"""

import base64
import hashlib
import hmac
import os
import struct
import time
from urllib.parse import quote

STEP_SECONDS = 30
DIGITS = 6


def generate_secret(num_bytes=20):
    """Random Base32 secret (160 bits by default, as recommended)."""
    return base64.b32encode(os.urandom(num_bytes)).decode("ascii").rstrip("=")


def _decode_secret(secret):
    secret = secret.strip().replace(" ", "").upper()
    padding = "=" * (-len(secret) % 8)
    return base64.b32decode(secret + padding)


def _hotp(secret, counter, digits=DIGITS):
    digest = hmac.new(
        _decode_secret(secret),
        struct.pack(">Q", counter),
        hashlib.sha1,
    ).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(value % (10 ** digits)).zfill(digits)


def current_step(for_time=None, step=STEP_SECONDS):
    moment = time.time() if for_time is None else for_time
    return int(moment // step)


def totp_code(secret, for_time=None, step=STEP_SECONDS, digits=DIGITS):
    """Code valid at the given time (default: now)."""
    return _hotp(secret, current_step(for_time, step), digits)


def verify_totp(secret, code, for_time=None, window=1,
                step=STEP_SECONDS, digits=DIGITS, min_step=0):
    """
    Checks a user-supplied code.

    window    : accepts +/- this many steps to allow for clock drift.
    min_step  : codes for steps <= min_step are rejected (replay protection:
                pass the last step that was already used).

    Returns the matched step number, or None if the code is not valid.
    """

    if not isinstance(code, str):
        return None

    code = code.strip().replace(" ", "")
    if len(code) != digits or not code.isdigit():
        return None

    now_step = current_step(for_time, step)
    matched = None

    # Always test every candidate so timing does not reveal which one matched
    for offset in range(-window, window + 1):
        candidate_step = now_step + offset
        expected = _hotp(secret, candidate_step, digits)
        if hmac.compare_digest(expected, code) \
                and candidate_step > min_step and matched is None:
            matched = candidate_step

    return matched


def provisioning_uri(secret, account_name, issuer="Secure Bank"):
    """otpauth:// URI that authenticator apps understand (used for the QR)."""
    label = quote(f"{issuer}:{account_name}")
    return (
        f"otpauth://totp/{label}?secret={secret}"
        f"&issuer={quote(issuer)}&algorithm=SHA1"
        f"&digits={DIGITS}&period={STEP_SECONDS}"
    )


def qr_png_bytes(data):
    """PNG bytes of a QR code for `data`, or None when the optional
    'qrcode' package is not installed (the UI then shows the secret key
    for manual entry)."""

    try:
        import io
        import qrcode
    except ImportError:
        return None

    image = qrcode.make(data)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()

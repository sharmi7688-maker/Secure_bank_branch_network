import base64
import unittest

import tests.base  # noqa: F401  (sets up sys.path)
from modules import totp

RFC_SECRET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"  # ASCII "12345678901234567890"


class TotpTests(unittest.TestCase):

    def test_rfc6238_reference_vectors(self):
        vectors = {
            59: "94287082",
            1111111109: "07081804",
            1111111111: "14050471",
            1234567890: "89005924",
            2000000000: "69279037",
            20000000000: "65353130",
        }
        for moment, expected in vectors.items():
            self.assertEqual(
                totp.totp_code(RFC_SECRET, for_time=moment, digits=8),
                expected,
            )

    def test_six_digit_code_is_last_six_digits(self):
        self.assertEqual(totp.totp_code(RFC_SECRET, for_time=59), "287082")

    def test_verify_accepts_current_and_adjacent_step(self):
        now = 1_700_000_000
        code = totp.totp_code(RFC_SECRET, for_time=now)
        self.assertEqual(
            totp.verify_totp(RFC_SECRET, code, for_time=now),
            totp.current_step(now),
        )
        # a code from the previous 30-second step (clock drift) is accepted
        self.assertIsNotNone(
            totp.verify_totp(RFC_SECRET, code, for_time=now + 30))

    def test_verify_rejects_codes_two_steps_away(self):
        now = 1_700_000_000
        code = totp.totp_code(RFC_SECRET, for_time=now)
        self.assertIsNone(
            totp.verify_totp(RFC_SECRET, code, for_time=now + 90))

    def test_replay_protection_with_min_step(self):
        now = 1_700_000_000
        code = totp.totp_code(RFC_SECRET, for_time=now)
        step = totp.verify_totp(RFC_SECRET, code, for_time=now)
        self.assertIsNone(
            totp.verify_totp(RFC_SECRET, code, for_time=now, min_step=step))

    def test_malformed_codes_rejected(self):
        for bad in ("", "12345", "1234567", "abcdef", None, 123456):
            self.assertIsNone(
                totp.verify_totp(RFC_SECRET, bad, for_time=1_700_000_000))

    def test_spaces_in_code_are_ignored(self):
        now = 1_700_000_000
        code = totp.totp_code(RFC_SECRET, for_time=now)
        spaced = code[:3] + " " + code[3:]
        self.assertIsNotNone(totp.verify_totp(RFC_SECRET, spaced, for_time=now))

    def test_generated_secret_is_160_bit_base32(self):
        secret = totp.generate_secret()
        padded = secret + "=" * (-len(secret) % 8)
        self.assertEqual(len(base64.b32decode(padded)), 20)
        self.assertNotEqual(secret, totp.generate_secret())

    def test_provisioning_uri(self):
        uri = totp.provisioning_uri("ABCDEF", "SB001", issuer="Secure Bank")
        self.assertTrue(uri.startswith("otpauth://totp/Secure%20Bank%3ASB001"))
        self.assertIn("secret=ABCDEF", uri)
        self.assertIn("issuer=Secure%20Bank", uri)


if __name__ == "__main__":
    unittest.main()

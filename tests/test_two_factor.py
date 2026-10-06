import sqlite3
import unittest

from tests.base import TempProjectTestCase, PASSWORD
from database.database import get_activities_for_branch, get_all_admin_activities
from modules import totp, two_factor
from modules.auth_service import (
    authenticate_branch, complete_branch_2fa,
    authenticate_admin, complete_admin_2fa,
)

T0 = 1_800_000_000


class TwoFactorTests(TempProjectTestCase):

    def setUp(self):
        super().setUp()
        self.bid = self.make_branch("Alpha")        # SB001
        self.admin = self.make_admin("root_admin")

    def enroll(self, kind="branch", account_id=None, moment=T0):
        account_id = account_id or (self.bid if kind == "branch" else self.admin)
        secret = two_factor.start_enrollment(kind, account_id)
        code = totp.totp_code(secret, for_time=moment)
        self.assertTrue(
            two_factor.confirm_enrollment(kind, account_id, code, now=moment))
        return secret

    def event_types(self):
        return [a[2] for a in get_activities_for_branch(self.bid)]

    # ---- enrolment ------------------------------------------------

    def test_not_enabled_until_confirmed(self):
        two_factor.start_enrollment("branch", self.bid)
        self.assertFalse(two_factor.is_enabled("branch", self.bid))
        self.assertIsNotNone(two_factor.get_pending_secret("branch", self.bid))

    def test_wrong_code_does_not_enable(self):
        two_factor.start_enrollment("branch", self.bid)
        self.assertFalse(
            two_factor.confirm_enrollment("branch", self.bid, "000000",
                                          now=T0))
        self.assertFalse(two_factor.is_enabled("branch", self.bid))

    def test_enrolment_is_logged(self):
        self.enroll()
        self.assertIn("2FA_ENABLED", self.event_types())

    def test_secret_is_encrypted_at_rest(self):
        secret = self.enroll()
        with open("database/bank.db", "rb") as f:
            self.assertNotIn(secret.encode(), f.read())
        connection = sqlite3.connect("database/bank.db")
        stored = connection.execute(
            "SELECT secret_enc FROM two_factor").fetchone()[0]
        connection.close()
        self.assertNotEqual(stored, secret)

    def test_secret_is_bound_to_its_account(self):
        # copying branch 1's encrypted secret onto another account must fail
        self.enroll()
        other = self.make_branch("Beta")
        connection = sqlite3.connect("database/bank.db")
        connection.execute(
            "UPDATE two_factor SET account_id = ? WHERE account_id = ?",
            (other, self.bid))
        connection.commit()
        connection.close()
        from cryptography.exceptions import InvalidTag
        with self.assertRaises(InvalidTag):
            two_factor.verify_login_code("branch", other, "123456", now=T0)

    # ---- login ----------------------------------------------------

    def test_login_without_2fa_is_unchanged(self):
        self.assertTrue(authenticate_branch("SB001", PASSWORD).ok)

    def test_login_with_2fa_needs_second_step(self):
        secret = self.enroll()
        first = authenticate_branch("SB001", PASSWORD)
        self.assertEqual(first.status, "NEEDS_2FA")
        self.assertNotIn("LOGIN", self.event_types())   # not logged in yet

        moment = T0 + 60
        code = totp.totp_code(secret, for_time=moment)
        done = complete_branch_2fa(self.bid, code, now=moment)
        self.assertTrue(done.ok)
        login = [a for a in get_activities_for_branch(self.bid)
                 if a[2] == "LOGIN"]
        self.assertIn("2FA verified", login[0][3])

    def test_wrong_password_never_reaches_2fa(self):
        self.enroll()
        self.assertEqual(
            authenticate_branch("SB001", "wrong").status, "BAD_PASSWORD")

    def test_used_code_cannot_be_replayed(self):
        secret = self.enroll()
        moment = T0 + 60
        code = totp.totp_code(secret, for_time=moment)
        self.assertTrue(complete_branch_2fa(self.bid, code, now=moment).ok)
        again = complete_branch_2fa(self.bid, code, now=moment)
        self.assertEqual(again.status, "BAD_2FA")

    def test_code_used_for_enrolment_cannot_be_reused_to_log_in(self):
        secret = self.enroll(moment=T0)
        code = totp.totp_code(secret, for_time=T0)
        self.assertEqual(
            complete_branch_2fa(self.bid, code, now=T0).status, "BAD_2FA")

    def test_three_wrong_codes_lock_the_account(self):
        self.enroll()
        for expected in (1, 2, 3):
            result = complete_branch_2fa(self.bid, "000000", now=T0 + 60)
            self.assertEqual(result.status, "BAD_2FA")
            self.assertEqual(result.attempts, expected)
        self.assertIn("ACCOUNT_LOCKED", self.event_types())
        self.assertIn("FAILED_2FA", self.event_types())
        locked = authenticate_branch("SB001", PASSWORD)
        self.assertEqual(locked.status, "LOCKED")

    # ---- disable / reset -----------------------------------------

    def test_disable_needs_password_and_valid_code(self):
        secret = self.enroll()
        moment = T0 + 60
        code = totp.totp_code(secret, for_time=moment)

        ok, _ = two_factor.disable("branch", self.bid, "wrong", code,
                                   now=moment)
        self.assertFalse(ok)
        ok, _ = two_factor.disable("branch", self.bid, PASSWORD, "000000",
                                   now=moment)
        self.assertFalse(ok)
        self.assertTrue(two_factor.is_enabled("branch", self.bid))

        ok, _ = two_factor.disable("branch", self.bid, PASSWORD, code,
                                   now=moment)
        self.assertTrue(ok)
        self.assertFalse(two_factor.is_enabled("branch", self.bid))
        self.assertIn("2FA_DISABLED", self.event_types())

    def test_administrator_can_reset_a_lost_device(self):
        self.enroll()
        self.assertTrue(two_factor.admin_reset("branch", self.bid))
        self.assertFalse(two_factor.is_enabled("branch", self.bid))
        self.assertTrue(authenticate_branch("SB001", PASSWORD).ok)

    # ---- administrators ------------------------------------------

    def test_admin_login_with_2fa(self):
        secret = self.enroll("admin")
        first = authenticate_admin("root_admin", PASSWORD)
        self.assertEqual(first.status, "NEEDS_2FA")
        moment = T0 + 60
        code = totp.totp_code(secret, for_time=moment)
        self.assertTrue(
            complete_admin_2fa(self.admin, code, now=moment).ok)
        types = [row[2] for row in get_all_admin_activities()]
        self.assertIn("ADMIN_2FA_ENABLED", types)
        self.assertIn("ADMIN_LOGIN", types)


if __name__ == "__main__":
    unittest.main()

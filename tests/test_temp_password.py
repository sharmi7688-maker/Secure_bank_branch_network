"""Admin-issued temporary password (forgotten-password recovery)."""

import os
import sqlite3
import time
import unittest
from datetime import datetime, timedelta

from tests.base import PASSWORD, TempProjectTestCase

from database.database import get_all_admin_activities, get_activities_for_branch
from modules import password_policy as pp
from modules import two_factor, totp
from modules.audit_chain import verify_all
from modules.auth_service import (
    authenticate_admin, authenticate_branch, complete_branch_2fa,
)
from modules.register import validate_password as branch_rule
from modules.admin_setup import validate_admin_password as admin_rule


class TempPasswordTests(TempProjectTestCase):

    def setUp(self):
        super().setUp()
        self.bid = self.make_branch("Alpha")
        self.admin_id = self.make_admin("root_admin")
        self.other_admin = self.make_admin("second_admin")
        self.code = f"SB{self.bid:03d}"

    # ---- generator ------------------------------------------------

    def test_generated_passwords_meet_every_rule(self):
        seen = set()
        for _ in range(25):
            password = pp.generate_temporary_password()
            self.assertTrue(branch_rule(password))
            self.assertTrue(admin_rule(password))
            self.assertGreaterEqual(len(password), 14)
            self.assertNotIn(password, seen)
            seen.add(password)

    def test_no_look_alike_characters(self):
        for _ in range(25):
            password = pp.generate_temporary_password()
            self.assertFalse(set(password) & set("0O1lI"))

    # ---- issuing --------------------------------------------------

    def test_branch_can_sign_in_with_temp_password_and_must_change_it(self):
        temporary = pp.issue_temporary_password(
            self.admin_id, "branch", self.bid)

        # the old password no longer works
        self.assertEqual(
            authenticate_branch(self.code, PASSWORD).status, "BAD_PASSWORD")

        result = authenticate_branch(self.code, temporary)
        self.assertTrue(result.ok)
        self.assertTrue(result.must_change_password)

        ok, _message = pp.change_password(
            "branch", self.bid, temporary, "N3w!Passw0rd#77",
            "N3w!Passw0rd#77")
        self.assertTrue(ok)
        self.assertFalse(pp.must_change_password("branch", self.bid))
        self.assertIsNone(pp.store.get_temp_password_expiry("branch", self.bid))

        # the temporary password is dead, the new one works
        self.assertEqual(
            authenticate_branch(self.code, temporary).status, "BAD_PASSWORD")
        self.assertTrue(authenticate_branch(self.code, "N3w!Passw0rd#77").ok)

    def test_admin_can_recover_another_admin(self):
        temporary = pp.issue_temporary_password(
            self.admin_id, "admin", self.other_admin)

        result = authenticate_admin("second_admin", temporary)
        self.assertTrue(result.ok)
        self.assertTrue(result.must_change_password)

    def test_cannot_issue_for_your_own_admin_account(self):
        with self.assertRaises(ValueError):
            pp.issue_temporary_password(
                self.admin_id, "admin", self.admin_id)

    def test_unknown_account_and_bad_kind(self):
        with self.assertRaises(ValueError):
            pp.issue_temporary_password(self.admin_id, "branch", 999)
        with self.assertRaises(ValueError):
            pp.issue_temporary_password(self.admin_id, "robot", 1)

    def test_password_is_stored_hashed_and_never_logged(self):
        temporary = pp.issue_temporary_password(
            self.admin_id, "branch", self.bid)

        connection = sqlite3.connect(os.path.join("database", "bank.db"))
        try:
            dump = "\n".join(
                str(row) for table in
                ("branches", "admins", "activity_logs", "admin_activity_logs")
                for row in connection.execute(f"SELECT * FROM {table}")
            )
        finally:
            connection.close()

        self.assertNotIn(temporary, dump)

    def test_both_sides_are_audited_and_chain_stays_valid(self):
        pp.issue_temporary_password(self.admin_id, "branch", self.bid)

        admin_types = [a[2] for a in get_all_admin_activities()]
        self.assertIn("ADMIN_TEMP_PASSWORD_ISSUED", admin_types)

        branch_types = [a[2] for a in get_activities_for_branch(self.bid)]
        self.assertIn("TEMP_PASSWORD_ISSUED", branch_types)

        self.assertTrue(all(r["ok"] for r in verify_all()))

    def test_lockout_is_cleared(self):
        for _ in range(3):
            authenticate_branch(self.code, "wrong")
        self.assertEqual(
            authenticate_branch(self.code, PASSWORD).status, "LOCKED")

        temporary = pp.issue_temporary_password(
            self.admin_id, "branch", self.bid)
        self.assertTrue(authenticate_branch(self.code, temporary).ok)

    # ---- expiry ---------------------------------------------------

    def test_temp_password_expires(self):
        temporary = pp.issue_temporary_password(
            self.admin_id, "branch", self.bid)

        pp.store.set_temporary_password(
            "branch", self.bid, *pp.hash_password(temporary),
            (datetime.now() - timedelta(minutes=1)).strftime(
                "%Y-%m-%d %H:%M:%S"))

        result = authenticate_branch(self.code, temporary)
        self.assertEqual(result.status, "TEMP_EXPIRED")
        self.assertFalse(result.ok)

        types = [a[2] for a in get_activities_for_branch(self.bid)]
        self.assertIn("TEMP_PASSWORD_EXPIRED", types)

        # an expired password is not a wrong password: no lockout counted
        self.assertEqual(result.attempts, 0)

    def test_expiry_window_is_24_hours(self):
        pp.issue_temporary_password(self.admin_id, "branch", self.bid)
        expiry = datetime.strptime(
            pp.store.get_temp_password_expiry("branch", self.bid),
            "%Y-%m-%d %H:%M:%S")
        hours = (expiry - datetime.now()).total_seconds() / 3600
        self.assertTrue(23.9 < hours <= 24.0)

    def test_corrupt_expiry_fails_closed(self):
        pp.store.set_temporary_password(
            "branch", self.bid, *pp.hash_password("Abcdef!234xyz"), "garbage")
        self.assertTrue(pp.temp_password_expired("branch", self.bid))

    def test_normal_accounts_are_never_expired(self):
        self.assertFalse(pp.temp_password_expired("branch", self.bid))

    # ---- 2FA interaction -----------------------------------------

    def test_two_factor_stays_on_after_temp_password(self):
        secret = two_factor.start_enrollment("branch", self.bid)
        self.assertTrue(two_factor.confirm_enrollment(
            "branch", self.bid, totp.totp_code(secret)))

        temporary = pp.issue_temporary_password(
            self.admin_id, "branch", self.bid)

        result = authenticate_branch(self.code, temporary)
        self.assertEqual(result.status, "NEEDS_2FA")

        later = time.time() + 60          # next code window (not the enrolment one)
        done = complete_branch_2fa(
            self.bid, totp.totp_code(secret, for_time=later), now=later)
        self.assertTrue(done.ok)
        self.assertTrue(done.must_change_password)

    # ---- console recovery ----------------------------------------

    def test_console_reset_for_the_only_admin(self):
        temporary = pp.console_reset_admin_password("root_admin")

        result = authenticate_admin("root_admin", temporary)
        self.assertTrue(result.ok)
        self.assertTrue(result.must_change_password)

        types = [a[2] for a in get_all_admin_activities()]
        self.assertIn("ADMIN_CONSOLE_PASSWORD_RESET", types)
        self.assertTrue(all(r["ok"] for r in verify_all()))

    def test_console_reset_can_also_remove_2fa(self):
        secret = two_factor.start_enrollment("admin", self.admin_id)
        two_factor.confirm_enrollment(
            "admin", self.admin_id, totp.totp_code(secret))
        self.assertTrue(two_factor.is_enabled("admin", self.admin_id))

        pp.console_reset_admin_password("root_admin", also_reset_2fa=True)
        self.assertFalse(two_factor.is_enabled("admin", self.admin_id))

    def test_console_reset_unknown_admin(self):
        with self.assertRaises(ValueError):
            pp.console_reset_admin_password("nobody")


if __name__ == "__main__":
    unittest.main()

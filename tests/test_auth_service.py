import unittest

from tests.base import TempProjectTestCase, PASSWORD
from database.database import get_activities_for_branch, get_all_admin_activities
from modules.auth_service import authenticate_branch, authenticate_admin
from modules.session_timeout import (
    is_expired, seconds_remaining, SESSION_TIMEOUT_MINUTES,
)
from datetime import datetime, timedelta


class BranchAuthTests(TempProjectTestCase):

    def setUp(self):
        super().setUp()
        self.bid = self.make_branch("Alpha")

    def types(self):
        return [a[2] for a in get_activities_for_branch(self.bid)]

    def test_successful_login_is_logged(self):
        result = authenticate_branch("sb001", PASSWORD)   # case-insensitive
        self.assertTrue(result.ok)
        self.assertEqual(result.account_name, "Alpha")
        self.assertIn("LOGIN", self.types())

    def test_invalid_code_format(self):
        self.assertEqual(
            authenticate_branch("XX1", PASSWORD).status, "INVALID_CODE")

    def test_unknown_branch(self):
        self.assertEqual(
            authenticate_branch("SB099", PASSWORD).status, "NOT_FOUND")

    def test_empty_password(self):
        self.assertEqual(
            authenticate_branch("SB001", "").status, "EMPTY_PASSWORD")

    def test_wrong_password_counts_attempts(self):
        first = authenticate_branch("SB001", "nope")
        second = authenticate_branch("SB001", "nope")
        self.assertEqual((first.status, first.attempts), ("BAD_PASSWORD", 1))
        self.assertEqual(second.attempts, 2)
        self.assertEqual(self.types().count("FAILED_LOGIN"), 2)

    def test_lockout_after_three_failures(self):
        for _ in range(3):
            authenticate_branch("SB001", "nope")
        self.assertIn("ACCOUNT_LOCKED", self.types())

        locked = authenticate_branch("SB001", PASSWORD)   # even correct one
        self.assertEqual(locked.status, "LOCKED")
        self.assertGreater(locked.remaining_seconds, 0)
        self.assertLessEqual(locked.remaining_seconds, 300)

    def test_success_resets_failed_attempts(self):
        authenticate_branch("SB001", "nope")
        self.assertTrue(authenticate_branch("SB001", PASSWORD).ok)
        self.assertEqual(authenticate_branch("SB001", "nope").attempts, 1)


class AdminAuthTests(TempProjectTestCase):

    def setUp(self):
        super().setUp()
        self.admin = self.make_admin("root_admin")

    def test_login_and_audit(self):
        self.assertTrue(authenticate_admin("root_admin", PASSWORD).ok)
        self.assertIn("ADMIN_LOGIN",
                      [r[2] for r in get_all_admin_activities()])

    def test_unknown_user_looks_like_wrong_password(self):
        unknown = authenticate_admin("nobody", PASSWORD)
        wrong = authenticate_admin("root_admin", "nope")
        self.assertEqual(unknown.status, wrong.status)
        self.assertTrue(unknown.message.startswith("Invalid username or password"))
        self.assertTrue(wrong.message.startswith("Invalid username or password"))

    def test_admin_lockout(self):
        for _ in range(3):
            authenticate_admin("root_admin", "nope")
        self.assertEqual(
            authenticate_admin("root_admin", PASSWORD).status, "LOCKED")
        self.assertIn("ADMIN_ACCOUNT_LOCKED",
                      [r[2] for r in get_all_admin_activities()])


class SessionTimeoutTests(unittest.TestCase):

    def test_not_expired_within_limit(self):
        now = datetime(2026, 10, 1, 12, 0, 0)
        last = now - timedelta(minutes=SESSION_TIMEOUT_MINUTES - 1)
        self.assertFalse(is_expired(last, now))
        self.assertEqual(seconds_remaining(last, now), 60)

    def test_expired_after_limit(self):
        now = datetime(2026, 10, 1, 12, 0, 0)
        last = now - timedelta(minutes=SESSION_TIMEOUT_MINUTES, seconds=1)
        self.assertTrue(is_expired(last, now))
        self.assertEqual(seconds_remaining(last, now), 0)

    def test_custom_timeout(self):
        now = datetime(2026, 10, 1, 12, 0, 0)
        self.assertTrue(is_expired(now - timedelta(minutes=3), now,
                                   timeout_minutes=2))


if __name__ == "__main__":
    unittest.main()

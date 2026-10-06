import unittest

from tests.base import TempProjectTestCase, PASSWORD
from database.database import get_activities_for_branch, get_all_admin_activities
from modules import password_policy as pp
from modules.auth_service import authenticate_branch, authenticate_admin


class StrengthMeterTests(unittest.TestCase):

    def score(self, password, words=()):
        return pp.password_strength(password, words)["score"]

    def test_empty(self):
        self.assertEqual(self.score(""), 0)

    def test_policy_failures_are_weak(self):
        self.assertEqual(self.score("abc"), 1)
        self.assertEqual(self.score("alllowercase123"), 1)

    def test_meets_policy_is_fair(self):
        self.assertEqual(self.score("Str0ng!Pass"), 2)

    def test_14_character_password_is_strong(self):
        self.assertEqual(self.score("Tr1cky!Horse#B"), 3)

    def test_16_plus_unique_characters_is_very_strong(self):
        self.assertEqual(self.score("Tr1cky!Horse#Battery"), 4)

    def test_common_words_are_capped(self):
        result = pp.password_strength("Password@123456")
        self.assertEqual(result["score"], 1)
        self.assertTrue(result["feedback"])

    def test_personal_words_are_capped(self):
        self.assertEqual(
            self.score("Alpha!Secret#99x", words=("Alpha",)), 1)

    def test_repeats_and_sequences_prevent_top_scores(self):
        self.assertLessEqual(self.score("Aaaa!bbbb#1234567"), 2)

    def test_rule_checklist(self):
        rules = dict(pp.password_strength("abc")["rules"])
        self.assertFalse(rules["At least 10 characters"])
        self.assertTrue(rules["A lowercase letter"])


class ChangePasswordTests(TempProjectTestCase):

    NEW = "Fresh!Secret#2026"

    def setUp(self):
        super().setUp()
        self.bid = self.make_branch("Alpha")
        self.admin = self.make_admin("root_admin")

    def change(self, current=PASSWORD, new=NEW, confirm=None, kind="branch"):
        account = self.bid if kind == "branch" else self.admin
        return pp.change_password(
            kind, account, current, new, new if confirm is None else confirm)

    def test_success_replaces_the_password(self):
        ok, _ = self.change()
        self.assertTrue(ok)
        self.assertEqual(
            authenticate_branch("SB001", PASSWORD).status, "BAD_PASSWORD")
        self.assertTrue(authenticate_branch("SB001", self.NEW).ok)
        self.assertIn("PASSWORD_CHANGED",
                      [a[2] for a in get_activities_for_branch(self.bid)])

    def test_admin_password_change(self):
        ok, _ = self.change(kind="admin")
        self.assertTrue(ok)
        self.assertTrue(authenticate_admin("root_admin", self.NEW).ok)
        self.assertIn("ADMIN_PASSWORD_CHANGED",
                      [r[2] for r in get_all_admin_activities()])

    def test_wrong_current_password_is_rejected_and_counted(self):
        ok, message = self.change(current="wrong")
        self.assertFalse(ok)
        self.assertIn("1/3", message)
        self.assertIn("FAILED_PASSWORD_CHANGE",
                      [a[2] for a in get_activities_for_branch(self.bid)])

    def test_repeated_wrong_current_password_locks_the_account(self):
        for _ in range(3):
            self.change(current="wrong")
        ok, message = self.change()
        self.assertFalse(ok)
        self.assertIn("locked", message.lower())

    def test_confirmation_must_match(self):
        ok, message = self.change(confirm="Different!Secret#1")
        self.assertFalse(ok)
        self.assertIn("do not match", message)

    def test_weak_new_password_rejected(self):
        ok, _ = self.change(new="weak")
        self.assertFalse(ok)

    def test_new_password_must_differ_from_current(self):
        ok, message = self.change(new=PASSWORD)
        self.assertFalse(ok)
        self.assertIn("different", message)

    def test_new_password_must_not_contain_the_name(self):
        ok, message = self.change(new="Alpha!Secret#2026")
        self.assertFalse(ok)
        self.assertIn("name", message)

    def test_forced_change_flag(self):
        pp.force_password_change("branch", self.bid)
        result = authenticate_branch("SB001", PASSWORD)
        self.assertTrue(result.ok)
        self.assertTrue(result.must_change_password)

        self.assertTrue(self.change()[0])
        self.assertFalse(pp.must_change_password("branch", self.bid))
        self.assertFalse(
            authenticate_branch("SB001", self.NEW).must_change_password)


if __name__ == "__main__":
    unittest.main()

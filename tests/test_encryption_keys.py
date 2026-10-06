import os
import unittest

from cryptography.exceptions import InvalidTag

from tests.base import TempProjectTestCase
from modules import encryption as enc
from modules import key_management
from modules.messaging_service import send_message, open_message
from database import store


class KeyVersioningTests(TempProjectTestCase):

    def test_first_key_is_version_1_and_matches_original_file(self):
        self.assertEqual(enc.list_key_ids(), [1])
        self.assertTrue(os.path.exists(os.path.join("config", "encryption.key")))
        self.assertEqual(enc.get_active_key_id(), 1)

    def test_rotation_creates_new_active_key(self):
        new_id = enc.rotate_encryption_key()
        self.assertEqual(new_id, 2)
        self.assertEqual(enc.list_key_ids(), [1, 2])
        self.assertEqual(enc.get_active_key_id(), 2)
        self.assertNotEqual(enc.load_key_by_id(1), enc.load_key_by_id(2))

    def test_old_data_stays_readable_after_rotation(self):
        encrypted, nonce, key_id = enc.encrypt_payload("secret")
        enc.rotate_encryption_key()
        self.assertEqual(
            enc.decrypt_payload(encrypted, nonce, key_id), "secret")

    def test_new_data_uses_the_active_key(self):
        enc.rotate_encryption_key()
        _e, _n, key_id = enc.encrypt_payload("x")
        self.assertEqual(key_id, 2)

    def test_wrong_key_version_fails(self):
        enc.rotate_encryption_key()
        encrypted, nonce, _ = enc.encrypt_payload("secret", key_id=1)
        with self.assertRaises(InvalidTag):
            enc.decrypt_payload(encrypted, nonce, 2)

    def test_associated_data_must_match(self):
        aad = enc.build_message_aad(1, 2, "2026-01-01 10:00:00")
        encrypted, nonce, key_id = enc.encrypt_payload("hi", aad=aad)
        self.assertEqual(
            enc.decrypt_payload(encrypted, nonce, key_id, aad), "hi")
        for wrong in (enc.build_message_aad(1, 3, "2026-01-01 10:00:00"),
                      enc.build_message_aad(2, 1, "2026-01-01 10:00:00"),
                      enc.build_message_aad(1, 2, "2026-01-01 10:00:01"),
                      None):
            with self.assertRaises(InvalidTag):
                enc.decrypt_payload(encrypted, nonce, key_id, wrong)

    def test_nonce_is_unique_per_encryption(self):
        nonces = {enc.encrypt_payload("same")[1] for _ in range(50)}
        self.assertEqual(len(nonces), 50)

    def test_corrupted_key_file_is_rejected(self):
        enc.rotate_encryption_key()
        with open(os.path.join("config", "encryption_key_v2.key"), "w") as f:
            f.write("not-a-key")
        with self.assertRaises(ValueError):
            enc.load_key_by_id(2)

    def test_secret_helpers_are_bound_to_their_context(self):
        encrypted, nonce, key_id = enc.encrypt_secret("SEED", "2fa|branch|1")
        self.assertEqual(
            enc.decrypt_secret(encrypted, nonce, key_id, "2fa|branch|1"),
            "SEED")
        with self.assertRaises(InvalidTag):
            enc.decrypt_secret(encrypted, nonce, key_id, "2fa|branch|2")


class ReencryptionTests(TempProjectTestCase):

    def setUp(self):
        super().setUp()
        self.a = self.make_branch("Alpha")
        self.b = self.make_branch("Beta")
        self.admin = self.make_admin("root_admin")

    def test_reencrypt_moves_messages_to_active_key(self):
        first = send_message(self.a, self.b, "first body", subject="One")
        enc.rotate_encryption_key()
        second = send_message(self.a, self.b, "second body", subject="Two")

        status = key_management.key_status()
        self.assertEqual(status["active_key_id"], 2)
        self.assertEqual(status["needs_reencryption"], 1)

        result = key_management.reencrypt_all_messages(self.admin)
        self.assertEqual(result["reencrypted"], 1)
        self.assertEqual(result["skipped"], [])

        self.assertEqual(store.get_message_row(first)["key_id"], 2)
        self.assertEqual(key_management.key_status()["needs_reencryption"], 0)

        opened = open_message(first, self.b)
        self.assertEqual((opened["subject"], opened["body"]),
                         ("One", "first body"))
        self.assertEqual(open_message(second, self.b)["body"], "second body")

    def test_damaged_messages_are_skipped_not_lost(self):
        good = send_message(self.a, self.b, "good", subject="G")
        bad = send_message(self.a, self.b, "bad", subject="B")
        import sqlite3
        connection = sqlite3.connect("database/bank.db")
        connection.execute(
            "UPDATE messages SET receiver_branch_id = 99 WHERE message_id=?",
            (bad,))
        connection.commit()
        connection.close()
        enc.rotate_encryption_key()

        result = key_management.reencrypt_all_messages(self.admin)
        self.assertEqual(result["reencrypted"], 1)
        self.assertEqual(result["skipped"], [bad])
        self.assertEqual(store.get_message_row(good)["key_id"], 2)
        self.assertEqual(store.get_message_row(bad)["key_id"], 1)

    def test_rotation_and_reencryption_are_audited(self):
        key_management.rotate_key(self.admin)
        key_management.reencrypt_all_messages(self.admin)
        from database.database import get_all_admin_activities
        types = [row[2] for row in get_all_admin_activities()]
        self.assertIn("ADMIN_KEY_ROTATED", types)
        self.assertIn("ADMIN_MESSAGES_REENCRYPTED", types)


if __name__ == "__main__":
    unittest.main()

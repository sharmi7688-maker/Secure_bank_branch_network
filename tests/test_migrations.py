import sqlite3
import unittest

from tests.base import TempProjectTestCase
from database.database import (
    log_activity, save_message, get_message_by_id,
)
from database.migrations import run_migrations
from modules.audit_chain import verify_all
from modules.encryption import (
    encrypt_message, generate_encryption_key, decrypt_message,
)
from modules.messaging_service import decrypt_message_row, NO_SUBJECT
from database import store


class LegacyUpgradeTests(TempProjectTestCase):
    """Starts from the ORIGINAL schema, like an existing bank.db."""

    MIGRATE = False

    def setUp(self):
        super().setUp()
        generate_encryption_key()                 # original single key
        self.a = self.make_branch("Alpha")
        self.b = self.make_branch("Beta")

        # legacy log rows written with raw SQL (no hash columns exist yet)
        connection = sqlite3.connect("database/bank.db")
        for i in range(3):
            connection.execute(
                "INSERT INTO activity_logs (branch_id, activity_type, "
                "description, activity_date) VALUES (?,?,?,?)",
                (self.a, "LOGIN", f"legacy {i}", f"2026-01-0{i + 1} 09:00:00"))
        connection.commit()
        connection.close()

        # legacy message encrypted by the ORIGINAL function
        encrypted, nonce = encrypt_message("old style message")
        self.legacy_id = save_message(
            self.a, self.b, encrypted, nonce, "2026-01-05 10:00:00")

    def test_migration_adds_columns_and_tables(self):
        applied = run_migrations()
        self.assertTrue(any("messages.priority" in a for a in applied))

        connection = sqlite3.connect("database/bank.db")
        columns = {r[1] for r in connection.execute(
            "PRAGMA table_info(messages)")}
        tables = {r[0] for r in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        connection.close()

        self.assertTrue({"priority", "key_id", "aad_version",
                         "sender_status", "receiver_status",
                         "parent_message_id"} <= columns)
        self.assertTrue({"two_factor", "audit_chain_head",
                         "schema_meta"} <= tables)

    def test_migration_is_idempotent(self):
        run_migrations()
        self.assertEqual(run_migrations(), [])

    def test_existing_logs_are_sealed_and_verify(self):
        run_migrations()
        results = {r["table"]: r for r in verify_all()}
        self.assertTrue(results["activity_logs"]["ok"])
        self.assertEqual(results["activity_logs"]["checked"], 3)

        log_activity(self.a, "LOGIN", "new row", "2026-02-01 09:00:00")
        self.assertTrue(verify_all()[0]["ok"])

    def test_legacy_message_still_readable_after_upgrade(self):
        run_migrations()
        row = store.get_message_row(self.legacy_id)
        self.assertEqual(row["aad_version"], 1)
        self.assertEqual(row["key_id"], 1)
        subject, body = decrypt_message_row(row)
        self.assertEqual(subject, NO_SUBJECT)
        self.assertEqual(body, "old style message")

        # ...and the original function still works on the original columns
        legacy = get_message_by_id(self.legacy_id)
        self.assertEqual(decrypt_message(legacy[3], legacy[4]),
                         "old style message")

    def test_existing_accounts_keep_working(self):
        run_migrations()
        from modules.auth_service import authenticate_branch
        from tests.base import PASSWORD
        result = authenticate_branch("SB001", PASSWORD)
        self.assertTrue(result.ok)
        self.assertFalse(result.must_change_password)


if __name__ == "__main__":
    unittest.main()

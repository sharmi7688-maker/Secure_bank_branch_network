import sqlite3
import unittest

from tests.base import TempProjectTestCase
from database.database import log_activity, log_admin_activity
from modules.audit_chain import verify_all, verify_chain


def raw(sql, params=()):
    connection = sqlite3.connect("database/bank.db")
    connection.execute(sql, params)
    connection.commit()
    connection.close()


class AuditChainTests(TempProjectTestCase):

    def setUp(self):
        super().setUp()
        self.branch = self.make_branch("Alpha")
        for i in range(5):
            log_activity(self.branch, "TEST", f"event {i}",
                         f"2026-02-01 10:00:0{i}")

    def result(self, table="activity_logs"):
        return verify_chain(table)

    def test_clean_chain_verifies(self):
        result = self.result()
        self.assertTrue(result["ok"])
        self.assertEqual(result["checked"], 5)

    def test_empty_logs_verify(self):
        self.assertTrue(self.result("admin_activity_logs")["ok"])

    def test_edited_row_is_detected(self):
        raw("UPDATE activity_logs SET description='changed' WHERE log_id=3")
        result = self.result()
        self.assertFalse(result["ok"])
        self.assertEqual(result["first_bad_log_id"], 3)
        self.assertIn("modified", result["problems"][0])

    def test_deleted_middle_row_is_detected(self):
        raw("DELETE FROM activity_logs WHERE log_id=2")
        result = self.result()
        self.assertFalse(result["ok"])

    def test_deleted_last_row_is_detected(self):
        raw("DELETE FROM activity_logs WHERE log_id=5")
        result = self.result()
        self.assertFalse(result["ok"])
        self.assertIn("removed", " ".join(result["problems"]))

    def test_all_rows_deleted_is_detected(self):
        raw("DELETE FROM activity_logs")
        self.assertFalse(self.result()["ok"])

    def test_row_inserted_outside_application_is_detected(self):
        raw("INSERT INTO activity_logs (branch_id, activity_type, "
            "description, activity_date) VALUES (1,'FAKE','forged',"
            "'2026-02-01 11:00:00')")
        self.assertFalse(self.result()["ok"])

    def test_attacker_cannot_forge_a_hash_without_the_key(self):
        # attacker edits the row AND "fixes" the hash with plain SHA-256
        import hashlib
        raw("UPDATE activity_logs SET description='changed', entry_hash=? "
            "WHERE log_id=5", (hashlib.sha256(b"x").hexdigest(),))
        self.assertFalse(self.result()["ok"])

    def test_forged_head_record_is_detected(self):
        raw("DELETE FROM activity_logs WHERE log_id=5")
        raw("UPDATE audit_chain_head SET entry_count=4, last_log_id=4 "
            "WHERE table_name='activity_logs'")
        self.assertFalse(self.result()["ok"])

    def test_missing_seal_is_detected(self):
        raw("UPDATE activity_logs SET entry_hash=NULL WHERE log_id=4")
        self.assertFalse(self.result()["ok"])

    def test_admin_chain_is_independent(self):
        admin = self.make_admin("root_admin")
        log_admin_activity(admin, "ADMIN_TEST", "hello", "2026-02-01 12:00:00")
        raw("UPDATE activity_logs SET description='changed' WHERE log_id=1")
        results = {r["table"]: r["ok"] for r in verify_all()}
        self.assertFalse(results["activity_logs"])
        self.assertTrue(results["admin_activity_logs"])


if __name__ == "__main__":
    unittest.main()

import sqlite3
import unittest
from datetime import datetime

from tests.base import TempProjectTestCase
from database.database import (
    get_activities_for_branch, save_message,
)
from modules.encryption import encrypt_message
from modules import messaging_service as ms


def raw(sql, params=()):
    connection = sqlite3.connect("database/bank.db")
    connection.execute(sql, params)
    connection.commit()
    connection.close()


class MessagingTests(TempProjectTestCase):

    def setUp(self):
        super().setUp()
        self.a = self.make_branch("Alpha")
        self.b = self.make_branch("Beta")
        self.c = self.make_branch("Gamma")

    def activity_types(self, branch):
        return [x[2] for x in get_activities_for_branch(branch)]

    # ---- sending / encryption ------------------------------------

    def test_send_and_open(self):
        mid = ms.send_message(self.a, self.b, "Wire transfer ready",
                              subject="Transfer", priority="urgent")
        opened = ms.open_message(mid, self.b)
        self.assertEqual(opened["subject"], "Transfer")
        self.assertEqual(opened["body"], "Wire transfer ready")
        self.assertEqual(opened["priority"], "URGENT")

    def test_subject_and_body_are_not_stored_in_plain_text(self):
        ms.send_message(self.a, self.b, "VerySecretBodyText",
                        subject="VerySecretSubject")
        with open("database/bank.db", "rb") as f:
            data = f.read()
        self.assertNotIn(b"VerySecretBodyText", data)
        self.assertNotIn(b"VerySecretSubject", data)

    def test_default_subject(self):
        mid = ms.send_message(self.a, self.b, "no subject here")
        self.assertEqual(ms.open_message(mid, self.b)["subject"],
                         ms.NO_SUBJECT)

    def test_validation_rules(self):
        bad = [
            dict(receiver_id=self.a, body="x"),                 # self
            dict(receiver_id=999, body="x"),                    # unknown
            dict(receiver_id=self.b, body="   "),               # empty
            dict(receiver_id=self.b, body="x" * 501),           # too long
            dict(receiver_id=self.b, body="x", subject="s" * 81),
            dict(receiver_id=self.b, body="x", priority="LOW"),
        ]
        for kwargs in bad:
            receiver = kwargs.pop("receiver_id")
            with self.assertRaises(ms.MessagingError, msg=str(kwargs)):
                ms.send_message(self.a, receiver, **kwargs)

    def test_send_is_logged_with_priority(self):
        ms.send_message(self.a, self.b, "x", priority="CONFIDENTIAL")
        row = get_activities_for_branch(self.a)[0]
        self.assertEqual(row[2], "MESSAGE_SENT")
        self.assertIn("SB002", row[3])
        self.assertIn("CONFIDENTIAL", row[3])

    # ---- access control & read status ----------------------------

    def test_third_party_cannot_open(self):
        mid = ms.send_message(self.a, self.b, "private")
        with self.assertRaises(PermissionError):
            ms.open_message(mid, self.c)

    def test_receiver_open_marks_read_once(self):
        mid = ms.send_message(self.a, self.b, "hello")
        self.assertEqual(ms.open_message(mid, self.b)["is_read"], 1)
        ms.open_message(mid, self.b)
        self.assertEqual(self.activity_types(self.b).count("MESSAGE_READ"), 1)

    def test_sender_opening_does_not_mark_read(self):
        mid = ms.send_message(self.a, self.b, "hello")
        ms.open_message(mid, self.a)
        inbox = ms.list_box(self.b, "inbox")
        self.assertEqual(inbox[0]["is_read"], 0)

    # ---- replies & threads ---------------------------------------

    def test_reply_and_thread(self):
        first = ms.send_message(self.a, self.b, "Question?", subject="Q")
        reply = ms.send_message(self.b, self.a, "Answer.", subject="Re: Q",
                                parent_id=first)
        third = ms.send_message(self.a, self.b, "Thanks", subject="Re: Q",
                                parent_id=reply)

        thread = ms.get_thread(reply, self.a)
        self.assertEqual([m["message_id"] for m in thread],
                         [first, reply, third])
        self.assertEqual([m["direction"] for m in thread],
                         ["sent", "received", "sent"])
        self.assertEqual(ms.list_box(self.a, "inbox")[0]["parent_message_id"],
                         first)

    def test_cannot_reply_to_someone_elses_message(self):
        first = ms.send_message(self.a, self.b, "hi")
        with self.assertRaises(ms.MessagingError):
            ms.send_message(self.c, self.a, "intruder", parent_id=first)
        with self.assertRaises(ms.MessagingError):
            ms.send_message(self.a, self.b, "self-reply", parent_id=first)

    def test_outsider_cannot_read_thread(self):
        first = ms.send_message(self.a, self.b, "hi")
        with self.assertRaises(PermissionError):
            ms.get_thread(first, self.c)

    # ---- archive / delete ----------------------------------------

    def test_archive_and_restore_affect_only_my_side(self):
        mid = ms.send_message(self.a, self.b, "hi")
        ms.set_status(mid, self.b, "ARCHIVED")
        self.assertEqual(ms.list_box(self.b, "inbox"), [])
        self.assertEqual(len(ms.list_box(self.b, "inbox", "ARCHIVED")), 1)
        self.assertEqual(len(ms.list_box(self.a, "sent")), 1)   # sender unaffected

        ms.set_status(mid, self.b, "ACTIVE")
        self.assertEqual(len(ms.list_box(self.b, "inbox")), 1)

    def test_delete_hides_message_but_keeps_the_row(self):
        mid = ms.send_message(self.a, self.b, "hi")
        ms.set_status(mid, self.b, "DELETED")
        self.assertEqual(ms.list_box(self.b, "inbox"), [])
        with self.assertRaises(ms.MessagingError):
            ms.open_message(mid, self.b)
        self.assertIn("MESSAGE_DELETED", self.activity_types(self.b))
        connection = sqlite3.connect("database/bank.db")
        count = connection.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        connection.close()
        self.assertEqual(count, 1)               # kept for audit

    def test_outsider_cannot_change_status(self):
        mid = ms.send_message(self.a, self.b, "hi")
        with self.assertRaises(PermissionError):
            ms.set_status(mid, self.c, "DELETED")

    # ---- search & filters ----------------------------------------

    def test_search_filters(self):
        ms.send_message(self.a, self.b, "Quarterly audit schedule",
                        subject="Audit")
        ms.send_message(self.c, self.b, "Cash vault inspection",
                        subject="Vault", priority="URGENT")
        ms.send_message(self.a, self.b, "Lunch menu", subject="Misc",
                        now=datetime(2026, 3, 1, 9, 0, 0))

        def find(**kw):
            return [m["subject"] for m in ms.list_box(self.b, "inbox", **kw)]

        self.assertEqual(sorted(find(keyword="audit")), ["Audit"])
        self.assertEqual(find(keyword="VAULT INSPECTION"), ["Vault"])   # body, case-insens.
        self.assertEqual(find(keyword="nothing-matches"), [])
        self.assertEqual(find(priority="URGENT"), ["Vault"])
        self.assertEqual(sorted(find(other_branch_id=self.a)),
                         ["Audit", "Misc"])
        self.assertEqual(find(date_to="2026-03-01"), ["Misc"])
        self.assertEqual(len(find(date_from="2026-03-02")), 2)

        mid = ms.list_box(self.b, "inbox", keyword="vault")[0]["message_id"]
        ms.open_message(mid, self.b)
        self.assertEqual(len(find(unread_only=True)), 2)

    # ---- tampering -----------------------------------------------

    def test_moving_a_message_to_another_branch_is_detected(self):
        mid = ms.send_message(self.a, self.b, "for Beta only")
        raw("UPDATE messages SET receiver_branch_id=? WHERE message_id=?",
            (self.c, mid))
        with self.assertRaises(ms.MessageIntegrityError):
            ms.open_message(mid, self.c)
        listed = ms.list_box(self.c, "inbox")[0]
        self.assertFalse(listed["intact"])

    def test_changing_the_sender_or_date_is_detected(self):
        mid = ms.send_message(self.a, self.b, "hello")
        raw("UPDATE messages SET sender_branch_id=? WHERE message_id=?",
            (self.c, mid))
        with self.assertRaises(ms.MessageIntegrityError):
            ms.open_message(mid, self.b)

        mid2 = ms.send_message(self.a, self.b, "hello again")
        raw("UPDATE messages SET sent_date='2000-01-01 00:00:00' "
            "WHERE message_id=?", (mid2,))
        with self.assertRaises(ms.MessageIntegrityError):
            ms.open_message(mid2, self.b)

    def test_modified_ciphertext_is_detected(self):
        mid = ms.send_message(self.a, self.b, "hello")
        raw("UPDATE messages SET encrypted_message='AAAA' || "
            "substr(encrypted_message, 5) WHERE message_id=?", (mid,))
        with self.assertRaises(ms.MessageIntegrityError):
            ms.open_message(mid, self.b)

    # ---- legacy messages -----------------------------------------

    def test_original_format_messages_still_work(self):
        encrypted, nonce = encrypt_message("written by v1")
        # (the original key IS key version 1)
        legacy_id = save_message(self.a, self.b, encrypted, nonce,
                                 "2026-01-01 10:00:00")
        listed = ms.list_box(self.b, "inbox")
        self.assertEqual(listed[0]["subject"], ms.NO_SUBJECT)
        opened = ms.open_message(legacy_id, self.b)
        self.assertEqual(opened["body"], "written by v1")


if __name__ == "__main__":
    unittest.main()

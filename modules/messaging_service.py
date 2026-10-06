"""
SECURE MESSAGING SERVICE
========================

Subject, priority, reply threads, archive/delete and search on top of the
AES-256-GCM message store.

* v2 messages encrypt the SUBJECT and the BODY together and bind the
  ciphertext to (sender, receiver, sent time). Priority is stored as
  readable metadata so administrators can see urgency without ever seeing
  content.
* Messages created by the original version (aad_version = 1) are still
  readable; they simply have no subject.
"""

import json
from datetime import datetime

from cryptography.exceptions import InvalidTag

from database import store
from database.database import (
    get_branch_by_id, log_activity, mark_message_as_read,
)
from modules import encryption as enc

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
PRIORITIES = ("NORMAL", "URGENT", "CONFIDENTIAL")
MAX_SUBJECT = 80
MAX_BODY = 500
NO_SUBJECT = "(No subject)"
UNREADABLE_SUBJECT = "Unreadable message (integrity check failed)"


class MessagingError(ValueError):
    """A rule was broken (empty text, wrong receiver, ...)."""


class MessageIntegrityError(Exception):
    """The ciphertext was modified, moved, or the key does not match."""


def branch_code(branch_id):
    return f"SB{branch_id:03d}"


# ---------------------------------------------------------
# DECRYPTION
# ---------------------------------------------------------

def decrypt_message_row(row):
    """Returns (subject, body) for a message row dict from the store."""

    aad = None
    if row["aad_version"] >= 2:
        aad = enc.build_message_aad(
            row["sender_branch_id"], row["receiver_branch_id"],
            row["sent_date"],
        )

    try:
        plaintext = enc.decrypt_payload(
            row["encrypted_message"], row["nonce"], row["key_id"], aad
        )
        if row["aad_version"] >= 2:
            return enc.unpack_message(plaintext)
        return NO_SUBJECT, plaintext
    except (InvalidTag, ValueError, KeyError, json.JSONDecodeError):
        raise MessageIntegrityError(
            "Unable to decrypt this message. It may have been modified, "
            "moved or corrupted."
        )


# ---------------------------------------------------------
# SENDING
# ---------------------------------------------------------

def send_message(sender_id, receiver_id, body, subject="",
                 priority="NORMAL", parent_id=None, now=None):
    """Validates, encrypts and stores a message. Returns the message id."""

    if sender_id == receiver_id:
        raise MessagingError("You cannot send a message to your own branch.")

    if get_branch_by_id(receiver_id) is None:
        raise MessagingError("Receiver branch does not exist.")

    body = (body or "").strip()
    if not body:
        raise MessagingError("Message cannot be empty.")
    if len(body) > MAX_BODY:
        raise MessagingError(
            f"Message is too long. Maximum allowed length is {MAX_BODY} "
            "characters."
        )

    subject = (subject or "").strip()
    if len(subject) > MAX_SUBJECT:
        raise MessagingError(
            f"Subject is too long. Maximum allowed length is {MAX_SUBJECT} "
            "characters."
        )
    if not subject:
        subject = NO_SUBJECT

    priority = (priority or "NORMAL").upper()
    if priority not in PRIORITIES:
        raise MessagingError("Invalid priority.")

    if parent_id is not None:
        parent = store.get_message_row(parent_id)
        if (parent is None
                or parent["receiver_branch_id"] != sender_id
                or parent["sender_branch_id"] != receiver_id):
            raise MessagingError(
                "You can only reply to a message you received, and the "
                "reply must go back to its sender."
            )

    moment = now if now is not None else datetime.now()
    sent_date = moment.strftime(DATETIME_FORMAT)

    aad = enc.build_message_aad(sender_id, receiver_id, sent_date)
    encrypted, nonce, key_id = enc.encrypt_payload(
        enc.pack_message(subject, body), aad=aad
    )

    message_id = store.insert_message_v2(
        sender_id, receiver_id, encrypted, nonce, sent_date,
        priority, parent_id, key_id,
    )

    verb = "Reply sent to" if parent_id else "Message sent to"
    tag = "" if priority == "NORMAL" else f" [{priority}]"
    log_activity(
        sender_id, "MESSAGE_SENT",
        f"{verb} {branch_code(receiver_id)}{tag}", sent_date,
    )

    return message_id


# ---------------------------------------------------------
# READING
# ---------------------------------------------------------

def _message_view(row, subject, body):
    return {
        "message_id": row["message_id"],
        "sender_branch_id": row["sender_branch_id"],
        "receiver_branch_id": row["receiver_branch_id"],
        "subject": subject,
        "body": body,
        "priority": row["priority"],
        "sent_date": row["sent_date"],
        "is_read": row["is_read"],
        "parent_message_id": row["parent_message_id"],
        "key_id": row["key_id"],
    }


def _visible_to(row, viewer_id):
    """The viewer must be a party to the message and must not have
    deleted it from their own side."""

    if viewer_id == row["receiver_branch_id"]:
        return row["receiver_status"] != "DELETED"
    if viewer_id == row["sender_branch_id"]:
        return row["sender_status"] != "DELETED"
    return False


def open_message(message_id, viewer_id, mark_read=True, now=None):
    """Decrypts a message for one of its two parties.

    Only the sender and the receiver may open it (PermissionError
    otherwise). When the receiver opens a new message it is marked as read
    and a MESSAGE_READ activity is logged."""

    row = store.get_message_row(message_id)
    if row is None:
        raise MessagingError("Message not found.")

    if viewer_id not in (row["sender_branch_id"], row["receiver_branch_id"]):
        raise PermissionError("You are not allowed to read this message.")

    if not _visible_to(row, viewer_id):
        raise MessagingError("Message not found.")

    subject, body = decrypt_message_row(row)

    if (mark_read and viewer_id == row["receiver_branch_id"]
            and row["is_read"] == 0):
        if mark_message_as_read(message_id, viewer_id) == 1:
            log_activity(
                viewer_id, "MESSAGE_READ",
                f"Message read from {branch_code(row['sender_branch_id'])}",
                (now or datetime.now()).strftime(DATETIME_FORMAT),
            )
            row["is_read"] = 1

    return _message_view(row, subject, body)


def list_box(viewer_id, box, status="ACTIVE", keyword="", priority=None,
             other_branch_id=None, date_from=None, date_to=None,
             unread_only=False):
    """
    Lists a branch's inbox ('inbox') or sent items ('sent'), optionally
    filtered. The keyword searches the decrypted subject and body; messages
    that fail their integrity check never match a keyword.

    Returns dicts with metadata + subject (the body is only returned by
    open_message).
    """

    keyword = (keyword or "").strip().lower()
    date_from = str(date_from) if date_from else None
    date_to = str(date_to) if date_to else None

    results = []

    for row in store.list_message_rows(viewer_id, box, status):
        other = (row["sender_branch_id"] if box == "inbox"
                 else row["receiver_branch_id"])

        if priority and row["priority"] != priority:
            continue
        if other_branch_id and other != other_branch_id:
            continue
        if unread_only and row["is_read"] != 0:
            continue

        day = row["sent_date"][:10]
        if date_from and day < date_from:
            continue
        if date_to and day > date_to:
            continue

        try:
            subject, body = decrypt_message_row(row)
            intact = True
        except MessageIntegrityError:
            subject, body, intact = UNREADABLE_SUBJECT, "", False

        if keyword:
            if not intact:
                continue
            if keyword not in subject.lower() and keyword not in body.lower():
                continue

        results.append({
            "message_id": row["message_id"],
            "other_branch_id": other,
            "subject": subject,
            "priority": row["priority"],
            "sent_date": row["sent_date"],
            "is_read": row["is_read"],
            "parent_message_id": row["parent_message_id"],
            "intact": intact,
        })

    return results


def get_thread(message_id, viewer_id):
    """The whole reply thread containing `message_id`, oldest first.
    Does not mark anything as read."""

    start = store.get_message_row(message_id)
    if start is None:
        raise MessagingError("Message not found.")
    if viewer_id not in (start["sender_branch_id"],
                         start["receiver_branch_id"]):
        raise PermissionError("You are not allowed to read this thread.")

    thread = []
    for row in store.get_thread_rows(message_id):
        if not _visible_to(row, viewer_id):
            continue
        try:
            subject, body = decrypt_message_row(row)
        except MessageIntegrityError:
            subject, body = UNREADABLE_SUBJECT, ""
        view = _message_view(row, subject, body)
        view["direction"] = (
            "sent" if row["sender_branch_id"] == viewer_id else "received"
        )
        thread.append(view)

    return thread


# ---------------------------------------------------------
# ARCHIVE / DELETE
# ---------------------------------------------------------

_STATUS_EVENTS = {
    "ARCHIVED": ("MESSAGE_ARCHIVED", "Message archived"),
    "DELETED": ("MESSAGE_DELETED", "Message deleted"),
    "ACTIVE": ("MESSAGE_RESTORED", "Message restored"),
}


def set_status(message_id, viewer_id, status, now=None):
    """Archive, delete or restore a message FROM THE VIEWER'S OWN SIDE.
    The other party's copy is never affected, and the row is kept for
    audit purposes."""

    if status not in _STATUS_EVENTS:
        raise MessagingError("Invalid message status.")

    row = store.get_message_row(message_id)
    if row is None or viewer_id not in (row["sender_branch_id"],
                                        row["receiver_branch_id"]):
        raise PermissionError("You are not allowed to change this message.")

    store.set_message_status(message_id, viewer_id, status)

    event, text = _STATUS_EVENTS[status]
    log_activity(
        viewer_id, event, f"{text} (#{message_id})",
        (now or datetime.now()).strftime(DATETIME_FORMAT),
    )
    return True

"""
ENCRYPTION KEY MANAGEMENT (administrator functions)
===================================================

* rotate_key()            creates a new key version; new messages use it.
* reencrypt_all_messages() moves every older message to the active key and
                           upgrades v1 messages to the v2 format (subject
                           field + authenticated sender/receiver/date).
                           Runs inside the system; contents are never shown.
"""

from datetime import datetime

from database import store
from database.connection import connect
from database.database import log_admin_activity
from modules import encryption as enc
from modules.messaging_service import (
    NO_SUBJECT, MessageIntegrityError, decrypt_message_row,
)

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _now():
    return datetime.now().strftime(DATETIME_FORMAT)


def key_status():
    """Overview for the admin dashboard."""

    ids = enc.list_key_ids()
    active = ids[-1] if ids else None

    connection = connect()
    try:
        by_key = dict(connection.execute(
            "SELECT key_id, COUNT(*) FROM messages GROUP BY key_id"
        ).fetchall())
        legacy = connection.execute(
            "SELECT COUNT(*) FROM messages WHERE aad_version < 2"
        ).fetchone()[0]
        total = connection.execute(
            "SELECT COUNT(*) FROM messages"
        ).fetchone()[0]
        pending = connection.execute(
            "SELECT COUNT(*) FROM messages "
            "WHERE key_id != ? OR aad_version < 2",
            (active if active is not None else -1,),
        ).fetchone()[0]
    finally:
        connection.close()

    return {
        "key_ids": ids,
        "active_key_id": active,
        "messages_by_key": by_key,
        "total_messages": total,
        "legacy_format_messages": legacy,
        "needs_reencryption": pending,
    }


def rotate_key(admin_id):
    """Creates a new active key version. Returns the new key id."""

    new_id = enc.rotate_encryption_key()
    log_admin_activity(
        admin_id, "ADMIN_KEY_ROTATED",
        f"Encryption key rotated: key version {new_id} is now active",
        _now(),
    )
    return new_id


def reencrypt_all_messages(admin_id):
    """
    Re-encrypts every message that is not yet on the active key in the
    v2 format. All-or-nothing: one transaction. Messages that fail their
    integrity check are skipped and reported (they cannot be re-encrypted).

    Returns {"reencrypted": n, "skipped": [message ids]}.
    """

    active = enc.get_active_key_id()
    reencrypted, skipped = 0, []

    connection = connect()
    try:
        connection.execute("BEGIN IMMEDIATE")

        ids = [r[0] for r in connection.execute(
            "SELECT message_id FROM messages "
            "WHERE key_id != ? OR aad_version < 2 ORDER BY message_id",
            (active,),
        ).fetchall()]

        for message_id in ids:
            row = store.get_message_row(message_id)

            try:
                subject, body = decrypt_message_row(row)
            except MessageIntegrityError:
                skipped.append(message_id)
                continue

            aad = enc.build_message_aad(
                row["sender_branch_id"], row["receiver_branch_id"],
                row["sent_date"],
            )
            encrypted, nonce, key_id = enc.encrypt_payload(
                enc.pack_message(subject or NO_SUBJECT, body),
                aad=aad, key_id=active,
            )
            store.update_message_encryption(
                message_id, encrypted, nonce, key_id, 2,
                connection=connection,
            )
            reencrypted += 1

        connection.commit()

    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    log_admin_activity(
        admin_id, "ADMIN_MESSAGES_REENCRYPTED",
        f"Re-encrypted {reencrypted} message(s) with key version {active}"
        + (f"; skipped {len(skipped)} damaged message(s)" if skipped else ""),
        _now(),
    )

    return {"reencrypted": reencrypted, "skipped": skipped}

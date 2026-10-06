"""
DATA ACCESS FOR THE ENHANCED FEATURES
=====================================

Two-factor records, password updates and the v2 message store.
(Legacy queries stay in database/database.py.)

Every function opens and closes its own connection, like the rest of the
project, and uses parameterised SQL only.
"""

from database.connection import connect

ACCOUNT_TYPES = ("branch", "admin")
MESSAGE_STATUSES = ("ACTIVE", "ARCHIVED", "DELETED")

_MESSAGE_COLUMNS = (
    "message_id, sender_branch_id, receiver_branch_id, encrypted_message, "
    "nonce, sent_date, is_read, priority, parent_message_id, key_id, "
    "aad_version, sender_status, receiver_status"
)

_MESSAGE_KEYS = (
    "message_id", "sender_branch_id", "receiver_branch_id",
    "encrypted_message", "nonce", "sent_date", "is_read", "priority",
    "parent_message_id", "key_id", "aad_version", "sender_status",
    "receiver_status",
)


def _check_type(account_type):
    if account_type not in ACCOUNT_TYPES:
        raise ValueError("account_type must be 'branch' or 'admin'.")


def _row_to_message(row):
    return dict(zip(_MESSAGE_KEYS, row)) if row else None


# ---------------------------------------------------------
# TWO-FACTOR AUTHENTICATION
# ---------------------------------------------------------

def get_two_factor(account_type, account_id):
    """Returns dict(secret_enc, nonce, key_id, enabled, last_step,
    enabled_date) or None."""

    _check_type(account_type)
    connection = connect()
    try:
        row = connection.execute(
            """
            SELECT secret_enc, nonce, key_id, enabled, last_step, enabled_date
            FROM two_factor WHERE account_type = ? AND account_id = ?
            """,
            (account_type, account_id),
        ).fetchone()
    finally:
        connection.close()

    if row is None:
        return None

    return {
        "secret_enc": row[0], "nonce": row[1], "key_id": row[2],
        "enabled": bool(row[3]), "last_step": row[4],
        "enabled_date": row[5],
    }


def save_pending_two_factor(account_type, account_id,
                            secret_enc, nonce, key_id):
    """Stores a not-yet-confirmed secret (enabled = 0)."""

    _check_type(account_type)
    connection = connect()
    try:
        connection.execute(
            """
            INSERT INTO two_factor
                (account_type, account_id, secret_enc, nonce, key_id,
                 enabled, last_step, enabled_date)
            VALUES (?, ?, ?, ?, ?, 0, 0, NULL)
            ON CONFLICT(account_type, account_id) DO UPDATE SET
                secret_enc = excluded.secret_enc,
                nonce = excluded.nonce,
                key_id = excluded.key_id,
                enabled = 0, last_step = 0, enabled_date = NULL
            """,
            (account_type, account_id, secret_enc, nonce, key_id),
        )
        connection.commit()
    finally:
        connection.close()


def enable_two_factor(account_type, account_id, last_step, enabled_date):
    _check_type(account_type)
    connection = connect()
    try:
        cursor = connection.execute(
            """
            UPDATE two_factor
            SET enabled = 1, last_step = ?, enabled_date = ?
            WHERE account_type = ? AND account_id = ?
            """,
            (last_step, enabled_date, account_type, account_id),
        )
        connection.commit()
        return cursor.rowcount == 1
    finally:
        connection.close()


def consume_totp_step(account_type, account_id, step):
    """
    Atomically records that `step` was used. Returns False if this step (or
    a later one) was already used — i.e. the code is being replayed.
    """

    _check_type(account_type)
    connection = connect()
    try:
        cursor = connection.execute(
            """
            UPDATE two_factor SET last_step = ?
            WHERE account_type = ? AND account_id = ?
              AND enabled = 1 AND last_step < ?
            """,
            (step, account_type, account_id, step),
        )
        connection.commit()
        return cursor.rowcount == 1
    finally:
        connection.close()


def delete_two_factor(account_type, account_id):
    _check_type(account_type)
    connection = connect()
    try:
        cursor = connection.execute(
            "DELETE FROM two_factor WHERE account_type = ? AND account_id = ?",
            (account_type, account_id),
        )
        connection.commit()
        return cursor.rowcount
    finally:
        connection.close()


def count_two_factor_enabled(account_type):
    _check_type(account_type)
    connection = connect()
    try:
        return connection.execute(
            "SELECT COUNT(*) FROM two_factor "
            "WHERE account_type = ? AND enabled = 1",
            (account_type,),
        ).fetchone()[0]
    finally:
        connection.close()


# ---------------------------------------------------------
# PASSWORDS
# ---------------------------------------------------------

def get_credentials(account_type, account_id):
    """Returns (name, password_hash, password_salt) or None.
    name = branch_name for branches, username for admins."""

    _check_type(account_type)
    if account_type == "branch":
        sql = ("SELECT branch_name, password_hash, password_salt "
               "FROM branches WHERE branch_id = ?")
    else:
        sql = ("SELECT username, password_hash, password_salt "
               "FROM admins WHERE admin_id = ?")

    connection = connect()
    try:
        return connection.execute(sql, (account_id,)).fetchone()
    finally:
        connection.close()


def update_password(account_type, account_id, password_hash,
                    password_salt, changed_date):
    """Stores a new password hash and clears any forced-change flag."""

    _check_type(account_type)
    table, id_col = (
        ("branches", "branch_id") if account_type == "branch"
        else ("admins", "admin_id")
    )

    connection = connect()
    try:
        cursor = connection.execute(
            f"""
            UPDATE {table}
            SET password_hash = ?, password_salt = ?,
                password_changed_date = ?, must_change_password = 0,
                temp_password_expires = NULL
            WHERE {id_col} = ?
            """,
            (password_hash, password_salt, changed_date, account_id),
        )
        connection.commit()
        return cursor.rowcount == 1
    finally:
        connection.close()


def set_must_change_password(account_type, account_id, flag):
    _check_type(account_type)
    table, id_col = (
        ("branches", "branch_id") if account_type == "branch"
        else ("admins", "admin_id")
    )

    connection = connect()
    try:
        cursor = connection.execute(
            f"UPDATE {table} SET must_change_password = ? WHERE {id_col} = ?",
            (1 if flag else 0, account_id),
        )
        connection.commit()
        return cursor.rowcount == 1
    finally:
        connection.close()


def get_must_change_password(account_type, account_id):
    _check_type(account_type)
    table, id_col = (
        ("branches", "branch_id") if account_type == "branch"
        else ("admins", "admin_id")
    )

    connection = connect()
    try:
        row = connection.execute(
            f"SELECT must_change_password FROM {table} WHERE {id_col} = ?",
            (account_id,),
        ).fetchone()
    finally:
        connection.close()

    return bool(row[0]) if row else False


def set_temporary_password(account_type, account_id, password_hash,
                           password_salt, expires):
    """Stores an administrator-issued temporary password: the account must
    change it at next sign-in and it stops working after `expires`.
    (password_changed_date is deliberately left alone: the account holder
    did not change it.)"""

    _check_type(account_type)
    table, id_col = (
        ("branches", "branch_id") if account_type == "branch"
        else ("admins", "admin_id")
    )

    connection = connect()
    try:
        cursor = connection.execute(
            f"""
            UPDATE {table}
            SET password_hash = ?, password_salt = ?,
                must_change_password = 1, temp_password_expires = ?
            WHERE {id_col} = ?
            """,
            (password_hash, password_salt, expires, account_id),
        )
        connection.commit()
        return cursor.rowcount == 1
    finally:
        connection.close()


def get_temp_password_expiry(account_type, account_id):
    """'YYYY-MM-DD HH:MM:SS' or None when no temporary password is active."""

    _check_type(account_type)
    table, id_col = (
        ("branches", "branch_id") if account_type == "branch"
        else ("admins", "admin_id")
    )

    connection = connect()
    try:
        row = connection.execute(
            f"SELECT temp_password_expires FROM {table} WHERE {id_col} = ?",
            (account_id,),
        ).fetchone()
    finally:
        connection.close()

    return row[0] if row else None


def get_password_changed_date(account_type, account_id):
    _check_type(account_type)
    table, id_col = (
        ("branches", "branch_id") if account_type == "branch"
        else ("admins", "admin_id")
    )

    connection = connect()
    try:
        row = connection.execute(
            f"SELECT password_changed_date FROM {table} WHERE {id_col} = ?",
            (account_id,),
        ).fetchone()
    finally:
        connection.close()

    return row[0] if row else None


# ---------------------------------------------------------
# MESSAGES (v2)
# ---------------------------------------------------------

def insert_message_v2(sender_id, receiver_id, encrypted_message, nonce,
                      sent_date, priority, parent_message_id, key_id):
    connection = connect()
    try:
        cursor = connection.execute(
            """
            INSERT INTO messages (
                sender_branch_id, receiver_branch_id, encrypted_message,
                nonce, sent_date, priority, parent_message_id,
                key_id, aad_version
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 2)
            """,
            (sender_id, receiver_id, encrypted_message, nonce, sent_date,
             priority, parent_message_id, key_id),
        )
        connection.commit()
        return cursor.lastrowid
    finally:
        connection.close()


def get_message_row(message_id):
    connection = connect()
    try:
        row = connection.execute(
            f"SELECT {_MESSAGE_COLUMNS} FROM messages WHERE message_id = ?",
            (message_id,),
        ).fetchone()
    finally:
        connection.close()
    return _row_to_message(row)


def list_message_rows(branch_id, box, status="ACTIVE"):
    """box = 'inbox' (received) or 'sent'. status filters the viewer's own
    side of the message. Newest first."""

    if box == "inbox":
        where = "receiver_branch_id = ? AND receiver_status = ?"
    elif box == "sent":
        where = "sender_branch_id = ? AND sender_status = ?"
    else:
        raise ValueError("box must be 'inbox' or 'sent'.")

    if status not in MESSAGE_STATUSES:
        raise ValueError("Invalid message status.")

    connection = connect()
    try:
        rows = connection.execute(
            f"SELECT {_MESSAGE_COLUMNS} FROM messages "
            f"WHERE {where} ORDER BY message_id DESC",
            (branch_id, status),
        ).fetchall()
    finally:
        connection.close()

    return [_row_to_message(r) for r in rows]


def set_message_status(message_id, branch_id, status):
    """Changes the viewer's own side (receiver or sender) of a message.
    Returns True if the branch is a party to the message."""

    if status not in MESSAGE_STATUSES:
        raise ValueError("Invalid message status.")

    connection = connect()
    try:
        changed = 0
        for column, owner in (("receiver_status", "receiver_branch_id"),
                              ("sender_status", "sender_branch_id")):
            cursor = connection.execute(
                f"UPDATE messages SET {column} = ? "
                f"WHERE message_id = ? AND {owner} = ?",
                (status, message_id, branch_id),
            )
            changed += cursor.rowcount
        connection.commit()
        return changed > 0
    finally:
        connection.close()


def get_thread_rows(message_id):
    """All messages in the same reply thread, oldest first."""

    connection = connect()
    try:
        # climb to the root
        root = message_id
        for _ in range(100):
            row = connection.execute(
                "SELECT parent_message_id FROM messages WHERE message_id = ?",
                (root,),
            ).fetchone()
            if row is None or row[0] is None:
                break
            root = row[0]

        # walk down through replies
        found, frontier = [root], [root]
        while frontier and len(found) < 500:
            marks = ",".join("?" * len(frontier))
            children = connection.execute(
                f"SELECT message_id FROM messages "
                f"WHERE parent_message_id IN ({marks})",
                frontier,
            ).fetchall()
            frontier = [c[0] for c in children if c[0] not in found]
            found.extend(frontier)

        marks = ",".join("?" * len(found))
        rows = connection.execute(
            f"SELECT {_MESSAGE_COLUMNS} FROM messages "
            f"WHERE message_id IN ({marks}) ORDER BY message_id",
            found,
        ).fetchall()
    finally:
        connection.close()

    return [_row_to_message(r) for r in rows]


def update_message_encryption(message_id, encrypted_message, nonce, key_id,
                              aad_version, connection=None):
    """Used by key re-encryption. Pass an open connection to make a whole
    batch atomic."""

    own = connection is None
    if own:
        connection = connect()
    try:
        connection.execute(
            """
            UPDATE messages
            SET encrypted_message = ?, nonce = ?, key_id = ?, aad_version = ?
            WHERE message_id = ?
            """,
            (encrypted_message, nonce, key_id, aad_version, message_id),
        )
        if own:
            connection.commit()
    finally:
        if own:
            connection.close()

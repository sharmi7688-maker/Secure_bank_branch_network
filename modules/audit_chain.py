"""
TAMPER-EVIDENT AUDIT LOG
========================

Every row written to activity_logs / admin_activity_logs is "sealed" with an
HMAC-SHA256 that also covers the hash of the previous row:

    entry_hash = HMAC(audit_key, prev_hash + table + log_id + actor +
                                 activity_type + description + date)

Because each hash depends on the one before it, editing or deleting any row
breaks every hash after it. A small "head" record (last id, last hash, row
count, HMAC) additionally detects rows removed from the END of the log.

The HMAC key lives in config/audit.key (never in the database), so someone
who can only edit bank.db cannot recompute a valid chain.
"""

import base64
import hashlib
import hmac
import os

from database.connection import connect

AUDIT_KEY_FILE = os.path.join("config", "audit.key")
GENESIS = "GENESIS"

# table name -> actor column. Whitelisted: names are never user input.
AUDIT_TABLES = {
    "activity_logs": "branch_id",
    "admin_activity_logs": "admin_id",
}


# ---------------------------------------------------------
# KEY HANDLING
# ---------------------------------------------------------

def load_audit_key():
    """Returns the 32-byte audit key, creating it on first use."""

    if not os.path.exists(AUDIT_KEY_FILE):
        os.makedirs(os.path.dirname(AUDIT_KEY_FILE), exist_ok=True)
        key_text = base64.b64encode(os.urandom(32)).decode("utf-8")
        try:
            fd = os.open(
                AUDIT_KEY_FILE,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                file.write(key_text)
        except FileExistsError:
            pass  # another session created it first

    with open(AUDIT_KEY_FILE, "r", encoding="utf-8") as file:
        return base64.b64decode(file.read().strip())


def _field(value):
    """Length-prefixed encoding so field boundaries are unambiguous."""
    text = "" if value is None else str(value)
    return f"{len(text)}:{text}"


def compute_entry_hash(key, prev_hash, table, log_id, actor_id,
                       activity_type, description, activity_date):
    message = "|".join(
        _field(part)
        for part in (prev_hash, table, log_id, actor_id,
                     activity_type, description, activity_date)
    )
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).hexdigest()


def _head_mac(key, table, last_id, last_hash, count):
    message = "|".join(_field(p) for p in (table, last_id, last_hash, count))
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).hexdigest()


# ---------------------------------------------------------
# SCHEMA
# ---------------------------------------------------------

def ensure_audit_schema(connection):
    """Adds the hash columns and the head table if they are missing.
    Safe to call repeatedly."""

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_chain_head (
            table_name TEXT PRIMARY KEY,
            last_log_id INTEGER NOT NULL,
            last_hash TEXT NOT NULL,
            entry_count INTEGER NOT NULL,
            head_mac TEXT NOT NULL
        )
    """)

    for table in AUDIT_TABLES:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = {row[1] for row in cursor.fetchall()}
        if not columns:
            continue  # table not created yet
        if "prev_hash" not in columns:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN prev_hash TEXT")
        if "entry_hash" not in columns:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN entry_hash TEXT")


# ---------------------------------------------------------
# SEALING (called inside the writer's open transaction)
# ---------------------------------------------------------

def seal_entry(connection, table, log_id):
    """Computes and stores the chained hash for one freshly inserted row."""

    if table not in AUDIT_TABLES:
        raise ValueError("Unknown audit table.")

    actor_col = AUDIT_TABLES[table]
    key = load_audit_key()
    cursor = connection.cursor()

    ensure_audit_schema(connection)

    cursor.execute(
        f"""
        SELECT {actor_col}, activity_type, description, activity_date
        FROM {table} WHERE log_id = ?
        """,
        (log_id,),
    )
    row = cursor.fetchone()
    if row is None:
        raise ValueError("Audit row not found.")

    cursor.execute(
        "SELECT last_hash, entry_count FROM audit_chain_head "
        "WHERE table_name = ?",
        (table,),
    )
    head = cursor.fetchone()
    prev_hash = head[0] if head else GENESIS
    count = (head[1] if head else 0) + 1

    entry_hash = compute_entry_hash(key, prev_hash, table, log_id, *row)

    cursor.execute(
        f"UPDATE {table} SET prev_hash = ?, entry_hash = ? WHERE log_id = ?",
        (prev_hash, entry_hash, log_id),
    )
    cursor.execute(
        """
        INSERT INTO audit_chain_head
            (table_name, last_log_id, last_hash, entry_count, head_mac)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(table_name) DO UPDATE SET
            last_log_id = excluded.last_log_id,
            last_hash   = excluded.last_hash,
            entry_count = excluded.entry_count,
            head_mac    = excluded.head_mac
        """,
        (table, log_id, entry_hash, count,
         _head_mac(key, table, log_id, entry_hash, count)),
    )


def seal_existing_rows(connection):
    """One-time baseline: chains every row that has no hash yet, in id order.
    Used by the migration for logs created before this feature existed."""

    ensure_audit_schema(connection)
    cursor = connection.cursor()
    sealed = 0
    for table in AUDIT_TABLES:
        cursor.execute(
            f"SELECT log_id FROM {table} WHERE entry_hash IS NULL "
            "ORDER BY log_id"
        )
        for (log_id,) in cursor.fetchall():
            seal_entry(connection, table, log_id)
            sealed += 1
    return sealed


# ---------------------------------------------------------
# VERIFICATION
# ---------------------------------------------------------

def verify_chain(table):
    """Checks one log table. Returns a dict:
        table, ok, checked, problems (list of text), first_bad_log_id
    """

    if table not in AUDIT_TABLES:
        raise ValueError("Unknown audit table.")

    actor_col = AUDIT_TABLES[table]
    key = load_audit_key()
    problems = []
    first_bad = None

    connection = connect()
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            SELECT log_id, {actor_col}, activity_type, description,
                   activity_date, prev_hash, entry_hash
            FROM {table} ORDER BY log_id
            """
        )
        rows = cursor.fetchall()

        cursor.execute(
            "SELECT last_log_id, last_hash, entry_count, head_mac "
            "FROM audit_chain_head WHERE table_name = ?",
            (table,),
        )
        head = cursor.fetchone()
    finally:
        connection.close()

    def flag(log_id, text):
        nonlocal first_bad
        problems.append(text)
        if first_bad is None:
            first_bad = log_id

    expected_prev = GENESIS
    for (log_id, actor, a_type, desc, a_date, prev_hash, entry_hash) in rows:

        if entry_hash is None or prev_hash is None:
            flag(log_id, f"Entry #{log_id} has no integrity seal.")
            continue

        if not hmac.compare_digest(prev_hash, expected_prev):
            flag(log_id, f"Entry #{log_id}: chain is broken "
                         "(an earlier entry was removed or changed).")

        recomputed = compute_entry_hash(
            key, prev_hash, table, log_id, actor, a_type, desc, a_date
        )
        if not hmac.compare_digest(recomputed, entry_hash):
            flag(log_id, f"Entry #{log_id}: content was modified.")

        expected_prev = entry_hash

    # Head record: catches rows removed from the end of the log
    if rows or head:
        if head is None:
            flag(None, "Chain head record is missing.")
        else:
            h_id, h_hash, h_count, h_mac = head
            expected_mac = _head_mac(key, table, h_id, h_hash, h_count)
            if not hmac.compare_digest(expected_mac, h_mac):
                flag(None, "Chain head record was modified.")
            elif not rows:
                flag(None, "All log entries were deleted.")
            else:
                last = rows[-1]
                if h_count != len(rows) or h_id != last[0] \
                        or last[6] is None \
                        or not hmac.compare_digest(h_hash, last[6]):
                    flag(None, "Entries were added or removed outside "
                               "the application.")

    return {
        "table": table,
        "ok": not problems,
        "checked": len(rows),
        "problems": problems,
        "first_bad_log_id": first_bad,
    }


def verify_all():
    """Verifies both log tables. Returns a list of result dicts."""
    return [verify_chain(table) for table in AUDIT_TABLES]

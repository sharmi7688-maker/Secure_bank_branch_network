"""
DATABASE MIGRATIONS
===================

Upgrades an existing bank.db (from the original project) to the enhanced
schema WITHOUT losing data. Every step is idempotent, so run_migrations()
can be called on every start-up.

New in this version:
  * branches / admins   : must_change_password, password_changed_date,
                          temp_password_expires
  * messages            : priority, parent_message_id, key_id, aad_version,
                          sender_status, receiver_status
  * activity logs       : prev_hash, entry_hash  (tamper-evident chain)
  * new tables          : two_factor, audit_chain_head, schema_meta
"""

from database.connection import connect
from modules.audit_chain import ensure_audit_schema, seal_existing_rows

SCHEMA_VERSION = 2

COLUMN_ADDITIONS = {
    "branches": [
        ("must_change_password", "INTEGER NOT NULL DEFAULT 0"),
        ("password_changed_date", "TEXT"),
        ("temp_password_expires", "TEXT"),
    ],
    "admins": [
        ("must_change_password", "INTEGER NOT NULL DEFAULT 0"),
        ("password_changed_date", "TEXT"),
        ("temp_password_expires", "TEXT"),
    ],
    "messages": [
        ("priority", "TEXT NOT NULL DEFAULT 'NORMAL'"),
        ("parent_message_id", "INTEGER"),
        ("key_id", "INTEGER NOT NULL DEFAULT 1"),
        ("aad_version", "INTEGER NOT NULL DEFAULT 1"),
        ("sender_status", "TEXT NOT NULL DEFAULT 'ACTIVE'"),
        ("receiver_status", "TEXT NOT NULL DEFAULT 'ACTIVE'"),
    ],
}

NEW_TABLES = {
    "schema_meta": """
        CREATE TABLE IF NOT EXISTS schema_meta (
            meta_key TEXT PRIMARY KEY,
            meta_value TEXT NOT NULL
        )
    """,
    "two_factor": """
        CREATE TABLE IF NOT EXISTS two_factor (
            account_type TEXT NOT NULL,
            account_id INTEGER NOT NULL,
            secret_enc TEXT NOT NULL,
            nonce TEXT NOT NULL,
            key_id INTEGER NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 0,
            last_step INTEGER NOT NULL DEFAULT 0,
            enabled_date TEXT,
            PRIMARY KEY (account_type, account_id)
        )
    """,
}


def _columns(cursor, table):
    cursor.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cursor.fetchall()}


def run_migrations():
    """Applies all pending migrations. Returns a list describing what
    was changed (empty list = database already up to date)."""

    applied = []
    connection = connect()

    try:
        cursor = connection.cursor()

        # 1. New columns on existing tables
        for table, additions in COLUMN_ADDITIONS.items():
            existing = _columns(cursor, table)
            if not existing:
                continue  # table does not exist yet
            for column, definition in additions:
                if column not in existing:
                    cursor.execute(
                        f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
                    )
                    applied.append(f"{table}.{column} added")

        # 2. New tables
        for name, sql in NEW_TABLES.items():
            cursor.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (name,),
            )
            if cursor.fetchone() is None:
                applied.append(f"table {name} created")
            cursor.execute(sql)

        # 3. Audit chain columns + one-time baseline for existing logs
        ensure_audit_schema(connection)

        cursor.execute(
            "SELECT meta_value FROM schema_meta WHERE meta_key = 'audit_baseline'"
        )
        if cursor.fetchone() is None:
            sealed = seal_existing_rows(connection)
            cursor.execute(
                "INSERT INTO schema_meta (meta_key, meta_value) "
                "VALUES ('audit_baseline', 'done')"
            )
            if sealed:
                applied.append(f"audit chain baseline: {sealed} existing log "
                               "entries sealed")

        # 4. Schema version
        cursor.execute(
            "SELECT meta_value FROM schema_meta WHERE meta_key = 'schema_version'"
        )
        row = cursor.fetchone()
        if row is None or int(row[0]) < SCHEMA_VERSION:
            cursor.execute(
                "INSERT INTO schema_meta (meta_key, meta_value) "
                "VALUES ('schema_version', ?) "
                "ON CONFLICT(meta_key) DO UPDATE SET "
                "meta_value = excluded.meta_value",
                (str(SCHEMA_VERSION),),
            )
            applied.append(f"schema version set to {SCHEMA_VERSION}")

        connection.commit()

    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    return applied

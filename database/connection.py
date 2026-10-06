"""
Shared SQLite connection helper used by the enhanced-version modules.

The legacy code opens "database/bank.db" directly; this helper keeps the
same relative path so both styles keep working side by side.
"""

import os
import sqlite3

DB_PATH = os.path.join("database", "bank.db")


def connect():
    """Opens a connection with a busy timeout (several Streamlit
    sessions may write at the same time)."""
    return sqlite3.connect(DB_PATH, timeout=10)

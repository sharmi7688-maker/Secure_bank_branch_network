"""
Shared test fixture.

Every test runs inside its own temporary "project" folder (own bank.db,
own encryption key, own audit key), so the real database is never touched.
The application uses relative paths ("database/bank.db", "config/..."), so
changing the working directory is all that is needed.
"""

import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.database import (  # noqa: E402
    create_database,
    create_messages_table,
    create_activity_logs_table,
    create_login_security_table,
    create_admins_table,
    create_admin_activity_logs_table,
    create_admin_login_security_table,
    insert_branch,
    insert_admin,
)
from database.migrations import run_migrations  # noqa: E402
from modules.encryption import ensure_key_exists  # noqa: E402
from modules.security import hash_password  # noqa: E402

PASSWORD = "Str0ng!Passw0rd#1"
_cached_hash = {}


def _password_hash():
    # PBKDF2 is deliberately slow: compute the shared test hash only once
    if "value" not in _cached_hash:
        _cached_hash["value"] = hash_password(PASSWORD)
    return _cached_hash["value"]


def create_legacy_tables():
    """Creates the ORIGINAL (pre-enhancement) schema."""
    with contextlib.redirect_stdout(io.StringIO()):
        create_database()
        create_messages_table()
        create_activity_logs_table()
        create_login_security_table()
        create_admins_table()
        create_admin_activity_logs_table()
        create_admin_login_security_table()


class TempProjectTestCase(unittest.TestCase):
    """Fresh, fully migrated project folder for every test."""

    MIGRATE = True

    def setUp(self):
        self._original_cwd = os.getcwd()
        self._tmp = tempfile.mkdtemp(prefix="sbn_test_")
        os.chdir(self._tmp)
        os.makedirs("database")
        os.makedirs("config")

        create_legacy_tables()

        if self.MIGRATE:
            run_migrations()
            ensure_key_exists()

    def tearDown(self):
        os.chdir(self._original_cwd)
        shutil.rmtree(self._tmp, ignore_errors=True)

    # ---- helpers -------------------------------------------------

    def make_branch(self, name="Alpha"):
        password_hash, salt = _password_hash()
        return insert_branch(name, password_hash, salt, "2026-01-01 09:00:00")

    def make_admin(self, username="root_admin"):
        password_hash, salt = _password_hash()
        return insert_admin(username, password_hash, salt,
                            "2026-01-01 09:00:00")

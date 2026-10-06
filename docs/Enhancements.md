# Final Project Enhancements

This document describes everything added on top of the original Secure Bank Branch Network System for the final project. All original features still work; the database is upgraded automatically and no data is lost.

---

## 1. Summary of new features

| # | Feature | Main files | Where to see it |
|---|---------|-----------|-----------------|
| 1 | Two-factor authentication (TOTP, RFC 6238) | `modules/totp.py`, `modules/two_factor.py` | Branch: *Profile & Security*; Admin: *My Account* |
| 2 | Session timeout (10 min idle) | `modules/session_timeout.py`, `streamlit_app.py` | Automatic; shown in the sidebar |
| 2 | Change password, strength meter, forced change | `modules/password_policy.py` | *Profile & Security* / *My Account*; registration forms |
| 3 | Tamper-evident audit log (HMAC hash chain) | `modules/audit_chain.py` | Admin: *Security Center > Audit Log Integrity* |
| 4 | Encryption key versioning, rotation, bound metadata | `modules/encryption.py`, `modules/key_management.py` | Admin: *Security Center > Encryption Keys* |
| 5 | Messaging upgrade: subject, priority, replies, search, archive, delete | `modules/messaging_service.py` | Branch: *Send / Inbox / Sent / Archive* |
| 7 | Admin analytics dashboard | `modules/analytics.py` | Admin: *Analytics* |
| 8 | Suspicious-activity alerts and CSV export | `modules/alerts.py`, `modules/reports.py` | Admin: *Alerts*, download buttons |
| 11 | Forgotten-password recovery (admin-issued temporary password) | `modules/password_policy.py`, `modules/admin_recovery.py` | Admin: *Security Center > Account Recovery* |
| 12 | Light theme | `streamlit_app.py` (CSS), `.streamlit/config.toml` | Whole app |
| 13 | Automated tests, migrations, documentation | `tests/`, `database/migrations.py`, `docs/` | `python -m pytest` |

---

## 2. Architecture

```text
streamlit_app.py            UI only (no security rules inside)
        |
modules/ (service layer)    auth_service, two_factor, totp, password_policy,
        |                   messaging_service, key_management, alerts,
        |                   analytics, reports, session_timeout, audit_chain,
        |                   account_lock, encryption, security
        |
database/                   database.py (original queries), store.py (new
        |                   queries), connection.py, migrations.py
        |
SQLite  database/bank.db    +   config/ (encryption keys, audit key)
```

The original console menu (`main.py`) still works because the database changes are backward compatible. The new features are available in the Streamlit interface.

---

## 3. How each feature works

### 3.1 Two-factor authentication (TOTP)
* Implemented from the standard (RFC 6238): HMAC-SHA1, 30-second steps, 6 digits, accepting one step of clock drift. The code is checked against the RFC test vectors in `tests/test_totp.py`.
* Setup: the user scans a QR code (or types the key) into an authenticator app and confirms with a first code. 2FA is only switched on after that confirmation.
* The secret is stored **encrypted** (AES-256-GCM, tied to the account), never in plain text.
* **Replay protection:** the last accepted time step is stored, so the same code cannot be used twice.
* Wrong codes count toward the normal 3-attempt lockout.
* Turning 2FA off needs the password **and** a current code. A lost device is handled by an administrator (*Security Center > Account Recovery > Reset 2FA*), which is audited.
* The QR image needs the optional package `qrcode[pil]`; without it the app shows the key for manual entry.

### 3.2 Sessions and passwords
* A session idle for more than 10 minutes is closed and logged (`SESSION_TIMEOUT`). Streamlit only runs code when the user interacts, so the check happens on the next click or keystroke; an expired session can never perform an action.
* The 2FA step must be completed within 5 minutes of the password step.
* Change password requires the current password (wrong attempts count toward lockout), the existing complexity rules, a different password, and no account name inside it.
* The strength meter shows a 0 to 4 score and a live checklist. An administrator can require a password change at next sign-in (*Account Recovery*).

### 3.3 Tamper-evident audit log
* Every row in `activity_logs` and `admin_activity_logs` gets `entry_hash = HMAC-SHA256(key, previous_hash + table + id + actor + type + description + date)`.
* Editing or deleting any row breaks every hash after it; a small "head" record also detects rows removed from the end.
* The HMAC key is in `config/audit.key`, **not** in the database, so someone who can only edit `bank.db` cannot recompute a valid chain.
* The row and its seal are written in one transaction. Existing rows are sealed when the database is first upgraded (tampering that happened *before* the upgrade cannot be detected).
* The administrator runs *Verify log integrity*; a failed check also raises a HIGH alert.

### 3.4 Encryption improvements
* **Key versions:** `config/encryption.key` is version 1 (your original key). Rotation creates `config/encryption_key_v2.key`, and so on. New messages use the newest key; old messages keep working because each message stores its `key_id`.
* **Re-encryption** moves every message to the active key in one all-or-nothing transaction.
* **Bound metadata:** the sender, receiver and sent time are passed to AES-GCM as *authenticated data*. If someone edits those database fields, or copies a ciphertext into another conversation, decryption fails the integrity check. (The message id is not used because it is only known after the row is inserted; the sent time plays that role.)
* Subject and body are encrypted together. Messages created by the original version stay readable (`aad_version = 1`) until re-encrypted.
* Administrators still see metadata only; they cannot read message content.

### 3.5 Messaging
* Subject (80 chars), body (500 chars), priority (Normal / Urgent / Confidential).
* **Replies** are linked to the original (`parent_message_id`) and form a conversation; you can only reply to a message you received, and the reply goes back to its sender.
* **Search and filters** (keyword, priority, other branch, unread, date range) run on the viewer's own messages after decryption inside the application.
* **Archive / delete / restore** work per side: deleting hides the message from your mailbox only; the other branch keeps its copy and the row is kept for auditing.
* Message text is HTML-escaped before display.

### 3.6 Analytics, alerts and reports
Alert rules (thresholds are constants at the top of `modules/alerts.py`):

| Rule | Severity |
|------|----------|
| Branch locked 2+ times in 24 h (4+ = high) | Medium / High |
| 5+ failed sign-ins in 15 min across the network (10+ = high) | Medium / High |
| 3+ administrator authentication failures in 60 min | High |
| 15+ messages from one branch in 10 min | Medium |
| Administrator sign-in between 00:00 and 04:59 | Low |
| Administrators without 2FA | Low |
| Audit-log chain broken | High |

CSV exports (activity with date range, message metadata, login security, alerts) neutralise cells that start with `=`, `+`, `-` or `@`, which prevents spreadsheet formula injection.

### 3.7 Forgotten password (admin-issued temporary password)
The system has no e-mail or SMS, so a forgotten password is recovered by an administrator:

1. The user contacts an administrator.
2. The administrator opens *Security Center > Account Recovery*, chooses *Branch* or *Administrator*, enters the branch code (e.g. SB003) or the username, and clicks **Issue temporary password**.
3. A random password (14 characters, meets every password rule, no look-alike characters such as 0/O or 1/l, created with Python's `secrets` module) is shown **once**. It is stored only as a PBKDF2 hash and is never written to any log.
4. The administrator gives it to the user through a safe channel.
5. The user signs in with it and is **forced to choose a new password** before anything else. The temporary password is entered as the "current password".
6. It **expires after 24 hours** (sign-in is refused with a clear message; it does not count as a failed attempt).

Other rules:
* Any lockout on the account is cleared.
* Two-factor authentication stays on. If the phone is lost too, the administrator also uses **Reset 2FA**.
* An administrator cannot issue one for their own account (they use *Change Password*), so a hijacked admin session cannot silently reset its own password.
* Audit: `ADMIN_TEMP_PASSWORD_ISSUED` in the administrator log and `TEMP_PASSWORD_ISSUED` in the account's own history. Expiry is logged as `TEMP_PASSWORD_EXPIRED`.
* **Only one administrator and they forgot the password?** Run on the server, from the project folder: `python -m modules.admin_recovery`. It asks for the username, requires typing `RESET`, optionally removes 2FA, prints a temporary password, and writes `ADMIN_CONSOLE_PASSWORD_RESET` to the audit log. It needs access to the project files, so it is not available from the web interface.

### 3.8 Light theme
The look is defined by colour variables at the top of the CSS in `streamlit_app.py` (`--sb-bg-1`, `--sb-panel`, `--sb-gold`, ...); change them to re-colour the app. `.streamlit/config.toml` sets Streamlit's own widgets (menus, tables, charts, code boxes) to the light theme, even if the browser or operating system uses dark mode. Keep that file when you copy the project.

---

## 4. New activity types in the audit log

`FAILED_2FA`, `2FA_ENABLED`, `2FA_DISABLED`, `PASSWORD_CHANGED`, `FAILED_PASSWORD_CHANGE`, `SESSION_TIMEOUT`, `MESSAGE_ARCHIVED`, `MESSAGE_DELETED`, `MESSAGE_RESTORED`, and for administrators (with `ADMIN_` prefix): `ADMIN_KEY_ROTATED`, `ADMIN_MESSAGES_REENCRYPTED`, `AUDIT_VERIFIED`, `ADMIN_RESET_2FA`, `ADMIN_FORCE_PASSWORD_CHANGE`, `ADMIN_SESSION_TIMEOUT`, `ADMIN_TEMP_PASSWORD_ISSUED`, `ADMIN_CONSOLE_PASSWORD_RESET`; and for accounts: `TEMP_PASSWORD_ISSUED`, `TEMP_PASSWORD_EXPIRED` (with `ADMIN_` prefix for administrators).

---

## 5. Upgrading an existing installation

1. **Back up** `database/bank.db` and the whole `config/` folder.
2. Install requirements: `pip install -r requirements.txt`.
3. Run `streamlit run streamlit_app.py`. On start-up the database is upgraded automatically (adds columns and tables, seals existing log rows). The upgrade is safe to run repeatedly.
4. Keep the `.streamlit/` folder (light theme) with the project.
5. Keep `config/` safe: `encryption.key`, `encryption_key_vN.key` and `audit.key`. Without a key file its messages cannot be decrypted, and without `audit.key` the log cannot be verified.

---

## 6. Known limitations and future work

* The inactivity timeout is evaluated when the user interacts (Streamlit has no server push).
* Keys are stored on the same machine as the database; production systems should use a hardware security module or a cloud key-management service.
* No recovery codes for 2FA (an administrator resets it instead); no e-mail or SMS delivery, so password recovery depends on an administrator being reachable (or server access for the last administrator).
* The temporary password is displayed on the administrator's screen once; hand it over through a safe channel.
* SQLite is a single-file database; a larger deployment would use PostgreSQL or similar.
* The console menu was not extended with the new features.

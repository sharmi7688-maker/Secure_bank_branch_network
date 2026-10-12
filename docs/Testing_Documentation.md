# Testing Documentation

## Secure Bank Branch Network System

---

# 1. Testing Overview

Testing was performed to verify that the Secure Bank Branch Network System behaves correctly under normal, invalid, and security-related conditions.

Testing covers:

* Authentication
* Account lockout
* Administrator security
* Messaging
* Database operations
* Activity logging
* Session management

---

# 2. Branch Authentication Testing

| Test                           | Expected Result               |
| ------------------------------ | ----------------------------- |
| Correct branch code + password | Login successful              |
| Invalid branch code            | Login rejected                |
| Incorrect password             | Failed attempt recorded       |
| Three failed attempts          | Account locked                |
| Login during lock              | Login rejected                |
| Lock expiration                | Login becomes available       |
| Administrator unlock           | Account immediately available |
| Failed-attempt reset           | Counter becomes zero          |

---

# 3. Administrator Authentication Testing

| Test                  | Expected Result         |
| --------------------- | ----------------------- |
| Correct credentials   | Admin login successful  |
| Incorrect password    | Failed attempt recorded |
| Three failed attempts | Administrator locked    |
| Login during lock     | Login rejected          |
| Lock expiration       | Administrator available |
| Administrator unlock  | Account available       |
| Reset attempts        | Counter becomes zero    |

---

# 4. Messaging Testing

| Test                      | Expected Result                                |
| ------------------------- | ---------------------------------------------- |
| Send valid message        | Message stored                                 |
| Send to registered branch | Delivery successful                            |
| Read message              | Status changes to READ                         |
| Unread message            | Status remains UNREAD                          |
| Encrypted storage         | Plaintext not directly stored                  |
| Admin views message       | Metadata shown, confidential content protected |

---

# 5. Activity Logging Testing

The system should record important events.

Example:

```text
LOGIN
LOGOUT
FAILED_LOGIN
MESSAGE_SENT
MESSAGE_READ
PROFILE_VIEWED
ADMIN_LOGIN
ADMIN_LOGOUT
ADMIN_FAILED_LOGIN
ADMIN_UNLOCK_BRANCH
ADMIN_RESET_BRANCH_ATTEMPTS
```

---

# 6. Session Testing

### Successful Login

Expected:

```text
Session Created
Dashboard Displayed
```

### Logout

Expected:

```text
Logout Activity Recorded
Session Destroyed
Main Menu Displayed
```

---

# 7. Database Testing

Database tests include:

* Database creation.
* Table creation.
* Table verification.
* Branch insertion.
* Branch retrieval.
* Login-security updates.
* Message insertion.
* Activity insertion.
* Security-status updates.

---

# 8. Security Test Example

A branch is intentionally given an incorrect password three times.

Expected result:

```text
Attempt 1 → Failed
Attempt 2 → Failed
Attempt 3 → Failed
             ↓
       Account Locked
             ↓
       5-minute lock
```

Database verification should show:

```text
failed_attempts = 3
locked_until = <future timestamp>
```

After unlocking:

```text
failed_attempts = 0
locked_until = NULL
```

---

# 9. Administrator Security Test

The administrator account is intentionally given an incorrect password three times.

Expected:

```text
Failed Attempts = 3
Account = LOCKED
```

After successful administrator security management:

```text
Failed Attempts = 0
Account = NOT LOCKED
```

---

# 10. Test Result

The tested security mechanisms demonstrate that:

* Failed logins are recorded.
* Login attempts are limited.
* Temporary account locking works.
* Locked accounts can be administratively unlocked.
* Failed-attempt counters can be reset.
* Successful authentication resets the security state as designed.
* Login/logout activities are recorded.
* Messaging activities are audited.

---

# 11. Future Testing

Future versions should include:

* Automated unit testing.
* Integration testing.
* Penetration testing.
* Load testing.
* Vulnerability scanning.
* Dependency security scanning.
* Authentication fuzz testing.
* Database failure testing.
* Encryption/decryption testing.
* Session-hijacking resistance testing.

---

# Automated Test Suite (Final Project)

The older `modules/test_*.py` and `verify_*.py` helper scripts remain, but the real test suite is now in `tests/` and uses a temporary database and temporary keys, so it never touches `bank.db`.

| Test file | Tests | Covers |
|-----------|-------|--------|
| `test_totp.py` | 9 | RFC 6238 vectors, drift window, replay step |
| `test_two_factor.py` | 14 | enrolment, login codes, disable, admin reset, encrypted storage |
| `test_auth_service.py` | 13 | sign-in, wrong/empty/unknown credentials, 3-strike lockout, administrator lockout, session timeout rules |
| `test_password_policy.py` | 18 | strength meter, change password rules, lockout on wrong current password |
| `test_encryption_keys.py` | 12 | key rotation, bound metadata, tamper detection, legacy messages |
| `test_messaging.py` | 19 | send, reply rules, search, archive/delete, permissions |
| `test_audit_chain.py` | 11 | sealing, edit/delete/insert/truncate detection |
| `test_alerts_analytics_reports.py` | 17 | alert thresholds, chart data, CSV injection |
| `test_migrations.py` | 5 | upgrade of an original-format database, idempotence |
| `test_temp_password.py` | 17 | generator rules, sign-in and forced change, 24-hour expiry, no clear-text storage, audit on both sides, lockout cleared, 2FA interaction, self-issue blocked, console recovery |
| **Total** | **135** | |

Run: `python -m pytest` (or `python -m unittest discover -s tests -t .` without pytest).

**UI smoke test:** `python tests/ui_smoke/run_ui_smoke.py` runs the real `streamlit_app.py` against a small fake Streamlit module in a temporary copy of the project and performs 83 checks (sign-in failures, 2FA set-up and login, messaging and replies, archive, password change, idle timeout, admin dashboard, key rotation, tamper detection, temporary-password recovery, light-theme CSS, staying on the same section after every button, form fields clearing after a successful submit). It does not replace testing the visuals in a browser.

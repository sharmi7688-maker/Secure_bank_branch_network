# Security Documentation

## Secure Bank Branch Network System

---

## 1. Security Overview

Security is a core component of the Secure Bank Branch Network System.

The system uses multiple security layers rather than relying on a single mechanism.

```text
Authentication
      ↓
Password Protection
      ↓
Login Attempt Monitoring
      ↓
Account Lockout
      ↓
Session Management
      ↓
Message Encryption
      ↓
Activity Auditing
```

---

## 2. Password Security

Passwords must never be stored directly.

The system stores password-derived values rather than the original password.

Conceptually:

```text
Password
   +
Salt
   ↓
Password Hash
   ↓
Database
```

---

## 3. Salt

A cryptographic salt is used with password processing.

The purpose of a salt is to ensure that identical passwords do not necessarily produce identical stored values.

---

## 4. Authentication

The authentication process verifies:

```text
User Identity
       +
Password
       ↓
Authentication Result
```

Only authenticated users can access protected functionality.

---

## 5. Failed Login Protection

The system limits authentication attempts.

Configuration:

```text
Maximum Failed Attempts: 3
Temporary Lock Duration: 5 minutes
```

Flow:

```text
Failed Attempt #1
       ↓
Failed Attempt #2
       ↓
Failed Attempt #3
       ↓
Account Locked
       ↓
5 Minutes
       ↓
Account Available
```

---

## 6. Automatic Lock Expiration

Temporary locks contain a timestamp.

The system compares the current time with the stored lock expiration time.

If the lock period has expired, the account becomes available again.

---

## 7. Administrator Security

Administrator authentication has its own security tracking.

Administrator failed attempts are stored separately from branch failed attempts.

This prevents branch authentication data from interfering with administrator security management.

---

## 8. Message Encryption

Confidential messages are encrypted before being stored.

The project uses:

```text
AES-256-GCM
```

AES-GCM provides authenticated encryption.

The system should protect:

```text
Plaintext Message
        ↓
Encryption
        ↓
Encrypted Data
        ↓
Database
```

When authorized recipients access the message:

```text
Encrypted Data
        ↓
Decryption
        ↓
Original Message
```

---

## 9. Administrator Message Restrictions

The administrator can monitor message metadata but confidential message content is not displayed.

This follows the principle of limiting privileged access to confidential information.

Example metadata:

```text
Message ID
Sender
Receiver
Timestamp
Status
Encryption Type
```

The confidential content remains protected.

---

## 10. Session Security

After successful authentication, a session is created.

After logout:

```text
Session destroyed
       ↓
Protected area unavailable
       ↓
User returned to login/main menu
```

---

## 11. Audit Logging

Security-related operations are recorded.

Examples:

```text
LOGIN
LOGOUT
FAILED_LOGIN
ADMIN_LOGIN
ADMIN_LOGOUT
ADMIN_FAILED_LOGIN
MESSAGE_SENT
MESSAGE_READ
ADMIN_UNLOCK_BRANCH
ADMIN_RESET_BRANCH_ATTEMPTS
```

Audit logs help administrators investigate suspicious activity.

---

## 12. Principle of Least Privilege

Users should only have access to functionality required for their role.

### Branch

```text
Messaging
Profile
Activity
Logout
```

### Administrator

```text
Branch monitoring
Message metadata
System activity
Security management
Logout
```

Confidential message contents should remain restricted.

---

## 13. Security Limitations

This project is primarily an academic/security demonstration system.

For production banking environments, additional mechanisms would be required, including:

* Hardware security modules.
* Multi-factor authentication.
* HTTPS/TLS.
* Key rotation.
* Centralized identity management.
* Database encryption at rest.
* Network segmentation.
* Intrusion detection.
* Security information and event management.
* Secure backup.
* Disaster recovery.
* Penetration testing.
* Formal security auditing.

---

## 14. Security Best Practices

Production deployments should:

1. Never hard-code secrets.
2. Store secrets in environment variables or a secure secret manager.
3. Use HTTPS.
4. Rotate encryption keys.
5. Restrict database permissions.
6. Back up data securely.
7. Monitor failed authentication attempts.
8. Keep dependencies updated.
9. Use strong administrator passwords.
10. Perform regular security testing.

---

# Final Project Additions

* **Two-factor authentication:** optional TOTP (RFC 6238) for branches and administrators; secrets stored encrypted; replay-protected; failed codes count toward lockout.
* **Session security:** 10-minute inactivity timeout, 5-minute window for the second login step, password change with the current password, forced password change by an administrator.
* **Audit integrity:** HMAC-SHA256 hash chain over both log tables, key kept outside the database (`config/audit.key`), on-demand verification and a HIGH alert on tampering.
* **Encryption:** versioned AES-256-GCM keys with rotation and re-encryption; sender, receiver and sent time are authenticated data, so edited or moved ciphertexts fail to decrypt.
* **Forgotten password:** administrator-issued random temporary password (shown once, stored hashed, never logged, 24-hour expiry, forced change at next sign-in, lockout cleared, audited on both sides); administrators cannot issue one for themselves; last-administrator recovery only through the server console (`python -m modules.admin_recovery`).
* **Monitoring:** rule-based suspicious-activity alerts; CSV exports protected against formula injection; message text HTML-escaped on display.

See `docs/Enhancements.md` for details and limitations.

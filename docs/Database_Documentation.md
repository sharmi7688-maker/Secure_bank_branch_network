# Database Documentation

## Secure Bank Branch Network System

---

# 1. Database Overview

The Secure Bank Branch Network System uses SQLite for persistent data storage.

Database:

```text
database/bank.db
```

SQLite is suitable for this academic/local implementation because it is lightweight and does not require a separate database server.

---

# 2. Branches Table

The branches table contains registered branch information.

Example fields:

```text
branch_id
branch_code
branch_name
password_hash
password_salt
created_date
```

The branch identifier uniquely identifies a branch.

---

# 3. Login Security Table

The login security table stores branch authentication-security information.

Important fields include:

```text
branch_id
failed_attempts
locked_until
```

Example:

```text
SB005
Failed Attempts: 3
Locked Until: <timestamp>
```

After the account is unlocked:

```text
Failed Attempts: 0
Locked Until: NULL
```

---

# 4. Administrator Login Security

Administrator authentication has a separate security table.

Example fields:

```text
admin_id
failed_attempts
locked_until
```

This allows administrator authentication to be monitored independently.

---

# 5. Messages

The message table stores branch communication information.

Typical fields include:

```text
message_id
sender_branch_id
receiver_branch_id
encrypted_content
sent_date
status
```

The message content is stored in encrypted form.

---

# 6. Activity Log

The activity log records important system operations.

Typical fields include:

```text
activity_id
actor_type
actor_id
activity_type
description
created_date
```

Examples:

```text
BRANCH | SB001 | LOGIN
BRANCH | SB001 | MESSAGE_SENT
BRANCH | SB002 | MESSAGE_READ
ADMIN  | admin | ADMIN_LOGIN
```

---

# 7. Relationships

Conceptually:

```text
BRANCH
  │
  ├──────── LOGIN_SECURITY
  │
  ├──────── MESSAGE (sender)
  │
  ├──────── MESSAGE (receiver)
  │
  └──────── ACTIVITY_LOG
```

---

# 8. Database Security

The database should not be publicly exposed.

The following information should never be displayed unnecessarily:

* Plain-text passwords.
* Encryption keys.
* Password-derived secrets.
* Confidential message plaintext.

---

# 9. Backup

The SQLite database should be backed up regularly in production.

A backup strategy should include:

```text
Database
   ↓
Encrypted Backup
   ↓
Secure Storage
   ↓
Recovery Testing
```

---

# 10. Future Database Improvements

For a production deployment, the project could migrate to:

* PostgreSQL
* MySQL
* Microsoft SQL Server

Additional database improvements could include:

* Foreign-key enforcement.
* Database encryption.
* Connection pooling.
* Role-based database permissions.
* Transaction management.
* Automated backup.
* Disaster recovery.

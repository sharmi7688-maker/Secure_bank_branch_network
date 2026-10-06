# 🔐 Secure Bank Branch Network System

A secure branch-to-branch banking communication system developed using Python, SQLite, cryptographic techniques, authentication mechanisms, and a modern web-based frontend.

The system is designed to provide secure communication between bank branches while maintaining authentication, authorization, password protection, account lockout, activity monitoring, encrypted messaging, and administrator security management.


## Final Project Enhancements

This version adds optional TOTP two-factor authentication, a 10-minute inactivity timeout, change-password with a strength meter, a tamper-evident audit log, versioned encryption keys with rotation, richer messaging (subject, priority, replies, search, archive), an admin analytics dashboard, suspicious-activity alerts with CSV export, administrator-issued temporary-password recovery for forgotten passwords, a light theme, and an automated test suite (135 tests + a UI flow test).

* Full description: [`docs/Enhancements.md`](docs/Enhancements.md)
* Install: `pip install -r requirements.txt`
* Run: `streamlit run streamlit_app.py`
* Test: `python -m pytest`
* Forgot a password: an administrator uses *Security Center > Account Recovery > Issue temporary password*; the only administrator uses `python -m modules.admin_recovery` on the server.
* Upgrading an existing `bank.db`: back up `database/` and `config/` first; the database upgrades itself on start-up.

---

## 📌 Project Overview

The **Secure Bank Branch Network System** is a banking communication platform that allows registered bank branches to securely communicate with other branches.

The system provides two major user roles:

* **Branch User**
* **Administrator**

Branch users can securely log in, communicate with other branches, view their profile, and check their activity history.

The administrator has centralized control over the branch network and can monitor branches, messages, system activity, and login security.

---

## 🎯 Objectives

The main objectives of this project are:

1. Provide secure authentication for bank branches.
2. Protect branch passwords using hashing and salts.
3. Implement failed-login monitoring.
4. Temporarily lock accounts after repeated failed attempts.
5. Allow administrators to unlock locked accounts.
6. Provide secure branch-to-branch messaging.
7. Encrypt confidential messages.
8. Maintain system activity logs.
9. Provide centralized administrator monitoring.
10. Prevent administrators from directly viewing confidential message contents.
11. Provide a professional and user-friendly frontend.
12. Maintain a secure and organized database structure.

---

## ✨ Main Features

### 👤 Branch Management

* Register new branches.
* Generate unique branch codes.
* Store branch information securely.
* View branch profile.
* Maintain branch registration date.

### 🔑 Secure Branch Login

* Branch-code based authentication.
* Password verification.
* Password hashing.
* Password salt.
* Failed-login tracking.
* Three-attempt login protection.
* Five-minute temporary account lock.
* Automatic lock expiration.
* Secure session handling.

### 🛡️ Administrator Authentication

* Administrator username/password authentication.
* Failed administrator login tracking.
* Three-attempt administrator account protection.
* Temporary administrator lock.
* Secure administrator session.
* Administrator login/logout logging.

### 💬 Secure Messaging

Branches can send messages to other registered branches.

Message features include:

* Sender branch identification.
* Receiver branch identification.
* Timestamp.
* Read/unread status.
* Encrypted message storage.
* AES-256-GCM encryption.
* Message metadata monitoring.

For security reasons, administrators can view message metadata but confidential message content is not displayed.

### 📊 Administrator Dashboard

The administrator dashboard provides:

* View All Branches
* View Branch Details
* View All Messages
* View System Activity
* View Login Security
* Account security management
* Branch account unlocking
* Administrator account unlocking
* Failed-attempt reset

### 🔍 Security Monitoring

The administrator can monitor:

* Failed branch login attempts.
* Locked branch accounts.
* Failed administrator login attempts.
* Administrator account status.
* Lock expiration time.
* Login activity.
* Logout activity.
* Message activity.
* Profile access.
* Security-management activities.

### 📝 Activity Logging

The system records important activities such as:

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
ADMIN_UNLOCK_ADMIN
ADMIN_RESET_BRANCH_ATTEMPTS
ADMIN_RESET_ADMIN_ATTEMPTS
```

---

# 🏗️ System Architecture

The project follows a layered architecture.

```text
                    ┌──────────────────────┐
                    │      FRONTEND        │
                    │   HTML/CSS/JS or     │
                    │      Streamlit       │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │    APPLICATION       │
                    │       LOGIC          │
                    └──────────┬───────────┘
                               │
                ┌──────────────┼──────────────┐
                ▼              ▼              ▼
        ┌──────────────┐ ┌────────────┐ ┌──────────────┐
        │Authentication│ │ Messaging  │ │   Security   │
        │   Module     │ │   Module   │ │    Module    │
        └──────┬───────┘ └─────┬──────┘ └──────┬───────┘
               │               │               │
               └───────────────┼───────────────┘
                               ▼
                    ┌──────────────────────┐
                    │       SQLite         │
                    │       Database       │
                    └──────────────────────┘
```

---

# 🛠️ Technologies Used

## Backend

* Python
* SQLite
* Python Cryptography Libraries
* Password Hashing
* Session Management

## Frontend

* Streamlit / HTML
* CSS
* JavaScript

## Database

* SQLite

## Security

* Password hashing
* Password salts
* AES-256-GCM encryption
* Failed-login detection
* Temporary account locking
* Session destruction
* Activity auditing

---

# 🔐 Security Design

The system implements multiple layers of security.

### Password Protection

Passwords are not stored as plain text.

The system stores:

```text
password_hash
password_salt
```

This prevents direct exposure of user passwords in the database.

### Account Lockout

After three consecutive failed login attempts:

```text
Maximum attempts = 3
Lock duration = 5 minutes
```

Example:

```text
Attempt 1 → Failed
Attempt 2 → Failed
Attempt 3 → Failed
             ↓
       Account Locked
             ↓
       5-minute lock
```

### Message Encryption

Confidential messages use:

```text
AES-256-GCM
```

The administrator can see message metadata but cannot directly view confidential message content.

---

# 🗄️ Database

The application uses SQLite.

The database file is:

```text
database/bank.db
```

Important database tables include:

```text
branches
login_security
admin_login_security
messages
activity_log
```

The exact schema may vary according to the implementation.

---

# 👨‍💼 Administrator Functions

The administrator dashboard provides:

```text
1. View All Branches
2. View Branch Details
3. View All Messages
4. View System Activity
5. View Login Security
6. Logout
```

Security management includes:

```text
1. Unlock Branch Account
2. Unlock Administrator Account
3. Reset Branch Failed Attempts
4. Reset Administrator Failed Attempts
5. Refresh
6. Back
```

---

# 🏦 Branch Functions

After successful branch authentication, the branch dashboard provides:

```text
1. Secure Messaging
2. Branch Profile
3. Activity History
4. Logout
```

---

# 🚀 Installation

### 1. Download or clone the project

git clone <repository-url>

### 2. Open the project folder

cd Secure_Bank_Branch_Network

### 3. Create a virtual environment

python -m venv venv

### 4. Activate the virtual environment

Windows:

venv\Scripts\activate

### 5. Upgrade pip

python -m pip install --upgrade pip

### 6. Install dependencies

pip install -r requirements.txt

### 7. Run the Streamlit application

streamlit run streamlit_app.py

---


# 🔑 Default Administrator

The project can be configured with an administrator account during database initialization.

For security reasons, administrator credentials should not be hard-coded in production deployments.

---

# 🧪 Security Testing

The following security scenarios have been tested:

### Branch Login

```text
Correct password
Incorrect password
Multiple incorrect passwords
Account lock
Lock expiration
Administrator unlock
Failed-attempt reset
Successful login after unlock
```

### Administrator Login

```text
Correct credentials
Incorrect password
Three failed attempts
Administrator account lock
Lock expiration
Administrator unlock
Failed-attempt reset
```

### Messaging

```text
Message creation
Message encryption
Message delivery
Message read status
Message metadata
Administrator metadata access
```

### Session Security

```text
Successful login
Dashboard access
Logout
Session destruction
Return to main menu
```

---

# 📊 Example Security Flow

```text
              USER LOGIN
                  │
                  ▼
          Verify Branch Code
                  │
                  ▼
          Check Account Lock
             /          \
           Locked      Active
             │           │
             ▼           ▼
       Reject Login   Verify Password
                         │
                   ┌─────┴─────┐
                   │           │
                 Valid       Invalid
                   │           │
                   ▼           ▼
             Create Session   Increase
                              Attempts
                                │
                                ▼
                          Attempts >= 3
                                │
                                ▼
                           Lock Account
                                │
                                ▼
                            5 Minutes
```

---

# 🎓 Academic Purpose

This project demonstrates practical implementation of:

* Python programming
* Database management
* Authentication
* Authorization
* Cryptography
* Secure password storage
* Session management
* Access control
* Audit logging
* Secure communication
* Frontend development
* Software architecture

---

# 🔮 Future Enhancements

Possible future improvements include:

* Two-factor authentication.
* Email/SMS OTP verification.
* Role-based access control.
* Password reset functionality.
* Digital signatures.
* Public/private key infrastructure.
* HTTPS deployment.
* PostgreSQL/MySQL support.
* Cloud deployment.
* Security alerts.
* Intrusion detection.
* Network monitoring.
* Advanced administrator analytics.
* Multi-level banking roles.
* Backup and recovery system.

---

# 👩‍💻 Author

**Sharmila TM**

Secure Bank Branch Network System

---

# 📄 License

This project is distributed under the MIT License.

See the `LICENSE` file for details.

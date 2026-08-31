# Secure Bank Branch Network System

## Project Documentation

---

## 1. Introduction

The Secure Bank Branch Network System is a secure communication and branch-management application developed to demonstrate how authentication, authorization, encryption, database management, and activity auditing can be combined into a single banking-oriented software system.

The application provides secure communication between bank branches while allowing an administrator to monitor the overall system.

---

## 2. Problem Statement

Traditional communication between geographically distributed bank branches may require strong authentication, confidentiality, activity monitoring, and controlled access.

The purpose of this project is to develop a system that provides:

* Secure branch authentication.
* Secure administrator authentication.
* Protected passwords.
* Account lockout mechanisms.
* Encrypted branch communication.
* Activity monitoring.
* Centralized security management.

---

## 3. Proposed Solution

The proposed system introduces a centralized secure branch network.

Each branch has a unique branch code and password.

The system verifies the branch credentials before allowing access.

Repeated authentication failures result in temporary account locking.

Branches can communicate through encrypted messages.

The administrator can monitor system activity without viewing confidential message contents.

---

## 4. User Roles

### 4.1 Branch User

Branch users can:

* Login.
* View dashboard.
* Send messages.
* Receive messages.
* Read messages.
* View profile.
* View activity history.
* Logout.

### 4.2 Administrator

The administrator can:

* Login.
* View branches.
* View branch details.
* View message metadata.
* View system activity.
* View login security.
* Unlock branch accounts.
* Reset branch failed attempts.
* Manage administrator security.
* Logout.

---

## 5. Functional Requirements

### Authentication

The system shall:

1. Accept valid credentials.
2. Reject invalid credentials.
3. Track failed login attempts.
4. Lock accounts after three failures.
5. Automatically release temporary locks.
6. Allow authorized administrator intervention.

### Messaging

The system shall:

1. Allow one branch to send a message to another.
2. Encrypt confidential message content.
3. Store sender and receiver information.
4. Store message timestamp.
5. Track read/unread status.

### Administration

The system shall:

1. Display registered branches.
2. Display branch details.
3. Display message metadata.
4. Display system activity.
5. Display security information.
6. Allow authorized account management.

---

## 6. Non-Functional Requirements

### Security

The system should protect:

* Passwords.
* Sessions.
* Message contents.
* Authentication information.

### Reliability

The system should maintain consistent database records.

### Usability

The interface should be simple enough for bank employees and administrators.

### Maintainability

The application should use modular components so individual features can be modified without affecting the complete system.

### Scalability

The architecture should allow migration from SQLite to a larger database system in future versions.

---

## 7. Security Mechanisms

### 7.1 Password Hashing

Passwords are converted into secure hashes before storage.

Plain-text passwords should never be stored.

### 7.2 Password Salt

A unique salt is associated with password hashing to strengthen password protection.

### 7.3 Login Attempt Monitoring

The system tracks failed authentication attempts.

### 7.4 Temporary Lockout

After three consecutive failed attempts, the account is temporarily locked for five minutes.

### 7.5 AES-256-GCM

Message confidentiality is protected using authenticated encryption.

AES-GCM provides both:

* Confidentiality
* Integrity/authentication

### 7.6 Activity Logging

Important system actions are recorded for auditing.

---

## 8. Database

The system uses SQLite for local persistence.

Major entities include:

```text
Branch
Login Security
Administrator Login Security
Message
Activity
```

The database stores operational information required by the application.

Sensitive information should be stored only in protected form.

---

## 9. Application Flow

```text
Start
  │
  ▼
Main Menu
  │
  ├── Register Branch
  │
  ├── Branch Login
  │      │
  │      ├── Verify account
  │      ├── Verify lock status
  │      ├── Verify password
  │      └── Branch Dashboard
  │
  ├── Administrator Login
  │      │
  │      ├── Verify administrator
  │      └── Admin Dashboard
  │
  ├── About
  │
  └── Exit
```

---

## 10. Frontend

The frontend provides a professional graphical interface over the backend functionality.

The frontend should provide:

* Login screens.
* Dashboard.
* Navigation.
* Messaging interface.
* Branch profile.
* Activity history.
* Administrator dashboard.
* Security monitoring.
* Responsive layout.

The frontend communicates with the application/database layer without exposing sensitive implementation details to the user.

---

## 11. Conclusion

The Secure Bank Branch Network System demonstrates how multiple security concepts can be combined to build a secure communication platform.

The project provides authentication, encryption, account protection, monitoring, logging, database persistence, and a user-friendly frontend.

It can be extended in future with stronger enterprise-level authentication, distributed databases, cloud deployment, and advanced monitoring.

# Secure Bank Branch Network System

## User Guide

---

# 1. Starting the Application

Activate the Python virtual environment.

```bash
venv\Scripts\activate
```

Run the application:

```bash
python main.py
```

If using the Streamlit frontend:

```bash
streamlit run frontend/app.py
```

---

# 2. Main Menu

The application provides:

```text
1. Register Branch
2. Login Branch
3. Admin Login
4. About Project
5. Exit
```

---

# 3. Registering a Branch

Select:

```text
1. Register Branch
```

Enter the requested branch information.

After successful registration, the system creates a unique branch identifier/code.

Example:

```text
SB001
SB002
SB003
```

---

# 4. Branch Login

Select:

```text
2. Login Branch
```

Enter:

```text
Branch Code
Password
```

If the credentials are correct, the branch dashboard will be displayed.

---

# 5. Incorrect Password

When an incorrect password is entered, the system increases the failed-attempt counter.

Example:

```text
Failed login attempts: 1/3
Remaining attempts: 2
```

After three failed attempts:

```text
Account has been temporarily locked.
```

The temporary lock lasts five minutes.

---

# 6. Locked Account

When a branch attempts to log in during the lock period, the system displays the remaining lock time.

Example:

```text
ACCOUNT TEMPORARILY LOCKED

Try again in approximately 4 minute(s).
```

The branch cannot authenticate until the lock expires or an administrator unlocks the account.

---

# 7. Branch Dashboard

After successful authentication, the branch dashboard provides:

```text
1. Secure Messaging
2. Branch Profile
3. Activity History
4. Logout
```

---

# 8. Secure Messaging

Branches can communicate with other registered branches.

The sender selects the destination branch and enters the message.

The message is protected using encryption before storage.

The receiver can later read the message.

---

# 9. Branch Profile

The profile section displays branch information such as:

```text
Branch ID
Branch Code
Branch Name
Registration Date
Account Status
Security Status
```

---

# 10. Activity History

The branch can view its recorded activities.

Examples include:

```text
LOGIN
LOGOUT
MESSAGE_SENT
MESSAGE_READ
PROFILE_VIEWED
FAILED_LOGIN
```

---

# 11. Administrator Login

Select:

```text
3. Admin Login
```

Enter the administrator credentials.

Successful authentication opens the administrator dashboard.

---

# 12. Administrator Dashboard

The dashboard contains:

```text
1. View All Branches
2. View Branch Details
3. View All Messages
4. View System Activity
5. View Login Security
6. Logout
```

---

# 13. View All Branches

This section displays all registered branches.

Typical information:

```text
ID
Branch Code
Branch Name
Registered Date
```

---

# 14. View Branch Details

The administrator can enter a branch code and view information about that branch.

The administrator can see branch metadata and security status.

---

# 15. View All Messages

The administrator can see message metadata such as:

```text
Message ID
Sender
Receiver
Date
Status
```

Confidential message content is not displayed to the administrator.

---

# 16. View System Activity

The activity screen provides an audit trail of important system operations.

Examples:

```text
ADMIN_LOGIN
ADMIN_LOGOUT
ADMIN_FAILED_LOGIN
LOGIN
LOGOUT
FAILED_LOGIN
MESSAGE_SENT
MESSAGE_READ
PROFILE_VIEWED
```

---

# 17. Login Security

The security screen displays:

```text
Branch
Failed Attempts
Lock Status
Locked Until
```

Administrator security information is also displayed.

---

# 18. Unlock Branch Account

If a branch account is locked:

1. Open Login Security.
2. Select Unlock Branch Account.
3. Enter the branch code.
4. Confirm the operation.

The system resets the failed attempts and removes the temporary lock.

---

# 19. Reset Failed Attempts

The administrator can reset a branch's failed login counter.

This is useful when an authorized branch needs its authentication status reset.

---

# 20. Logout

Always use the Logout option after completing work.

The application:

```text
Records logout activity
Destroys the active session
Returns to the main menu
```

---

# 21. Security Recommendations

Users should:

* Never share passwords.
* Never store passwords in plain text.
* Always logout after use.
* Use strong passwords.
* Avoid sharing branch credentials.
* Report suspicious login activity.
* Keep the application and dependencies updated.

Administrators should regularly review:

* Failed logins.
* Locked accounts.
* Activity logs.
* Message metadata.
* Security events.

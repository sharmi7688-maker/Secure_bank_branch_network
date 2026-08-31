# Project Structure

## Secure Bank Branch Network System

```text
Secure_Bank_Branch_Network/
│
├── main.py
│
├── requirements.txt
├── README.md
├── LICENSE
├── .gitignore
│
├── database/
│   └── bank.db
│
├── frontend/
│   ├── app.py
│   ├── assets/
│   │   ├── css/
│   │   ├── images/
│   │   └── icons/
│   └── components/
│
├── backend/
│   ├── authentication/
│   ├── messaging/
│   ├── security/
│   ├── database/
│   └── utilities/
│
└── docs/
    ├── PROJECT_DOCUMENTATION.md
    ├── USER_GUIDE.md
    ├── SECURITY_DOCUMENTATION.md
    ├── DATABASE_DOCUMENTATION.md
    ├── TESTING_DOCUMENTATION.md
    └── PROJECT_STRUCTURE.md
```

---

## Main Components

### main.py

Application entry point for the project.

---

### database/

Contains the SQLite database and/or database initialization components.

---

### frontend/

Contains the graphical user interface.

The frontend is responsible for:

* Login screens.
* Dashboards.
* Navigation.
* Messaging interface.
* Security interface.
* Visual presentation.

---

### backend/

Contains the application's business logic.

Major responsibilities include:

```text
Authentication
Messaging
Encryption
Security
Database Operations
Activity Logging
Session Management
```

---

### docs/

Contains project documentation.

Documentation includes:

```text
Project Documentation
User Guide
Security Documentation
Database Documentation
Testing Documentation
Project Structure
```

---

# Recommended Development Principle

Frontend code should communicate with backend functions rather than directly duplicating security logic.

Conceptually:

```text
Frontend
   ↓
Application/Service Layer
   ↓
Security & Business Logic
   ↓
Database
```

This makes the project easier to maintain and improves separation of responsibilities.

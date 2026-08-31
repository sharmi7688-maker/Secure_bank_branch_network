import sqlite3


def create_database():
    """
    Creates the database and the branches table.
    """

    # Connect to the database
    connection = sqlite3.connect("database/bank.db")

    # Create a cursor
    cursor = connection.cursor()

    # Create the branches table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS branches (
            branch_id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch_name TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            created_date TEXT NOT NULL
        )
    """)

    # Save changes
    connection.commit()

    # Close the connection
    connection.close()

    print("Database created successfully.")
    print("Branches table created successfully.")


def check_branches_table():
    """
    Checks whether the branches table exists.
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        AND name = 'branches'
    """)

    result = cursor.fetchone()

    

    if result:
        print("Branches table verified successfully.")

        cursor.execute("PRAGMA table_info(branches)")
        columns = cursor.fetchall()

        print("\nBranches Table Structure:")
        print("-" * 50)

        for column in columns:
            print(f"Column: {column[1]} | Type: {column[2]}")

        print("-" * 50)

    else:
        print("Branches table was not found.")

    connection.close()   
   

def insert_branch(branch_name, password_hash, password_salt, created_date):
    """
    Inserts a new branch into the branches table.
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO branches
        (branch_name, password_hash, password_salt, created_date)
        VALUES (?, ?, ?, ?)
    """, (branch_name, password_hash, password_salt, created_date))

    connection.commit()

    branch_id = cursor.lastrowid

    connection.close()

    return branch_id     

def get_all_branches():
    """
    Retrieves registered branch information.
    Password hash and salt are not returned.
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT branch_id, branch_name, created_date
        FROM branches
        ORDER BY branch_id
    """)

    branches = cursor.fetchall()

    connection.close()

    return branches

def branch_exists(branch_name):
    """
    Checks whether a branch with the given name already exists.
    Returns True if the branch exists, otherwise False.
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT branch_id
        FROM branches
        WHERE LOWER(branch_name) = LOWER(?)
    """, (branch_name,))

    result = cursor.fetchone()

    connection.close()

    return result is not None

def get_branch_by_code(branch_code):
    """
    Retrieves a branch using its Secure Bank branch code.

    Valid examples:
        SB001
        SB002
        SB010

    Returns:
        Branch information if the code is valid and exists.
        None if the code is invalid or the branch does not exist.
    """

    # Check whether input is a string
    if not isinstance(branch_code, str):
        return None

    # Remove unnecessary spaces and convert to uppercase
    branch_code = branch_code.strip().upper()

    # Secure Bank branch code must have exactly 5 characters
    if len(branch_code) != 5:
        return None

    # First two characters must be SB
    if not branch_code.startswith("SB"):
        return None

    # Last three characters must be digits
    if not branch_code[2:].isdigit():
        return None

    # Convert SB003 -> 3
    branch_id = int(branch_code[2:])

    # Branch IDs must be greater than zero
    if branch_id <= 0:
        return None

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            branch_id,
            branch_name,
            password_hash,
            password_salt
        FROM branches
        WHERE branch_id = ?
    """, (branch_id,))

    branch = cursor.fetchone()

    connection.close()

    return branch

def create_messages_table():
    """
    Creates the messages table if it does not already exist.
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_branch_id INTEGER NOT NULL,
            receiver_branch_id INTEGER NOT NULL,
            encrypted_message TEXT NOT NULL,
            nonce TEXT NOT NULL,
            sent_date TEXT NOT NULL,
            is_read INTEGER NOT NULL DEFAULT 0,

            FOREIGN KEY (sender_branch_id)
                REFERENCES branches(branch_id),

            FOREIGN KEY (receiver_branch_id)
                REFERENCES branches(branch_id)
        )
    """)

    connection.commit()
    connection.close()

def get_messages_table_structure():
    """
    Returns the structure of the messages table.
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("PRAGMA table_info(messages)")

    columns = cursor.fetchall()

    connection.close()

    return columns    

def save_message(
    sender_branch_id,
    receiver_branch_id,
    encrypted_message,
    nonce,
    sent_date
):
    """
    Saves an encrypted message to the messages table.
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO messages (
            sender_branch_id,
            receiver_branch_id,
            encrypted_message,
            nonce,
            sent_date
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        sender_branch_id,
        receiver_branch_id,
        encrypted_message,
        nonce,
        sent_date
    ))

    connection.commit()

    message_id = cursor.lastrowid

    connection.close()

    return message_id

def get_message_by_id(message_id):
    """
    Retrieves a message from the messages table
    using its message ID.
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            message_id,
            sender_branch_id,
            receiver_branch_id,
            encrypted_message,
            nonce,
            sent_date,
            is_read
        FROM messages
        WHERE message_id = ?
    """, (message_id,))

    message = cursor.fetchone()

    connection.close()

    return message

def get_messages_for_branch(branch_id):
    """
    Retrieves messages received by a specific branch.
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            message_id,
            sender_branch_id,
            receiver_branch_id,
            encrypted_message,
            nonce,
            sent_date,
            is_read
        FROM messages
        WHERE receiver_branch_id = ?
        ORDER BY message_id DESC
    """, (branch_id,))

    messages = cursor.fetchall()

    connection.close()

    return messages


def mark_message_as_read(message_id, branch_id):
    """
    Marks a message as read only if the message
    belongs to the specified receiver branch.
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE messages
        SET is_read = 1
        WHERE message_id = ?
        AND receiver_branch_id = ?
    """, (
        message_id,
        branch_id
    ))

    connection.commit()

    updated_rows = cursor.rowcount

    connection.close()

    return updated_rows

def get_branch_by_id(branch_id):
    """
    Retrieves branch details using branch ID.
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            branch_id,
            branch_name
        FROM branches
        WHERE branch_id = ?
    """, (branch_id,))

    branch = cursor.fetchone()

    connection.close()

    return branch

def get_sent_messages_for_branch(branch_id):
    """
    Retrieves messages sent by a specific branch.
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            message_id,
            sender_branch_id,
            receiver_branch_id,
            encrypted_message,
            nonce,
            sent_date,
            is_read
        FROM messages
        WHERE sender_branch_id = ?
        ORDER BY message_id DESC
    """, (branch_id,))

    messages = cursor.fetchall()

    connection.close()

    return messages

def get_branch_profile(branch_id):
    """
    Retrieves profile information for a specific branch.
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            branch_id,
            branch_name,
            created_date
        FROM branches
        WHERE branch_id = ?
    """, (branch_id,))

    branch = cursor.fetchone()

    connection.close()

    return branch

def create_activity_logs_table():
    """
    Creates the activity_logs table if it does not already exist.
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch_id INTEGER NOT NULL,
            activity_type TEXT NOT NULL,
            description TEXT NOT NULL,
            activity_date TEXT NOT NULL,

            FOREIGN KEY (branch_id)
                REFERENCES branches(branch_id)
        )
    """)

    connection.commit()
    connection.close()

def log_activity(
    branch_id,
    activity_type,
    description,
    activity_date
):
    """
    Saves a branch activity to the activity_logs table.
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO activity_logs (
            branch_id,
            activity_type,
            description,
            activity_date
        )
        VALUES (?, ?, ?, ?)
    """, (
        branch_id,
        activity_type,
        description,
        activity_date
    ))

    connection.commit()

    log_id = cursor.lastrowid

    connection.close()

    return log_id

def get_activities_for_branch(branch_id):
    """
    Retrieves activity history for a specific branch.
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            log_id,
            branch_id,
            activity_type,
            description,
            activity_date
        FROM activity_logs
        WHERE branch_id = ?
        ORDER BY log_id DESC
    """, (branch_id,))

    activities = cursor.fetchall()

    connection.close()

    return activities    

def create_login_security_table():
    """
    Creates the login_security table if it does not already exist.
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS login_security (
            branch_id INTEGER PRIMARY KEY,
            failed_attempts INTEGER NOT NULL DEFAULT 0,
            locked_until TEXT,

            FOREIGN KEY (branch_id)
                REFERENCES branches(branch_id)
        )
    """)

    connection.commit()
    connection.close()

def create_admins_table():
    """
    Creates the admins table if it does not already exist.
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            created_date TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()

def insert_admin(
    username,
    password_hash,
    password_salt,
    created_date
):
    """
    Inserts a new administrator into the admins table.
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO admins (
            username,
            password_hash,
            password_salt,
            created_date
        )
        VALUES (?, ?, ?, ?)
    """, (
        username,
        password_hash,
        password_salt,
        created_date
    ))

    connection.commit()

    admin_id = cursor.lastrowid

    connection.close()

    return admin_id

def admin_exists(username):
    """
    Checks whether an administrator username already exists.

    Returns:
        True  -> username exists
        False -> username does not exist
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT admin_id
        FROM admins
        WHERE LOWER(username) = LOWER(?)
    """, (username,))

    result = cursor.fetchone()

    connection.close()

    return result is not None

def get_admin_by_username(username):
    """
    Retrieves administrator information using username.

    Password hash and salt are returned only for
    authentication purposes.
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            admin_id,
            username,
            password_hash,
            password_salt
        FROM admins
        WHERE LOWER(username) = LOWER(?)
    """, (username,))

    admin = cursor.fetchone()

    connection.close()

    return admin


def get_all_branches_admin():
    """
    Retrieves all registered branches for the admin dashboard.

    Password information is never returned.
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            branch_id,
            branch_name,
            created_date
        FROM branches
        ORDER BY branch_id
    """)

    branches = cursor.fetchall()

    connection.close()

    return branches


def get_all_messages_admin():
    """
    Retrieves all messages for administrator monitoring.

    Encrypted message content is returned because the admin
    dashboard will display message metadata only.
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            message_id,
            sender_branch_id,
            receiver_branch_id,
            sent_date,
            is_read
        FROM messages
        ORDER BY message_id DESC
    """)

    messages = cursor.fetchall()

    connection.close()

    return messages


def get_all_activities_admin():
    """
    Retrieves activity logs from both branches
    and administrators.

    Returns:
        actor, activity_type, description, activity_date
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            'BRANCH' AS actor_type,
            printf('SB%03d', al.branch_id) AS actor,
            al.activity_type,
            al.description,
            al.activity_date
        FROM activity_logs al

        UNION ALL

        SELECT
            'ADMIN' AS actor_type,
            a.username AS actor,
            aal.activity_type,
            aal.description,
            aal.activity_date
        FROM admin_activity_logs aal

        INNER JOIN admins a
            ON aal.admin_id = a.admin_id

        ORDER BY activity_date DESC
    """)

    activities = cursor.fetchall()

    connection.close()

    return activities


def get_all_login_security_admin():
    """
    Retrieves login security information for all registered branches.

    Every registered branch is displayed, even if it does not
    yet have a record in the login_security table.
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            b.branch_id,
            COALESCE(ls.failed_attempts, 0),
            ls.locked_until
        FROM branches b
        LEFT JOIN login_security ls
            ON b.branch_id = ls.branch_id
        ORDER BY b.branch_id
    """)

    security_records = cursor.fetchall()

    connection.close()

    return security_records

def create_admin_activity_logs_table():
    """
    Creates the administrator activity log table
    if it does not already exist.
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_activity_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL,
            activity_type TEXT NOT NULL,
            description TEXT NOT NULL,
            activity_date TEXT NOT NULL,

            FOREIGN KEY (admin_id)
                REFERENCES admins(admin_id)
        )
    """)

    connection.commit()
    connection.close()


def log_admin_activity(
    admin_id,
    activity_type,
    description,
    activity_date
):
    """
    Records an administrator security activity.
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO admin_activity_logs (
            admin_id,
            activity_type,
            description,
            activity_date
        )
        VALUES (?, ?, ?, ?)
    """, (
        admin_id,
        activity_type,
        description,
        activity_date
    ))

    connection.commit()

    log_id = cursor.lastrowid

    connection.close()

    return log_id


def get_all_admin_activities():
    """
    Retrieves all administrator activities.
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            aal.log_id,
            a.username,
            aal.activity_type,
            aal.description,
            aal.activity_date
        FROM admin_activity_logs aal
        INNER JOIN admins a
            ON aal.admin_id = a.admin_id
        ORDER BY aal.log_id DESC
    """)

    activities = cursor.fetchall()

    connection.close()

    return activities

def create_admin_login_security_table():
    """
    Creates the admin_login_security table if it does not already exist.
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_login_security (
            admin_id INTEGER PRIMARY KEY,
            failed_attempts INTEGER NOT NULL DEFAULT 0,
            locked_until TEXT,

            FOREIGN KEY (admin_id)
                REFERENCES admins(admin_id)
        )
    """)

    connection.commit()
    connection.close()


def initialize_admin_login_security(admin_id):
    """
    Creates a login-security record for an administrator
    if one does not already exist.
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO admin_login_security (
            admin_id,
            failed_attempts,
            locked_until
        )
        VALUES (?, 0, NULL)
    """, (admin_id,))

    connection.commit()
    connection.close()


def get_admin_login_security(admin_id):
    """
    Retrieves login-security information for an administrator.

    Returns:
        Tuple containing:
        failed_attempts,
        locked_until

        None if no record exists.
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            failed_attempts,
            locked_until
        FROM admin_login_security
        WHERE admin_id = ?
    """, (admin_id,))

    result = cursor.fetchone()

    connection.close()

    return result


def update_admin_login_security(
    admin_id,
    failed_attempts,
    locked_until
):
    """
    Updates administrator login-security information.
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE admin_login_security
        SET
            failed_attempts = ?,
            locked_until = ?
        WHERE admin_id = ?
    """, (
        failed_attempts,
        locked_until,
        admin_id
    ))

    connection.commit()
    connection.close()    

def get_all_admin_login_security():
    """
    Retrieves login-security information for all administrators.

    Returns:
        List containing:
        username,
        failed_attempts,
        locked_until
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            a.username,
            als.failed_attempts,
            als.locked_until
        FROM admins a
        LEFT JOIN admin_login_security als
            ON a.admin_id = als.admin_id
        ORDER BY a.admin_id
    """)

    security_records = cursor.fetchall()

    connection.close()

    return security_records    

def get_all_admin_login_security_details():
    """
    Retrieves administrator login-security information.

    Returns:
        admin_id,
        username,
        failed_attempts,
        locked_until
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            a.admin_id,
            a.username,
            COALESCE(als.failed_attempts, 0),
            als.locked_until
        FROM admins a
        LEFT JOIN admin_login_security als
            ON a.admin_id = als.admin_id
        ORDER BY a.admin_id
    """)

    security_records = cursor.fetchall()

    connection.close()

    return security_records


def reset_branch_login_security(branch_id):
    """
    Resets failed login attempts and removes
    the lock for a branch.

    Returns:
        True  -> Branch security record was updated.
        False -> Branch was not found.
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT branch_id
        FROM branches
        WHERE branch_id = ?
    """, (branch_id,))

    branch = cursor.fetchone()

    if branch is None:

        connection.close()
        return False

    cursor.execute("""
        INSERT OR IGNORE INTO login_security (
            branch_id,
            failed_attempts,
            locked_until
        )
        VALUES (?, 0, NULL)
    """, (branch_id,))

    cursor.execute("""
        UPDATE login_security
        SET
            failed_attempts = 0,
            locked_until = NULL
        WHERE branch_id = ?
    """, (branch_id,))

    connection.commit()
    connection.close()

    return True


def reset_admin_login_security(admin_id):
    """
    Resets failed login attempts and removes
    the lock for an administrator.

    Returns:
        True  -> Admin security record was updated.
        False -> Administrator was not found.
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT admin_id
        FROM admins
        WHERE admin_id = ?
    """, (admin_id,))

    admin = cursor.fetchone()

    if admin is None:

        connection.close()
        return False

    cursor.execute("""
        INSERT OR IGNORE INTO admin_login_security (
            admin_id,
            failed_attempts,
            locked_until
        )
        VALUES (?, 0, NULL)
    """, (admin_id,))

    cursor.execute("""
        UPDATE admin_login_security
        SET
            failed_attempts = 0,
            locked_until = NULL
        WHERE admin_id = ?
    """, (admin_id,))

    connection.commit()
    connection.close()

    return True
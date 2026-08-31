from modules.admin_session import (
    get_current_admin_session,
    is_admin_logged_in,
    destroy_admin_session
)

from database.database import (
    get_all_branches_admin,
    get_all_messages_admin,
    get_all_activities_admin,
    get_all_login_security_admin,
    get_all_admin_login_security_details,
    get_branch_by_id,
    get_message_by_id,
    get_admin_by_username,
    log_activity,
    log_admin_activity,
    reset_branch_login_security,
    reset_admin_login_security
)

from datetime import datetime


def get_branch_code(branch_id):
    return f"SB{branch_id:03d}"


def show_all_branches():
    """
    Displays all registered branches.
    """

    branches = get_all_branches_admin()

    print("\n" + "=" * 80)
    print("                         ALL BRANCHES")
    print("=" * 80)

    if len(branches) == 0:

        print("\nNo branches registered.")

        input("\nPress Enter to return...")
        return

    print("\n" + "-" * 80)

    print(
        f"{'ID':<6}"
        f"{'Branch Code':<16}"
        f"{'Branch Name':<25}"
        f"{'Registered Date':<24}"
    )

    print("-" * 80)

    for branch_id, branch_name, created_date in branches:

        branch_code = get_branch_code(branch_id)

        print(
            f"{branch_id:<6}"
            f"{branch_code:<16}"
            f"{branch_name:<25}"
            f"{created_date:<24}"
        )

    print("-" * 80)

    input("\nPress Enter to return to Admin Dashboard...")


def show_branch_details():
    """
    Displays details of a selected branch.
    """

    print("\n" + "=" * 60)
    print("                    BRANCH DETAILS")
    print("=" * 60)

    branch_code = input(
        "\nEnter Branch Code: "
    ).strip().upper()

    if not branch_code.startswith("SB"):

        print("\nInvalid Branch Code.")
        input("\nPress Enter to return...")
        return

    try:

        branch_id = int(branch_code[2:])

    except ValueError:

        print("\nInvalid Branch Code.")
        input("\nPress Enter to return...")
        return

    branch = get_branch_by_id(branch_id)

    if branch is None:

        print("\nBranch not found.")
        input("\nPress Enter to return...")
        return

    (
        branch_id,
        branch_name
    ) = branch

    # Get registration date separately
    branches = get_all_branches_admin()

    created_date = None

    for item in branches:

        if item[0] == branch_id:

            created_date = item[2]
            break

    print("\n" + "-" * 60)

    print(f"Branch ID       : {branch_id}")
    print(f"Branch Code     : {get_branch_code(branch_id)}")
    print(f"Branch Name     : {branch_name}")
    print(f"Registered Date : {created_date}")

    print("\nAccount Status  : ACTIVE")
    print("Security Status : PROTECTED")

    print("-" * 60)

    input("\nPress Enter to return to Admin Dashboard...")


def show_message_details():
    """
    Displays metadata/details of a selected message.

    The actual message content is never decrypted or displayed
    to the administrator.
    """

    print("\n" + "=" * 60)
    print("                    MESSAGE DETAILS")
    print("=" * 60)

    message_id_input = input(
        "\nEnter Message ID: "
    ).strip()

    if not message_id_input.isdigit():

        print("\nInvalid Message ID.")

        input("\nPress Enter to return...")
        return

    message_id = int(message_id_input)

    message = get_message_by_id(message_id)

    if message is None:

        print("\nMessage not found.")

        input("\nPress Enter to return...")
        return

    (
        message_id,
        sender_branch_id,
        receiver_branch_id,
        encrypted_message,
        nonce,
        sent_date,
        is_read
    ) = message

    sender_branch = get_branch_by_id(
        sender_branch_id
    )

    receiver_branch = get_branch_by_id(
        receiver_branch_id
    )

    if sender_branch is None:

        sender_name = "Unknown"

    else:

        sender_name = sender_branch[1]

    if receiver_branch is None:

        receiver_name = "Unknown"

    else:

        receiver_name = receiver_branch[1]

    sender_code = get_branch_code(
        sender_branch_id
    )

    receiver_code = get_branch_code(
        receiver_branch_id
    )

    status = (
        "READ"
        if is_read == 1
        else "UNREAD"
    )

    print("\n" + "-" * 60)

    print(
        f"Message ID       : {message_id}"
    )

    print(
        f"Sender Branch    : "
        f"{sender_name} ({sender_code})"
    )

    print(
        f"Receiver Branch  : "
        f"{receiver_name} ({receiver_code})"
    )

    print(
        f"Sent Date        : {sent_date}"
    )

    print(
        f"Message Status   : {status}"
    )

    print(
        f"Encryption       : AES-256-GCM"
    )

    print(
        f"Message Content  : PROTECTED"
    )

    print("-" * 60)

    print("\nSecurity Notice:")
    print(
        "The administrator can view message metadata,"
    )
    print(
        "but confidential message content is not displayed."
    )

    print("-" * 60)

    input(
        "\nPress Enter to return to All Messages..."
    )


def show_all_messages():
    """
    Displays message metadata for all messages.

    The administrator cannot view decrypted message content.
    """

    while True:

        messages = get_all_messages_admin()

        print("\n" + "=" * 90)
        print("                         ALL MESSAGES")
        print("=" * 90)

        if len(messages) == 0:

            print("\nNo messages found.")

            print("\n" + "-" * 60)
            print("1. Back")
            print("-" * 60)

            choice = input(
                "Enter your choice: "
            ).strip()

            if choice == "1":

                return

            print("\nInvalid choice.")

            continue

        print("\n" + "-" * 90)

        print(
            f"{'ID':<6}"
            f"{'From':<12}"
            f"{'To':<12}"
            f"{'Date':<24}"
            f"{'Status':<12}"
        )

        print("-" * 90)

        for (
            message_id,
            sender_branch_id,
            receiver_branch_id,
            sent_date,
            is_read
        ) in messages:

            sender_code = get_branch_code(
                sender_branch_id
            )

            receiver_code = get_branch_code(
                receiver_branch_id
            )

            status = (
                "READ"
                if is_read == 1
                else "UNREAD"
            )

            print(
                f"{message_id:<6}"
                f"{sender_code:<12}"
                f"{receiver_code:<12}"
                f"{sent_date:<24}"
                f"{status:<12}"
            )

        print("-" * 90)

        print("\n1. View Message Details")
        print("2. Refresh")
        print("3. Back")

        choice = input(
            "\nEnter your choice (1-3): "
        ).strip()

        if choice == "1":

            show_message_details()

        elif choice == "2":

            print("\nRefreshing Messages...")

        elif choice == "3":

            print("\nReturning to Admin Dashboard...")
            return

        else:

            print("\nInvalid choice.")
            print("Please enter a number from 1 to 3.")


def show_system_activity():
    """
    Displays activity logs from all branches
    and administrators.
    """

    activities = get_all_activities_admin()

    print("\n" + "=" * 130)
    print("                         SYSTEM ACTIVITY")
    print("=" * 130)

    if len(activities) == 0:

        print("\nNo activity records found.")

        input("\nPress Enter to return...")
        return

    print("\n" + "-" * 130)

    print(
        f"{'Type':<10}"
        f"{'Actor':<12}"
        f"{'Activity':<35}"
        f"{'Description':<50}"
        f"{'Date & Time':<22}"
    )

    print("-" * 130)

    for (
        actor_type,
        actor,
        activity_type,
        description,
        activity_date
    ) in activities:
        
        # Convert values to strings so formatting
        # works safely even if a database value is None.
        actor_type = str(actor_type)
        actor = str(actor)
        activity_type = str(activity_type) 
        description = str(description) 
        activity_date = str(activity_date)

        # Keep long activity names from breaking 
        # the table layout. 
        if len(activity_type) > 28: 

            activity_display = ( 
                activity_type[:27] + "..." 
            )

        else: 

            activity_display = activity_type

        # Keep long descriptions from breaking 
        # the table layout.  

        if len(description) > 43: 
            description_display = ( 
                description[:40] + "..." 
            )  

        else: 

            description_display = description

        print(
            f"{actor_type:<10}"
            f"{actor:<12}"
            f"{activity_display:<35}"
            f"{description_display:<50}"
            f"{activity_date:<22}"
        )

    print("-" * 130)

    input("\nPress Enter to return to Admin Dashboard...")

def unlock_branch_account():
    """
    Manually unlocks a branch account.

    The action is recorded in administrator activity logs.
    """

    print("\n" + "=" * 60)
    print("                 UNLOCK BRANCH ACCOUNT")
    print("=" * 60)

    branch_code = input(
        "\nEnter Branch Code: "
    ).strip().upper()

    if not branch_code.startswith("SB"):

        print("\nInvalid Branch Code.")
        input("\nPress Enter to return...")
        return

    if len(branch_code) != 5:

        print("\nInvalid Branch Code.")
        input("\nPress Enter to return...")
        return

    if not branch_code[2:].isdigit():

        print("\nInvalid Branch Code.")
        input("\nPress Enter to return...")
        return

    branch_id = int(branch_code[2:])

    if branch_id <= 0:

        print("\nInvalid Branch Code.")
        input("\nPress Enter to return...")
        return

    branch = get_branch_by_id(branch_id)

    if branch is None:

        print("\nBranch not found.")
        input("\nPress Enter to return...")
        return

    branch_name = branch[1]

    success = reset_branch_login_security(
        branch_id
    )

    if success:

        current_time = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        current_admin = get_current_admin_session()

        log_admin_activity(
            current_admin["admin_id"],
            "ADMIN_UNLOCK_BRANCH",
            (
                f"Administrator unlocked branch "
                f"{branch_code} ({branch_name})"
            ),
            current_time
        )

        print("\nBranch account successfully unlocked.")
        print(f"Branch Code : {branch_code}")
        print(f"Branch Name : {branch_name}")
        print("Failed attempts reset to 0.")
        print("Lock status : NOT LOCKED")

    else:

        print("\nUnable to unlock branch account.")

    input("\nPress Enter to return to Login Security...")


def unlock_admin_account():
    """
    Manually unlocks an administrator account.

    The action is recorded in administrator activity logs.
    """

    print("\n" + "=" * 60)
    print("             UNLOCK ADMINISTRATOR ACCOUNT")
    print("=" * 60)

    username = input(
        "\nEnter Admin Username: "
    ).strip()

    if username == "":

        print("\nUsername cannot be empty.")
        input("\nPress Enter to return...")
        return

    

    admin = get_admin_by_username(username)

    if admin is None:

        print("\nAdministrator not found.")
        input("\nPress Enter to return...")
        return

    (
        admin_id,
        stored_username,
        stored_hash,
        stored_salt
    ) = admin

    success = reset_admin_login_security(
        admin_id
    )

    if success:

        current_time = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        current_admin = get_current_admin_session()

        log_admin_activity(
            current_admin["admin_id"],
            "ADMIN_UNLOCK_ADMIN",
            (
                f"Administrator unlocked account "
                f"'{stored_username}'"
            ),
            current_time
        )

        print(
            "\nAdministrator account successfully unlocked."
        )

        print(
            f"Username : {stored_username}"
        )

        print(
            "Failed attempts reset to 0."
        )

        print(
            "Lock status : NOT LOCKED"
        )

    else:

        print(
            "\nUnable to unlock administrator account."
        )

    input("\nPress Enter to return to Login Security...")


def reset_branch_attempts():
    """
    Resets failed login attempts for a branch.
    """

    print("\n" + "=" * 60)
    print("             RESET BRANCH LOGIN ATTEMPTS")
    print("=" * 60)

    branch_code = input(
        "\nEnter Branch Code: "
    ).strip().upper()

    if not branch_code.startswith("SB"):

        print("\nInvalid Branch Code.")
        input("\nPress Enter to return...")
        return

    if len(branch_code) != 5:

        print("\nInvalid Branch Code.")
        input("\nPress Enter to return...")
        return

    if not branch_code[2:].isdigit():

        print("\nInvalid Branch Code.")
        input("\nPress Enter to return...")
        return

    branch_id = int(branch_code[2:])

    branch = get_branch_by_id(branch_id)

    if branch is None:

        print("\nBranch not found.")
        input("\nPress Enter to return...")
        return

    branch_name = branch[1]

    success = reset_branch_login_security(
        branch_id
    )

    if success:

        current_time = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        current_admin = get_current_admin_session()

        log_admin_activity(
            current_admin["admin_id"],
            "ADMIN_RESET_BRANCH_ATTEMPTS",
            (
                f"Administrator reset failed login "
                f"attempts for {branch_code} "
                f"({branch_name})"
            ),
            current_time
        )

        print("\nBranch login attempts reset successfully.")
        print(f"Branch Code : {branch_code}")
        print("Failed attempts : 0")

    else:

        print("\nUnable to reset branch attempts.")

    input("\nPress Enter to return to Login Security...")


def reset_admin_attempts():
    """
    Resets failed login attempts for an administrator.
    """

    print("\n" + "=" * 60)
    print("          RESET ADMIN LOGIN ATTEMPTS")
    print("=" * 60)

    username = input(
        "\nEnter Admin Username: "
    ).strip()

    if username == "":

        print("\nUsername cannot be empty.")
        input("\nPress Enter to return...")
        return

 

    admin = get_admin_by_username(username)

    if admin is None:

        print("\nAdministrator not found.")
        input("\nPress Enter to return...")
        return

    (
        admin_id,
        stored_username,
        stored_hash,
        stored_salt
    ) = admin

    success = reset_admin_login_security(
        admin_id
    )

    if success:

        current_time = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        current_admin = get_current_admin_session()

        log_admin_activity(
            current_admin["admin_id"],
            "ADMIN_RESET_ADMIN_ATTEMPTS",
            (
                f"Administrator reset failed login "
                f"attempts for admin "
                f"'{stored_username}'"
            ),
            current_time
        )

        print(
            "\nAdministrator login attempts reset successfully."
        )

        print(
            f"Username : {stored_username}"
        )

        print(
            "Failed attempts : 0"
        )

    else:

        print(
            "\nUnable to reset administrator attempts."
        )

    input("\nPress Enter to return to Login Security...")

def show_login_security():
    """
    Displays login security information for branches
    and administrators.

    The administrator can also access security-management
    operations from this screen.
    """

    while True:

        security_records = get_all_login_security_admin()

        print("\n" + "=" * 85)
        print("                         LOGIN SECURITY")
        print("=" * 85)

        # --------------------------------------------------
        # BRANCH LOGIN SECURITY
        # --------------------------------------------------

        print("\nBRANCH LOGIN SECURITY")
        print("-" * 85)

        if len(security_records) == 0:

            print("No branch security records found.")

        else:

            print(
                f"{'Branch':<12}"
                f"{'Failed Attempts':<20}"
                f"{'Lock Status':<18}"
                f"{'Locked Until':<22}"
            )

            print("-" * 85)

            current_time = datetime.now()

            for (
                branch_id,
                failed_attempts,
                locked_until
            ) in security_records:

                branch_code = get_branch_code(
                    branch_id
                )

                locked = False

                if locked_until is not None:

                    try:

                        lock_time = datetime.strptime(
                            locked_until,
                            "%Y-%m-%d %H:%M:%S"
                        )

                        if current_time < lock_time:

                            locked = True

                    except ValueError:

                        locked = False

                status = (
                    "LOCKED"
                    if locked
                    else "NOT LOCKED"
                )

                lock_display = (
                    locked_until
                    if locked
                    else "-"
                )

                print(
                    f"{branch_code:<12}"
                    f"{failed_attempts:<20}"
                    f"{status:<18}"
                    f"{lock_display:<22}"
                )

            print("-" * 85)

        # --------------------------------------------------
        # ADMINISTRATOR LOGIN SECURITY
        # --------------------------------------------------

        admin_security_records = (
            get_all_admin_login_security_details()
        )

        print("\nADMINISTRATOR LOGIN SECURITY")
        print("-" * 85)

        if len(admin_security_records) == 0:

            print("No administrator security records found.")

        else:

            print(
                f"{'Admin':<15}"
                f"{'Failed Attempts':<20}"
                f"{'Lock Status':<18}"
                f"{'Locked Until':<22}"
            )

            print("-" * 85)

            current_time = datetime.now()

            for (
                admin_id,
                username,
                failed_attempts,
                locked_until
            ) in admin_security_records:

                locked = False

                if locked_until is not None:

                    try:

                        lock_time = datetime.strptime(
                            locked_until,
                            "%Y-%m-%d %H:%M:%S"
                        )

                        if current_time < lock_time:

                            locked = True

                    except ValueError:

                        locked = False

                status = (
                    "LOCKED"
                    if locked
                    else "NOT LOCKED"
                )

                lock_display = (
                    locked_until
                    if locked
                    else "-"
                )

                print(
                    f"{username:<15}"
                    f"{failed_attempts:<20}"
                    f"{status:<18}"
                    f"{lock_display:<22}"
                )

            print("-" * 85)

        # --------------------------------------------------
        # SECURITY MANAGEMENT MENU
        # --------------------------------------------------

        print("\nSECURITY MANAGEMENT")
        print("-" * 85)

        print("1. Unlock Branch Account")
        print("2. Unlock Administrator Account")
        print("3. Reset Branch Failed Attempts")
        print("4. Reset Administrator Failed Attempts")
        print("5. Refresh")
        print("6. Back")

        print("-" * 85)

        choice = input(
            "Enter your choice (1-6): "
        ).strip()

        # --------------------------------------------------
        # 1. UNLOCK BRANCH
        # --------------------------------------------------

        if choice == "1":

            unlock_branch_account()

        # --------------------------------------------------
        # 2. UNLOCK ADMIN
        # --------------------------------------------------

        elif choice == "2":

            unlock_admin_account()

        # --------------------------------------------------
        # 3. RESET BRANCH ATTEMPTS
        # --------------------------------------------------

        elif choice == "3":

            reset_branch_attempts()

        # --------------------------------------------------
        # 4. RESET ADMIN ATTEMPTS
        # --------------------------------------------------

        elif choice == "4":

            reset_admin_attempts()

        # --------------------------------------------------
        # 5. REFRESH
        # --------------------------------------------------

        elif choice == "5":

            print("\nRefreshing Login Security...")

        # --------------------------------------------------
        # 6. BACK
        # --------------------------------------------------

        elif choice == "6":

            print("\nReturning to Admin Dashboard...")
            return

        else:

            print("\nInvalid choice.")
            print("Please select 1-6.")


def show_admin_dashboard():
    """
    Displays the administrator dashboard.
    """

    if not is_admin_logged_in():

        print("\nAuthentication required.")
        print("Please login before accessing this feature.")
        return

    current_admin = get_current_admin_session()

    if current_admin is None:

        print("\nAuthentication required.")
        print("Please login before accessing this feature.")
        return

    admin_id = current_admin["admin_id"]
    username = current_admin["username"]

    while True:

        print("\n" + "=" * 60)
        print("                     SECURE BANK")
        print("                  ADMIN DASHBOARD")
        print("=" * 60)

        print(f"\nWelcome, {username}")

        print("\n" + "-" * 60)

        print("1. View All Branches")
        print("2. View Branch Details")
        print("3. View All Messages")
        print("4. View System Activity")
        print("5. View Login Security")
        print("6. Logout")

        print("-" * 60)

        choice = input(
            "Enter your choice (1-6): "
        ).strip()

        if choice == "1":

            show_all_branches()

        elif choice == "2":

            show_branch_details()

        elif choice == "3":

            show_all_messages()

        elif choice == "4":

            show_system_activity()

        elif choice == "5":

            show_login_security()

        elif choice == "6":

            current_time = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            print("\nLogging out administrator...")

            log_admin_activity(
                admin_id,
                "ADMIN_LOGOUT",
                "Administrator logged out",
                current_time
            )

            print("Admin logout activity recorded.")

            destroy_admin_session()

            print("Admin session destroyed.")
            print("Administrator securely logged out.")

            return

        else:

            print("\nInvalid choice.")
            print("Please select 1-6.")



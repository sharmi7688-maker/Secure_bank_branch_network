from modules.admin_session import (
    create_admin_session,
    get_current_admin_session,
    is_admin_logged_in,
    require_admin_login,
    destroy_admin_session
)


def main():

    print("\n" + "=" * 60)
    print("       ADMIN SESSION SECURITY TEST")
    print("=" * 60)

    admin = {
        "admin_id": 1,
        "username": "admin"
    }

    # ---------------------------------------------------------
    # TEST 1: No session initially
    # ---------------------------------------------------------

    print("\nTesting access before admin login...")

    if not require_admin_login():

        print("ACCESS DENIED")
        print("Unauthenticated admin access was correctly rejected.")

    else:

        print("SECURITY ERROR")
        print("Unauthenticated access was allowed.")

    # ---------------------------------------------------------
    # TEST 2: Create admin session
    # ---------------------------------------------------------

    print("\nCreating administrator session...")

    create_admin_session(admin)

    session = get_current_admin_session()

    print("\nCurrent Admin Session:")
    print(session)

    # ---------------------------------------------------------
    # TEST 3: Verify session
    # ---------------------------------------------------------

    print("\nTesting authenticated admin access...")

    if require_admin_login():

        print("ACCESS GRANTED")
        print("Authenticated admin session detected.")

    else:

        print("SECURITY ERROR")
        print("Authenticated admin was rejected.")

    # ---------------------------------------------------------
    # TEST 4: Check session status
    # ---------------------------------------------------------

    print("\nChecking admin login status...")

    if is_admin_logged_in():

        print("Admin session is active.")

    else:

        print("SECURITY ERROR")
        print("Admin session was not detected.")

    # ---------------------------------------------------------
    # TEST 5: Destroy session
    # ---------------------------------------------------------

    print("\nDestroying administrator session...")

    destroy_admin_session()

    print("\nCurrent Admin Session:")
    print(get_current_admin_session())

    # ---------------------------------------------------------
    # TEST 6: Access after logout
    # ---------------------------------------------------------

    print("\nTesting access after admin logout...")

    if not require_admin_login():

        print("ACCESS DENIED")
        print("Logged-out admin session was correctly rejected.")

    else:

        print("SECURITY ERROR")
        print("Admin access remained active after logout.")

    # ---------------------------------------------------------
    # COMPLETE
    # ---------------------------------------------------------

    print("\n" + "=" * 60)
    print("             TEST COMPLETED")
    print("=" * 60)


if __name__ == "__main__":

    main()
from modules.session import (
    create_session,
    get_current_session,
    is_logged_in,
    require_login,
    destroy_session
)


test_branch = {
    "branch_id": 1,
    "branch_code": "SB001",
    "branch_name": "Bangalore"
}


print("\n" + "=" * 60)
print("          COMPLETE SESSION SECURITY TEST")
print("=" * 60)


# ----------------------------------------------------------
# TEST 1 — No session
# ----------------------------------------------------------

print("\nTEST 1: Initial Session")

destroy_session()

print("Logged in:", is_logged_in())
print("Current session:", get_current_session())


# ----------------------------------------------------------
# TEST 2 — Access without login
# ----------------------------------------------------------

print("\nTEST 2: Access Without Login")

access = require_login()

print("Access allowed:", access)


# ----------------------------------------------------------
# TEST 3 — Create session
# ----------------------------------------------------------

print("\nTEST 3: Create Session")

create_session(test_branch)

print("Logged in:", is_logged_in())
print("Current session:", get_current_session())


# ----------------------------------------------------------
# TEST 4 — Access with session
# ----------------------------------------------------------

print("\nTEST 4: Access With Login")

access = require_login()

print("Access allowed:", access)


# ----------------------------------------------------------
# TEST 5 — Verify branch identity
# ----------------------------------------------------------

print("\nTEST 5: Verify Branch Identity")

session = get_current_session()

print("Branch ID   :", session["branch_id"])
print("Branch Code :", session["branch_code"])
print("Branch Name :", session["branch_name"])
print("Login Time  :", session["login_time"])


# ----------------------------------------------------------
# TEST 6 — Destroy session
# ----------------------------------------------------------

print("\nTEST 6: Destroy Session")

destroy_session()

print("Logged in:", is_logged_in())
print("Current session:", get_current_session())


# ----------------------------------------------------------
# TEST 7 — Access after logout
# ----------------------------------------------------------

print("\nTEST 7: Access After Logout")

access = require_login()

print("Access allowed:", access)


print("\n" + "=" * 60)
print("          SESSION TEST COMPLETED")
print("=" * 60)
from modules.session import (
    create_session,
    get_current_session,
    is_logged_in,
    destroy_session
)


test_branch = {
    "branch_id": 1,
    "branch_code": "SB001",
    "branch_name": "Bangalore"
}


print("\n" + "=" * 60)
print("              SESSION SECURITY TEST")
print("=" * 60)


print("\n1. Initial session status:")

print(
    "Logged in:",
    is_logged_in()
)


print("\n2. Creating session...")

create_session(test_branch)

print("Session created.")


print("\n3. Checking session:")

print(
    "Logged in:",
    is_logged_in()
)


print("\n4. Current session:")

session = get_current_session()

print(session)


print("\n5. Destroying session...")

destroy_session()

print("Session destroyed.")


print("\n6. Final session status:")

print(
    "Logged in:",
    is_logged_in()
)

print(
    "Current session:",
    get_current_session()
)


print("=" * 60)
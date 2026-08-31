from modules.session import (
    create_session,
    destroy_session,
    require_login
)


test_branch = {
    "branch_id": 1,
    "branch_code": "SB001",
    "branch_name": "Bangalore"
}


print("\n" + "=" * 60)
print("             SESSION PROTECTION TEST")
print("=" * 60)


print("\nTest 1: No active session")

destroy_session()

result = require_login()

print("Access allowed:", result)


print("\nTest 2: Active session")

create_session(test_branch)

result = require_login()

print("Access allowed:", result)


print("\nTest 3: Destroy session")

destroy_session()

result = require_login()

print("Access allowed:", result)


print("=" * 60)
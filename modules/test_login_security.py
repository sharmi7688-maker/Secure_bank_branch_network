from modules.login_security import (
    initialize_login_security,
    check_login_lock,
    record_failed_attempt,
    reset_login_attempts
)


TEST_BRANCH_ID = 1


print("\n" + "=" * 60)
print("           LOGIN SECURITY TEST")
print("=" * 60)


print("\n1. Initializing security record...")

initialize_login_security(TEST_BRANCH_ID)

print("Security record initialized.")


print("\n2. Checking initial lock status...")

locked = check_login_lock(TEST_BRANCH_ID)

print("Locked:", locked)


print("\n3. Recording failed attempts...")

for attempt in range(1, 4):

    count = record_failed_attempt(
        TEST_BRANCH_ID
    )

    print(
        f"Failed attempt {attempt}: "
        f"Total = {count}"
    )


print("\n4. Checking lock status...")

locked = check_login_lock(TEST_BRANCH_ID)

print("Locked:", locked)


print("\n5. Resetting login attempts...")

reset_login_attempts(TEST_BRANCH_ID)

print("Login attempts reset.")


print("\n6. Checking lock status after reset...")

locked = check_login_lock(TEST_BRANCH_ID)

print("Locked:", locked)


print("\n" + "=" * 60)
print("           TEST COMPLETED")
print("=" * 60)
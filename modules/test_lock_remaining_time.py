from modules.login_security import (
    initialize_login_security,
    record_failed_attempt,
    get_lock_remaining_time,
    reset_login_attempts
)


TEST_BRANCH_ID = 1


print("\n" + "=" * 60)
print("       LOCK REMAINING TIME TEST")
print("=" * 60)


reset_login_attempts(TEST_BRANCH_ID)

initialize_login_security(TEST_BRANCH_ID)

print("\nCreating failed login attempts...")

for attempt in range(3):

    count = record_failed_attempt(
        TEST_BRANCH_ID
    )

    print(
        f"Attempt {attempt + 1}: "
        f"{count}/3"
    )


remaining_seconds = get_lock_remaining_time(
    TEST_BRANCH_ID
)


print("\nRemaining lock time:")

print(
    f"{remaining_seconds} seconds"
)


remaining_minutes = remaining_seconds // 60

remaining_seconds_display = (
    remaining_seconds % 60
)


print(
    f"Approximately "
    f"{remaining_minutes} minute(s) "
    f"and "
    f"{remaining_seconds_display} second(s)"
)


reset_login_attempts(TEST_BRANCH_ID)


print("\nSecurity record reset.")

print("=" * 60)
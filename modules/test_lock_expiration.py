import sqlite3
from datetime import datetime, timedelta

from modules.login_security import (
    initialize_login_security,
    record_failed_attempt,
    check_login_lock,
    reset_login_attempts
)


TEST_BRANCH_ID = 1

DATABASE_PATH = "database/bank.db"


print("\n" + "=" * 60)
print("          LOCK EXPIRATION TEST")
print("=" * 60)


# --------------------------------------------------
# Step 1: Reset test branch
# --------------------------------------------------

print("\n1. Resetting security record...")

initialize_login_security(TEST_BRANCH_ID)
reset_login_attempts(TEST_BRANCH_ID)

print("Security record reset.")


# --------------------------------------------------
# Step 2: Create 3 failed attempts
# --------------------------------------------------

print("\n2. Recording 3 failed attempts...")

for attempt in range(1, 4):

    count = record_failed_attempt(
        TEST_BRANCH_ID
    )

    print(
        f"Attempt {attempt}: "
        f"Failed attempts = {count}"
    )


# --------------------------------------------------
# Step 3: Check lock
# --------------------------------------------------

print("\n3. Checking lock status...")

locked = check_login_lock(
    TEST_BRANCH_ID
)

print("Locked:", locked)


# --------------------------------------------------
# Step 4: Simulate expired lock
# --------------------------------------------------

print("\n4. Simulating expired lock...")

expired_time = (
    datetime.now() - timedelta(minutes=1)
).strftime("%Y-%m-%d %H:%M:%S")


connection = sqlite3.connect(
    DATABASE_PATH
)

cursor = connection.cursor()

cursor.execute("""
    UPDATE login_security
    SET locked_until = ?
    WHERE branch_id = ?
""", (
    expired_time,
    TEST_BRANCH_ID
))

connection.commit()
connection.close()

print("Lock expiration simulated.")


# --------------------------------------------------
# Step 5: Check lock after expiration
# --------------------------------------------------

print("\n5. Checking lock after expiration...")

locked = check_login_lock(
    TEST_BRANCH_ID
)

print("Locked:", locked)


# --------------------------------------------------
# Step 6: Record another failed attempt
# --------------------------------------------------

print("\n6. Recording another failed attempt...")

count = record_failed_attempt(
    TEST_BRANCH_ID
)

print(
    "Failed attempts after expired lock:",
    count
)


# --------------------------------------------------
# Step 7: Reset test data
# --------------------------------------------------

print("\n7. Cleaning up test data...")

reset_login_attempts(
    TEST_BRANCH_ID
)

print("Test security record reset.")


print("\n" + "=" * 60)
print("          TEST COMPLETED")
print("=" * 60)
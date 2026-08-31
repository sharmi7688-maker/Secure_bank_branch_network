from modules.session import (
    create_session,
    get_current_session,
    require_branch_session,
    destroy_session
)


print("\n" + "=" * 60)
print("       BRANCH SESSION SECURITY TEST")
print("=" * 60)


branch_one = {
    "branch_id": 1,
    "branch_code": "SB001",
    "branch_name": "Bangalore"
}


print("\nCreating session for:")
print("Branch:", branch_one["branch_name"])
print("Code  :", branch_one["branch_code"])

create_session(branch_one)


print("\nCurrent Session:")
print(get_current_session())


print("\nTesting correct branch...")

if require_branch_session(1):

    print("ACCESS GRANTED")
    print("Correct branch session detected.")

else:

    print("TEST FAILED")


print("\nTesting different branch...")

if require_branch_session(2):

    print("TEST FAILED")
    print("Different branch was incorrectly allowed.")

else:

    print("ACCESS DENIED")
    print("Different branch was correctly rejected.")


print("\nDestroying session...")

destroy_session()


print("Current Session:")
print(get_current_session())


print("\nTesting access after logout...")

if require_branch_session(1):

    print("TEST FAILED")
    print("Access was allowed after logout.")

else:

    print("ACCESS DENIED")
    print("Unauthenticated access was correctly rejected.")


print("\n" + "=" * 60)
print("             TEST COMPLETED")
print("=" * 60)
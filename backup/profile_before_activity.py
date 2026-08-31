from database.database import get_branch_profile


def show_profile(branch):

    branch_id = branch["branch_id"]
    branch_code = branch["branch_code"]

    profile = get_branch_profile(branch_id)

    if profile is None:

        print("\nUnable to retrieve branch profile.")
        return

    (
        profile_branch_id,
        branch_name,
        created_date
    ) = profile

    print("\n" + "=" * 60)
    print("                     SECURE BANK")
    print("                   BRANCH PROFILE")
    print("=" * 60)

    print(f"\nBranch ID       : {profile_branch_id}")
    print(f"Branch Code     : {branch_code}")
    print(f"Branch Name     : {branch_name}")
    print(f"Registered Date : {created_date}")

    print("\nAccount Status  : ACTIVE")
    print("Security Status : PROTECTED")

    print("\n" + "=" * 60)

    input("\nPress Enter to return to dashboard...")

if __name__ == "__main__":

    test_branch = {
        "branch_id": 1,
        "branch_code": "SB001",
        "branch_name": "Bangalore"
    }

    show_profile(test_branch)

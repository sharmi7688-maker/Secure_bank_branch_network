from database.database import get_all_branches


def verify_branches():
    """
    Displays registered branches without exposing password data.
    """

    branches = get_all_branches()

    print("\n" + "=" * 70)
    print("             REGISTERED SECURE BANK BRANCHES")
    print("=" * 70)

    if not branches:
        print("No branches are registered.")
        return

    print(f"{'ID':<8}{'Branch Name':<20}{'Created Date':<25}")
    print("-" * 70)

    for branch in branches:
        branch_id, branch_name, created_date = branch

        print(f"{branch_id:<8}{branch_name:<20}{created_date:<25}")

    print("-" * 70)
    print(f"Total Branches: {len(branches)}")
    print("=" * 70)


if __name__ == "__main__":
    verify_branches()
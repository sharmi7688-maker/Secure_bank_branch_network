from database.database import get_all_branches


def test_branch_list():

    branches = get_all_branches()

    print("\n" + "=" * 60)
    print("              REGISTERED BANK BRANCHES")
    print("=" * 60)

    for branch_id, branch_name in branches:

        branch_code = f"SB{branch_id:03d}"

        print(
            f"ID: {branch_id} | "
            f"Code: {branch_code} | "
            f"Name: {branch_name}"
        )

    print("=" * 60)


if __name__ == "__main__":
    test_branch_list()
from database.database import get_activities_for_branch


if __name__ == "__main__":

    branch_id = 1

    activities = get_activities_for_branch(
        branch_id
    )

    print("\nActivities for Branch:", branch_id)
    print("-" * 70)

    for activity in activities:

        (
            log_id,
            branch_id,
            activity_type,
            description,
            activity_date
        ) = activity

        print(
            f"{log_id} | "
            f"{activity_type} | "
            f"{description} | "
            f"{activity_date}"
        )

    print("-" * 70)
from datetime import datetime

from database.database import log_activity


if __name__ == "__main__":

    branch_id = 1

    current_time = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    log_id = log_activity(
        branch_id,
        "TEST",
        "Activity logging test",
        current_time
    )

    print("\nActivity saved successfully.")
    print("Log ID :", log_id)
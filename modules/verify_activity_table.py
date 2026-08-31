import sqlite3


def verify_activity_table():

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        AND name = 'activity_logs'
    """)

    result = cursor.fetchone()

    if result:

        print("\nActivity logs table verified successfully.")

        cursor.execute(
            "PRAGMA table_info(activity_logs)"
        )

        columns = cursor.fetchall()

        print("\nActivity Logs Table Structure:")
        print("-" * 60)

        for column in columns:

            print(
                f"Column: {column[1]} | "
                f"Type: {column[2]}"
            )

        print("-" * 60)

    else:

        print(
            "\nActivity logs table was not found."
        )

    connection.close()


if __name__ == "__main__":

    verify_activity_table()
import sqlite3


def verify_messages_table():
    """
    Verifies the structure of the messages table.
    """

    connection = sqlite3.connect("database/bank.db")
    cursor = connection.cursor()

    cursor.execute("PRAGMA table_info(messages)")

    columns = cursor.fetchall()

    connection.close()

    print("\n" + "=" * 70)
    print("                 MESSAGES TABLE STRUCTURE")
    print("=" * 70)

    if not columns:
        print("Messages table does not exist.")
        return

    for column in columns:
        column_id, column_name, column_type, not_null, default_value, primary_key = column

        print(
            f"Column: {column_name} | "
            f"Type: {column_type} | "
            f"Primary Key: {primary_key}"
        )

    print("=" * 70)


if __name__ == "__main__":
    verify_messages_table()
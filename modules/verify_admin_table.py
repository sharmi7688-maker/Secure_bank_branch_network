import sqlite3


DATABASE_PATH = "database/bank.db"


def verify_admin_table():

    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        AND name = 'admins'
    """)

    result = cursor.fetchone()

    if result is None:

        print("\nAdmin table was not found.")

        connection.close()
        return

    print("\n" + "=" * 60)
    print("                 ADMIN TABLE STRUCTURE")
    print("=" * 60)

    cursor.execute("PRAGMA table_info(admins)")

    columns = cursor.fetchall()

    for column in columns:

        column_id = column[0]
        column_name = column[1]
        column_type = column[2]
        primary_key = column[5]

        print(
            f"Column: {column_name} | "
            f"Type: {column_type} | "
            f"Primary Key: {primary_key}"
        )

    print("=" * 60)

    connection.close()


if __name__ == "__main__":

    verify_admin_table()
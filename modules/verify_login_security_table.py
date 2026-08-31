import sqlite3


def verify_login_security_table():

    connection = sqlite3.connect(
        "database/bank.db"
    )

    cursor = connection.cursor()

    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        AND name = 'login_security'
    """)

    result = cursor.fetchone()

    if result:

        print(
            "\nLogin security table "
            "verified successfully."
        )

        cursor.execute(
            "PRAGMA table_info(login_security)"
        )

        columns = cursor.fetchall()

        print(
            "\nLogin Security Table Structure:"
        )

        print("-" * 60)

        for column in columns:

            print(
                f"Column: {column[1]} | "
                f"Type: {column[2]}"
            )

        print("-" * 60)

    else:

        print(
            "\nLogin security table was not found."
        )

    connection.close()


if __name__ == "__main__":

    verify_login_security_table()
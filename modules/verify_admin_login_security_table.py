import sqlite3


DATABASE_PATH = "database/bank.db"


connection = sqlite3.connect(DATABASE_PATH)
cursor = connection.cursor()


cursor.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
    AND name = 'admin_login_security'
""")

result = cursor.fetchone()


if result:

    print("\nAdmin Login Security table verified successfully.")

    cursor.execute(
        "PRAGMA table_info(admin_login_security)"
    )

    columns = cursor.fetchall()

    print("\nAdmin Login Security Table Structure:")
    print("-" * 60)

    for column in columns:

        print(
            f"Column: {column[1]} | "
            f"Type: {column[2]}"
        )

    print("-" * 60)

else:

    print(
        "\nAdmin Login Security table was not found."
    )


connection.close()
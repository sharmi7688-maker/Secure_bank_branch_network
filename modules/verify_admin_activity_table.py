import sqlite3


DATABASE_PATH = "database/bank.db"


connection = sqlite3.connect(DATABASE_PATH)
cursor = connection.cursor()

cursor.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
    AND name = 'admin_activity_logs'
""")

result = cursor.fetchone()

if result:

    print("\nAdmin Activity Logs table verified successfully.")

    cursor.execute("""
        PRAGMA table_info(admin_activity_logs)
    """)

    columns = cursor.fetchall()

    print("\nAdmin Activity Logs Table Structure:")
    print("-" * 60)

    for column in columns:
        print(
            f"Column: {column[1]} | "
            f"Type: {column[2]}"
        )

    print("-" * 60)

else:

    print("\nAdmin Activity Logs table was not found.")


connection.close()
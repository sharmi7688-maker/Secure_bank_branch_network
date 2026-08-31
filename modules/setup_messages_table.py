from database.database import (
    create_messages_table,
    get_messages_table_structure
)


def setup_messages():
    create_messages_table()

    print("\nMessages table created successfully.")

    columns = get_messages_table_structure()

    print("\n" + "=" * 60)
    print("             MESSAGES TABLE STRUCTURE")
    print("=" * 60)

    for column in columns:
        column_id, column_name, column_type, not_null, default_value, primary_key = column

        print(
            f"Column: {column_name} | "
            f"Type: {column_type}"
        )

    print("=" * 60)


if __name__ == "__main__":
    setup_messages()
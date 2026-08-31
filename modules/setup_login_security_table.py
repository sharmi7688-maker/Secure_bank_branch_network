from database.database import create_login_security_table


if __name__ == "__main__":

    create_login_security_table()

    print(
        "Login security table created successfully."
    )
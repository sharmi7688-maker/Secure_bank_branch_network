from modules.register import validate_password


test_passwords = [
    "password",
    "Password1",
    "Password@1",
    "Password@123",
    "Welcome@123",
    "Admin@123",
    "Secure@123",
    "SecureBank@2026"
]


print("\nPassword Security Test")
print("=" * 60)

for password in test_passwords:

    result = validate_password(password)

    status = "VALID" if result else "INVALID"

    print(
        f"{password:<20} : {status}"
    )

print("=" * 60)
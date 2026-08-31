from modules.session import (
    get_current_session,
    is_logged_in
)


print("\n" + "=" * 60)
print("              ACTIVE SESSION")
print("=" * 60)

print("\nLogged in:")
print(is_logged_in())

print("\nCurrent Session:")
print(get_current_session())

print("=" * 60)
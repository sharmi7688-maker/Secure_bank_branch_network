"""
Manages the currently logged-in administrator session.
"""

_current_admin_session = None


def create_admin_session(admin):
    """
    Creates an administrator session.

    Parameters:
        admin: Dictionary containing admin_id and username.
    """

    global _current_admin_session

    _current_admin_session = {
        "admin_id": admin["admin_id"],
        "username": admin["username"]
    }


def get_current_admin_session():
    """
    Returns the currently logged-in administrator.

    Returns:
        Admin session dictionary if logged in.
        None if no admin is logged in.
    """

    return _current_admin_session


def is_admin_logged_in():
    """
    Checks whether an administrator is currently logged in.

    Returns:
        True  -> Admin is logged in
        False -> No admin session
    """

    return _current_admin_session is not None


def require_admin_login():
    """
    Checks whether an authenticated administrator session exists.

    Returns:
        True  -> Active admin session exists.
        False -> No active admin session.
    """

    if _current_admin_session is None:

        print("\nAuthentication required.")
        print("Please login as administrator before accessing this feature.")

        return False

    return True


def destroy_admin_session():
    """
    Destroys the current administrator session.
    """

    global _current_admin_session

    _current_admin_session = None
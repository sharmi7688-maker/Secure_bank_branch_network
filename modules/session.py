from datetime import datetime


_current_session = None


def create_session(branch):
    """
    Creates a session for the logged-in branch.
    """

    global _current_session

    _current_session = {
        "branch_id": branch["branch_id"],
        "branch_code": branch["branch_code"],
        "branch_name": branch["branch_name"],
        "login_time": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    }


def get_current_session():
    """
    Returns the current logged-in session.

    Returns:
        Session dictionary if logged in.
        None if no branch is logged in.
    """

    return _current_session


def is_logged_in():
    """
    Checks whether a branch is currently logged in.

    Returns:
        True  -> Branch is logged in.
        False -> No branch is logged in.
    """

    return _current_session is not None


def destroy_session():
    """
    Destroys the current session.
    """

    global _current_session

    _current_session = None

def require_login():
    """
    Checks whether an authenticated session exists.

    Returns:
        True  -> Active session exists.
        False -> No active session.
    """

    if _current_session is None:

        print("\nAuthentication required.")
        print("Please login before accessing this feature.")

        return False

    return True    

def require_branch_session(branch_id):
    """
    Verifies that an authenticated session exists
    and belongs to the requested branch.

    Returns:
        True  -> Session belongs to the branch.
        False -> Authentication failed.
    """

    if _current_session is None:

        print("\nAuthentication required.")
        print("Please login before accessing this feature.")

        return False

    if _current_session["branch_id"] != branch_id:

        print("\nAccess denied.")
        print("The active session does not belong to this branch.")

        return False

    return True


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
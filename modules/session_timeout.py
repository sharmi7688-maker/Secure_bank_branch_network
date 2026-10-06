"""
INACTIVITY TIMEOUT
==================

Pure helper functions (no Streamlit import) so the policy is easy to test.
The Streamlit app calls them on every interaction: if the account has been
idle for longer than SESSION_TIMEOUT_MINUTES the session is destroyed.
"""

from datetime import datetime, timedelta

SESSION_TIMEOUT_MINUTES = 10


def _now(now):
    return now if now is not None else datetime.now()


def idle_seconds(last_activity, now=None):
    return int((_now(now) - last_activity).total_seconds())


def is_expired(last_activity, now=None,
               timeout_minutes=SESSION_TIMEOUT_MINUTES):
    return _now(now) - last_activity > timedelta(minutes=timeout_minutes)


def seconds_remaining(last_activity, now=None,
                      timeout_minutes=SESSION_TIMEOUT_MINUTES):
    left = timeout_minutes * 60 - idle_seconds(last_activity, now)
    return max(left, 0)

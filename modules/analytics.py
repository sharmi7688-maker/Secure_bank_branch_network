"""
ADMIN ANALYTICS
===============

Read-only aggregate queries for the dashboard charts. Nothing here touches
message content - only counts and metadata.
"""

from datetime import datetime, timedelta

from database import store
from database.connection import connect

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
FAILURE_TYPES = ("FAILED_LOGIN", "FAILED_2FA")


def _now(now):
    return now if now is not None else datetime.now()


def _days(count, now):
    today = _now(now).date()
    return [(today - timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(count - 1, -1, -1)]


def _daily(connection, sql, params, days):
    counts = dict(connection.execute(sql, params).fetchall())
    return [(day, counts.get(day, 0)) for day in days]


def overview(now=None):
    """Headline numbers for the dashboard."""

    moment = _now(now)
    now_text = moment.strftime(DATETIME_FORMAT)
    since_24h = (moment - timedelta(hours=24)).strftime(DATETIME_FORMAT)

    connection = connect()
    try:
        scalar = lambda sql, params=(): connection.execute(
            sql, params).fetchone()[0]

        marks = ",".join("?" * len(FAILURE_TYPES))
        data = {
            "branches": scalar("SELECT COUNT(*) FROM branches"),
            "messages": scalar("SELECT COUNT(*) FROM messages"),
            "unread": scalar(
                "SELECT COUNT(*) FROM messages WHERE is_read = 0"),
            "urgent": scalar(
                "SELECT COUNT(*) FROM messages WHERE priority = 'URGENT'"),
            "locked_now": scalar(
                "SELECT COUNT(*) FROM login_security "
                "WHERE locked_until IS NOT NULL AND locked_until > ?",
                (now_text,)),
            "failed_logins_24h": scalar(
                f"SELECT COUNT(*) FROM activity_logs "
                f"WHERE activity_type IN ({marks}) AND activity_date >= ?",
                FAILURE_TYPES + (since_24h,)),
        }
    finally:
        connection.close()

    data["branches_with_2fa"] = store.count_two_factor_enabled("branch")
    return data


def messages_per_branch():
    """[{'Branch': 'SB001', 'Sent': n, 'Received': n}, ...]"""

    connection = connect()
    try:
        rows = connection.execute("""
            SELECT b.branch_id,
                   (SELECT COUNT(*) FROM messages
                    WHERE sender_branch_id = b.branch_id),
                   (SELECT COUNT(*) FROM messages
                    WHERE receiver_branch_id = b.branch_id)
            FROM branches b ORDER BY b.branch_id
        """).fetchall()
    finally:
        connection.close()

    return [
        {"Branch": f"SB{bid:03d}", "Sent": sent, "Received": received}
        for (bid, sent, received) in rows
    ]


def messages_per_day(days=14, now=None):
    connection = connect()
    try:
        return _daily(
            connection,
            "SELECT substr(sent_date, 1, 10), COUNT(*) FROM messages "
            "GROUP BY 1", (), _days(days, now))
    finally:
        connection.close()


def failed_logins_per_day(days=14, now=None):
    marks = ",".join("?" * len(FAILURE_TYPES))
    connection = connect()
    try:
        return _daily(
            connection,
            f"SELECT substr(activity_date, 1, 10), COUNT(*) "
            f"FROM activity_logs WHERE activity_type IN ({marks}) GROUP BY 1",
            FAILURE_TYPES, _days(days, now))
    finally:
        connection.close()


def lockouts_per_day(days=14, now=None):
    connection = connect()
    try:
        return _daily(
            connection,
            "SELECT substr(activity_date, 1, 10), COUNT(*) "
            "FROM activity_logs WHERE activity_type = 'ACCOUNT_LOCKED' "
            "GROUP BY 1", (), _days(days, now))
    finally:
        connection.close()


def priority_breakdown():
    connection = connect()
    try:
        rows = connection.execute(
            "SELECT priority, COUNT(*) FROM messages GROUP BY priority"
        ).fetchall()
    finally:
        connection.close()

    counts = dict(rows)
    return [{"Priority": p, "Messages": counts.get(p, 0)}
            for p in ("NORMAL", "URGENT", "CONFIDENTIAL")]

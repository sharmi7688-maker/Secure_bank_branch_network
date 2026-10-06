"""
CSV AUDIT REPORTS
=================

Builds the CSV text for the administrator "Reports" section. Message
reports contain METADATA ONLY (never content).

Spreadsheet-safe: a cell that starts with = + - @ is prefixed with an
apostrophe so Excel cannot execute it as a formula (CSV injection).
"""

import csv
import io

from database.database import (
    get_all_activities_admin,
    get_all_login_security_admin,
)
from database.connection import connect

DANGEROUS_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def sanitize_cell(value):
    text = "" if value is None else str(value)
    if text.startswith(DANGEROUS_PREFIXES):
        return "'" + text
    return text


def to_csv(headers, rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow([sanitize_cell(h) for h in headers])
    for row in rows:
        writer.writerow([sanitize_cell(cell) for cell in row])
    return buffer.getvalue()


def activity_report(date_from=None, date_to=None):
    """System activity (branches + administrators), optional date range
    as 'YYYY-MM-DD' strings or date objects (inclusive)."""

    date_from = str(date_from) if date_from else None
    date_to = str(date_to) if date_to else None

    rows = []
    for (actor_type, actor, activity, description,
         when) in get_all_activities_admin():
        day = when[:10]
        if date_from and day < date_from:
            continue
        if date_to and day > date_to:
            continue
        rows.append((when, actor_type, actor, activity, description))

    rows.sort(key=lambda r: r[0])
    return to_csv(
        ["Date & Time", "Type", "Actor", "Activity", "Description"], rows
    )


def messages_report():
    connection = connect()
    try:
        data = connection.execute(
            """
            SELECT message_id, sender_branch_id, receiver_branch_id,
                   sent_date, is_read, priority, key_id
            FROM messages ORDER BY message_id
            """
        ).fetchall()
    finally:
        connection.close()

    rows = [
        (mid, f"SB{s:03d}", f"SB{r:03d}", sent,
         "READ" if read else "UNREAD", priority, f"v{key_id}")
        for (mid, s, r, sent, read, priority, key_id) in data
    ]
    return to_csv(
        ["Message ID", "From", "To", "Sent", "Status", "Priority",
         "Key version"], rows
    )


def login_security_report():
    rows = [
        (f"SB{bid:03d}", failed, locked or "-")
        for (bid, failed, locked) in get_all_login_security_admin()
    ]
    return to_csv(["Branch", "Failed attempts", "Locked until"], rows)


def alerts_report(alerts):
    rows = [(a.severity, a.rule, a.title, a.detail, a.count) for a in alerts]
    return to_csv(["Severity", "Rule", "Title", "Detail", "Count"], rows)

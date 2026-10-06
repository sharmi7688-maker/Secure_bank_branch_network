"""
SUSPICIOUS-ACTIVITY ALERTS
==========================

Rule-based detection over the audit logs. Thresholds are constants at the
top so they are easy to explain, tune and test.

    Rule                      Looks at                      Severity
    ------------------------  ----------------------------  ----------------
    REPEATED_LOCKOUTS         ACCOUNT_LOCKED, 24 h          MEDIUM / HIGH
    FAILED_LOGIN_SPIKE        failed logins, 15 min         MEDIUM / HIGH
    ADMIN_AUTH_FAILURES       admin failures, 60 min        HIGH
    MESSAGE_FLOOD             MESSAGE_SENT per branch,10min MEDIUM
    AUDIT_INTEGRITY           hash-chain verification       HIGH
    OFF_HOURS_ADMIN_LOGIN     admin login 00:00-04:59, 24 h LOW
    ADMIN_WITHOUT_2FA         admins without 2FA            LOW
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from database import store
from database.connection import connect
from modules.audit_chain import verify_all

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

LOCKOUTS_MEDIUM = 2
LOCKOUTS_HIGH = 4
LOCKOUT_WINDOW_HOURS = 24

SPIKE_MEDIUM = 5
SPIKE_HIGH = 10
SPIKE_WINDOW_MINUTES = 15

ADMIN_FAILURES_HIGH = 3
ADMIN_FAILURE_WINDOW_MINUTES = 60

FLOOD_THRESHOLD = 15
FLOOD_WINDOW_MINUTES = 10

OFF_HOURS = ("00", "01", "02", "03", "04")

SEVERITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


@dataclass
class Alert:
    rule: str
    severity: str
    title: str
    detail: str
    count: int = 0


def _since(now, **delta):
    return (now - timedelta(**delta)).strftime(DATETIME_FORMAT)


def evaluate_alerts(now=None, check_integrity=True):
    """Runs every rule. Returns alerts sorted HIGH -> LOW."""

    now = now if now is not None else datetime.now()
    alerts = []

    connection = connect()
    try:
        # 1. Repeated lockouts per branch
        rows = connection.execute(
            """
            SELECT branch_id, COUNT(*) FROM activity_logs
            WHERE activity_type = 'ACCOUNT_LOCKED' AND activity_date >= ?
            GROUP BY branch_id HAVING COUNT(*) >= ?
            """,
            (_since(now, hours=LOCKOUT_WINDOW_HOURS), LOCKOUTS_MEDIUM),
        ).fetchall()
        for branch_id, count in rows:
            alerts.append(Alert(
                "REPEATED_LOCKOUTS",
                "HIGH" if count >= LOCKOUTS_HIGH else "MEDIUM",
                f"Repeated lockouts: SB{branch_id:03d}",
                f"Branch SB{branch_id:03d} was locked {count} times in the "
                f"last {LOCKOUT_WINDOW_HOURS} hours. Possible password "
                "guessing.",
                count,
            ))

        # 2. Failed-login spike across the whole network
        count, branches = connection.execute(
            """
            SELECT COUNT(*), COUNT(DISTINCT branch_id) FROM activity_logs
            WHERE activity_type IN ('FAILED_LOGIN', 'FAILED_2FA')
              AND activity_date >= ?
            """,
            (_since(now, minutes=SPIKE_WINDOW_MINUTES),),
        ).fetchone()
        if count >= SPIKE_MEDIUM:
            alerts.append(Alert(
                "FAILED_LOGIN_SPIKE",
                "HIGH" if count >= SPIKE_HIGH else "MEDIUM",
                "Spike in failed logins",
                f"{count} failed sign-in attempts across {branches} "
                f"branch(es) in the last {SPIKE_WINDOW_MINUTES} minutes.",
                count,
            ))

        # 3. Administrator authentication failures
        rows = connection.execute(
            """
            SELECT a.username, COUNT(*) FROM admin_activity_logs l
            JOIN admins a ON a.admin_id = l.admin_id
            WHERE l.activity_type IN ('ADMIN_FAILED_LOGIN', 'ADMIN_FAILED_2FA')
              AND l.activity_date >= ?
            GROUP BY a.username HAVING COUNT(*) >= ?
            """,
            (_since(now, minutes=ADMIN_FAILURE_WINDOW_MINUTES),
             ADMIN_FAILURES_HIGH),
        ).fetchall()
        for username, count in rows:
            alerts.append(Alert(
                "ADMIN_AUTH_FAILURES", "HIGH",
                f"Administrator sign-in failures: {username}",
                f"{count} failed attempts on administrator '{username}' in "
                f"the last {ADMIN_FAILURE_WINDOW_MINUTES} minutes.",
                count,
            ))

        # 4. Message flood
        rows = connection.execute(
            """
            SELECT branch_id, COUNT(*) FROM activity_logs
            WHERE activity_type = 'MESSAGE_SENT' AND activity_date >= ?
            GROUP BY branch_id HAVING COUNT(*) >= ?
            """,
            (_since(now, minutes=FLOOD_WINDOW_MINUTES), FLOOD_THRESHOLD),
        ).fetchall()
        for branch_id, count in rows:
            alerts.append(Alert(
                "MESSAGE_FLOOD", "MEDIUM",
                f"Unusual message volume: SB{branch_id:03d}",
                f"Branch SB{branch_id:03d} sent {count} messages in "
                f"{FLOOD_WINDOW_MINUTES} minutes.",
                count,
            ))

        # 6. Off-hours administrator logins
        rows = connection.execute(
            """
            SELECT a.username, l.activity_date FROM admin_activity_logs l
            JOIN admins a ON a.admin_id = l.admin_id
            WHERE l.activity_type = 'ADMIN_LOGIN' AND l.activity_date >= ?
            ORDER BY l.activity_date DESC
            """,
            (_since(now, hours=24),),
        ).fetchall()
        for username, when in rows:
            if when[11:13] in OFF_HOURS:
                alerts.append(Alert(
                    "OFF_HOURS_ADMIN_LOGIN", "LOW",
                    f"Off-hours administrator login: {username}",
                    f"'{username}' signed in at {when} (outside normal "
                    "working hours).",
                    1,
                ))

        # 7. Administrators without 2FA
        total_admins = connection.execute(
            "SELECT COUNT(*) FROM admins").fetchone()[0]
    finally:
        connection.close()

    without_2fa = total_admins - store.count_two_factor_enabled("admin")
    if without_2fa > 0:
        alerts.append(Alert(
            "ADMIN_WITHOUT_2FA", "LOW",
            "Administrators without two-factor authentication",
            f"{without_2fa} administrator account(s) are not protected by "
            "2FA.",
            without_2fa,
        ))

    # 5. Audit-log integrity
    if check_integrity:
        for result in verify_all():
            if not result["ok"]:
                alerts.append(Alert(
                    "AUDIT_INTEGRITY", "HIGH",
                    f"Audit log tampering detected ({result['table']})",
                    result["problems"][0],
                    len(result["problems"]),
                ))

    alerts.sort(key=lambda a: (SEVERITY_ORDER[a.severity], a.rule))
    return alerts

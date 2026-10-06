import csv
import io
import sqlite3
import unittest
from datetime import datetime, timedelta

from tests.base import TempProjectTestCase
from database.database import log_activity, log_admin_activity
from modules import alerts, analytics, reports, two_factor, totp
from modules import messaging_service as ms

NOW = datetime(2026, 10, 1, 12, 0, 0)


def stamp(**delta):
    return (NOW - timedelta(**delta)).strftime("%Y-%m-%d %H:%M:%S")


class AlertTests(TempProjectTestCase):

    def setUp(self):
        super().setUp()
        self.a = self.make_branch("Alpha")
        self.b = self.make_branch("Beta")

    def rules(self, **kw):
        return {x.rule: x for x in alerts.evaluate_alerts(NOW, **kw)}

    def test_quiet_system_has_no_alerts(self):
        self.assertEqual(alerts.evaluate_alerts(NOW), [])

    def test_repeated_lockouts_medium_then_high(self):
        for i in range(2):
            log_activity(self.a, "ACCOUNT_LOCKED", "locked", stamp(hours=i + 1))
        self.assertEqual(self.rules()["REPEATED_LOCKOUTS"].severity, "MEDIUM")
        for i in range(2):
            log_activity(self.a, "ACCOUNT_LOCKED", "locked", stamp(hours=i + 5))
        self.assertEqual(self.rules()["REPEATED_LOCKOUTS"].severity, "HIGH")

    def test_old_lockouts_are_ignored(self):
        for i in range(4):
            log_activity(self.a, "ACCOUNT_LOCKED", "locked", stamp(days=3, hours=i))
        self.assertNotIn("REPEATED_LOCKOUTS", self.rules())

    def test_failed_login_spike(self):
        for i in range(5):
            log_activity(self.a, "FAILED_LOGIN", "bad", stamp(minutes=i + 1))
        self.assertEqual(self.rules()["FAILED_LOGIN_SPIKE"].severity, "MEDIUM")
        for i in range(5):
            log_activity(self.b, "FAILED_2FA", "bad", stamp(minutes=i + 1))
        spike = self.rules()["FAILED_LOGIN_SPIKE"]
        self.assertEqual(spike.severity, "HIGH")
        self.assertIn("2 branch", spike.detail)

    def test_admin_failures(self):
        admin = self.make_admin("root_admin")
        for i in range(3):
            log_admin_activity(admin, "ADMIN_FAILED_LOGIN", "bad",
                               stamp(minutes=i + 1))
        found = self.rules()["ADMIN_AUTH_FAILURES"]
        self.assertEqual(found.severity, "HIGH")
        self.assertIn("root_admin", found.title)

    def test_message_flood(self):
        for i in range(15):
            log_activity(self.a, "MESSAGE_SENT", "sent", stamp(minutes=1))
        self.assertIn("MESSAGE_FLOOD", self.rules())

    def test_off_hours_admin_login(self):
        admin = self.make_admin("root_admin")
        log_admin_activity(admin, "ADMIN_LOGIN", "in", "2026-10-01 02:30:00")
        self.assertIn("OFF_HOURS_ADMIN_LOGIN", self.rules())

    def test_admin_without_2fa_until_enabled(self):
        admin = self.make_admin("root_admin")
        self.assertIn("ADMIN_WITHOUT_2FA", self.rules())
        secret = two_factor.start_enrollment("admin", admin)
        two_factor.confirm_enrollment(
            "admin", admin, totp.totp_code(secret, for_time=NOW.timestamp()),
            now=NOW.timestamp())
        self.assertNotIn("ADMIN_WITHOUT_2FA", self.rules())

    def test_tampering_raises_a_high_alert(self):
        log_activity(self.a, "LOGIN", "in", stamp(minutes=1))
        connection = sqlite3.connect("database/bank.db")
        connection.execute("UPDATE activity_logs SET description='x'")
        connection.commit()
        connection.close()
        self.assertEqual(self.rules()["AUDIT_INTEGRITY"].severity, "HIGH")
        self.assertNotIn("AUDIT_INTEGRITY", self.rules(check_integrity=False))

    def test_sorted_by_severity(self):
        admin = self.make_admin("root_admin")
        for i in range(3):
            log_admin_activity(admin, "ADMIN_FAILED_LOGIN", "bad",
                               stamp(minutes=i + 1))
        severities = [x.severity for x in alerts.evaluate_alerts(NOW)]
        self.assertEqual(severities, sorted(
            severities, key=alerts.SEVERITY_ORDER.get))


class AnalyticsTests(TempProjectTestCase):

    def setUp(self):
        super().setUp()
        self.a = self.make_branch("Alpha")
        self.b = self.make_branch("Beta")

    def test_overview_and_breakdowns(self):
        ms.send_message(self.a, self.b, "one", priority="URGENT", now=NOW)
        ms.send_message(self.b, self.a, "two", now=NOW)
        log_activity(self.a, "FAILED_LOGIN", "bad", stamp(hours=1))

        data = analytics.overview(NOW)
        self.assertEqual(data["branches"], 2)
        self.assertEqual(data["messages"], 2)
        self.assertEqual(data["unread"], 2)
        self.assertEqual(data["urgent"], 1)
        self.assertEqual(data["failed_logins_24h"], 1)

        per_branch = {r["Branch"]: r for r in analytics.messages_per_branch()}
        self.assertEqual(per_branch["SB001"]["Sent"], 1)
        self.assertEqual(per_branch["SB001"]["Received"], 1)

        priorities = {r["Priority"]: r["Messages"]
                      for r in analytics.priority_breakdown()}
        self.assertEqual(priorities, {"NORMAL": 1, "URGENT": 1,
                                      "CONFIDENTIAL": 0})

    def test_daily_series_are_zero_filled(self):
        ms.send_message(self.a, self.b, "x", now=NOW)
        series = analytics.messages_per_day(7, NOW)
        self.assertEqual(len(series), 7)
        self.assertEqual(series[-1], ("2026-10-01", 1))
        self.assertEqual(sum(count for _day, count in series), 1)

    def test_lockout_series(self):
        log_activity(self.a, "ACCOUNT_LOCKED", "locked", stamp(days=1))
        series = dict(analytics.lockouts_per_day(7, NOW))
        self.assertEqual(series["2026-09-30"], 1)


class ReportTests(TempProjectTestCase):

    def test_csv_injection_is_neutralised(self):
        for dangerous in ("=cmd()", "+1", "-2", "@SUM(A1)"):
            self.assertEqual(reports.sanitize_cell(dangerous), "'" + dangerous)
        self.assertEqual(reports.sanitize_cell("normal"), "normal")
        self.assertEqual(reports.sanitize_cell(None), "")

    def test_activity_report_and_date_filter(self):
        a = self.make_branch("Alpha")
        log_activity(a, "LOGIN", "=HYPERLINK(evil)", "2026-09-01 09:00:00")
        log_activity(a, "LOGIN", "later", "2026-10-01 09:00:00")

        everything = list(csv.reader(io.StringIO(reports.activity_report())))
        self.assertEqual(len(everything), 3)                    # header + 2
        self.assertIn("'=HYPERLINK(evil)", [c for r in everything for c in r])

        october = list(csv.reader(io.StringIO(
            reports.activity_report(date_from="2026-10-01"))))
        self.assertEqual(len(october), 2)

    def test_message_report_contains_metadata_only(self):
        a, b = self.make_branch("Alpha"), self.make_branch("Beta")
        ms.send_message(a, b, "TopSecretBody", subject="TopSecretSubject")
        text = reports.messages_report()
        self.assertIn("SB001", text)
        self.assertNotIn("TopSecret", text)

    def test_security_and_alert_reports(self):
        self.make_branch("Alpha")
        self.assertIn("SB001", reports.login_security_report())
        sample = [alerts.Alert("R", "HIGH", "T", "D", 3)]
        self.assertIn("HIGH", reports.alerts_report(sample))


if __name__ == "__main__":
    unittest.main()

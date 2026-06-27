import os
import uuid
import datetime
from django.urls import reverse
from django.conf import settings
from django.core import mail
from django.test import override_settings
from rest_framework import status
from finance.tests.basetest import BaseTestCase
from finance.tests.support_test_helpers import patch_support_notify_delay
from finance.models import SupportTicket
from loguru import logger

class SupportLogsTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self._notify_patcher = patch_support_notify_delay()
        self._notify_patcher.start()
        self.addCleanup(self._notify_patcher.stop)
        from django.core.cache import cache
        cache.clear()
        self.url = reverse("support_tickets")
        self.cleanup_paths = []

    def tearDown(self):
        super().tearDown()
        # Clean up any files created during tests
        for path in self.cleanup_paths:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass

    def test_dynamic_loguru_user_files_created(self):
        """
        Verify that dynamic Loguru user files are created when logging with a valid user UUID context.
        """
        user_uuid = uuid.uuid4()
        with logger.contextualize(uid=str(user_uuid)):
            logger.info("This is a test diagnostic log message.")
        logger.complete()

        # Check if log file exists in either location
        possible_paths = [
            os.path.join(settings.BASE_DIR, "logs", "diagnostic", f"{user_uuid}.log"),
            os.path.join(settings.BASE_DIR, "finance", "logs", "diagnostic", f"{user_uuid}.log"),
        ]
        found = False
        for path in possible_paths:
            if os.path.exists(path):
                found = True
                self.cleanup_paths.append(path)
                # Verify content
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    self.assertIn("This is a test diagnostic log message.", content)
                break
        self.assertTrue(found, f"Diagnostic log file not found in possible locations: {possible_paths}")

    @override_settings(BUG_REPORT_TO_EMAIL="admin@example.com")
    def test_bug_ticket_extracts_and_dumps_logs(self):
        """
        Verify that bug tickets extract and dump logs to logs/incidents/incident_{ticket_id}.log
        with the correct 10-minute window logs.
        """
        user_id = str(self.profile.user_id)
        now = datetime.datetime.now()

        # Compute times inside and outside the 10-minute window
        t_outside = now - datetime.timedelta(minutes=15)
        t_inside1 = now - datetime.timedelta(minutes=5)
        t_inside2 = now - datetime.timedelta(minutes=1)

        t_outside_str = t_outside.strftime("%Y-%m-%d %H:%M:%S")
        t_inside1_str = t_inside1.strftime("%Y-%m-%d %H:%M:%S")
        t_inside2_str = t_inside2.strftime("%Y-%m-%d %H:%M:%S")

        # Create user log entries
        log_content = (
            f"{t_outside_str} | INFO     | uid={user_id} - Outside window log\n"
            f"  Continuation line for outside window\n"
            f"{t_inside1_str} | INFO     | uid={user_id} - Inside window log 1\n"
            f"  Continuation line 1 for inside log 1\n"
            f"  Continuation line 2 for inside log 1\n"
            f"{t_inside2_str} | ERROR    | uid={user_id} - Inside window log 2\n"
        )

        # Write to dynamic diagnostic log locations
        log_dirs = [
            os.path.join(settings.BASE_DIR, "logs", "diagnostic"),
            os.path.join(settings.BASE_DIR, "finance", "logs", "diagnostic")
        ]
        for log_dir in log_dirs:
            os.makedirs(log_dir, exist_ok=True)
            log_file_path = os.path.join(log_dir, f"{user_id}.log")
            with open(log_file_path, "w", encoding="utf-8") as f:
                f.write(log_content)
            self.cleanup_paths.append(log_file_path)

        # Send POST request for bug ticket
        payload = {
            "report_type": "BUG",
            "nature": "Test bug for logs",
            "comment": "This bug is to test if logs are extracted properly.",
            "severity": "HIGH",
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        ticket_id = response.data["id"]
        expected_log_key = f"logs/incidents/incident_{ticket_id}.log"
        self.assertEqual(response.data["diagnostic_log_key"], expected_log_key)

        # Check that the incident log was created in at least one of the locations
        incident_paths = [
            os.path.join(settings.BASE_DIR, "logs", "incidents", f"incident_{ticket_id}.log"),
            os.path.join(settings.BASE_DIR, "finance", "logs", "incidents", f"incident_{ticket_id}.log"),
        ]
        found_incident = False
        for path in incident_paths:
            if os.path.exists(path):
                found_incident = True
                self.cleanup_paths.append(path)
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Verify metadata in the incident report
                    self.assertIn(f"Ticket ID: {ticket_id}", content)
                    self.assertIn(f"User ID: {user_id}", content)
                    self.assertIn("Severity: HIGH", content)
                    # Verify correct window matching
                    self.assertIn("Inside window log 1", content)
                    self.assertIn("Continuation line 1 for inside log 1", content)
                    self.assertIn("Continuation line 2 for inside log 1", content)
                    self.assertIn("Inside window log 2", content)
                    # Verify outside logs are filtered out
                    self.assertNotIn("Outside window log", content)
                    self.assertNotIn("Continuation line for outside window", content)
                break
        self.assertTrue(found_incident, f"Incident log file not found in locations: {incident_paths}")

    @override_settings(OPERATOR_NOTIFY_EMAIL="operator@financemanager.local")
    def test_bug_ticket_triggers_notify_email(self):
        """
        Bug ticket submission enqueues F-014 notify_operator (eager) with UUID-only body.
        """
        mail.outbox.clear()
        payload = {
            "report_type": "BUG",
            "nature": "Database down",
            "comment": "The database is not responding to queries.",
            "severity": "HIGH",
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.to, ["operator@financemanager.local"])
        self.assertIn("[FM-NOTIFY]", sent_email.subject)
        self.assertIn("BUG_REPORT", sent_email.subject)
        self.assertIn("Database down", sent_email.body)
        self.assertIn(str(self.profile.user_id), sent_email.body)
        self.assertNotIn("Username:", sent_email.body)
        self.assertNotIn("@", sent_email.body.split("User-Ref:")[0])

    @override_settings(
        OPERATOR_NOTIFY_EMAIL="operator@financemanager.local",
        BETA_FEATURE_REQUESTS_ENABLED=True,
    )
    def test_feature_ticket_triggers_notify_email(self):
        """Feature request submission enqueues F-014 notify with FEATURE_REQUEST event."""
        mail.outbox.clear()
        payload = {
            "report_type": "FEATURE",
            "nature": "Dark mode toggle",
            "comment": "Please add a dark mode option in settings.",
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertIn("[FM-NOTIFY]", sent_email.subject)
        self.assertIn("FEATURE_REQUEST", sent_email.subject)
        self.assertEqual(sent_email.from_email, "featurerequest@thehivemanager.com")
        self.assertIn(str(self.profile.user_id), sent_email.body)

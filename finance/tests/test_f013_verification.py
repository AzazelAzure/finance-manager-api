import os
import uuid

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from loguru import logger
from rest_framework import status

from finance.tests.basetest import BaseTestCase
from finance.tests.support_test_helpers import patch_support_notify_delay


class F013VerificationTestCase(TestCase):
    cleanup_paths: list[str]

    def setUp(self):
        self.cleanup_paths = []

    def tearDown(self):
        for path in self.cleanup_paths:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

    def test_anonymous_uid_does_not_create_diagnostic_file(self):
        with logger.contextualize(uid="anonymous"):
            logger.info("anonymous traffic should not create a file")
        logger.complete()
        diagnostic_dir = os.path.join(settings.BASE_DIR, "logs", "diagnostic")
        if os.path.isdir(diagnostic_dir):
            for name in os.listdir(diagnostic_dir):
                self.assertNotEqual(name, "anonymous.log")

    def test_forged_uid_does_not_create_path_traversal_file(self):
        with logger.contextualize(uid="../../etc/passwd"):
            logger.info("forged uid attempt")
        logger.complete()
        self.assertFalse(os.path.exists("/etc/passwd.log"))

    def test_valid_uuid_creates_diagnostic_file(self):
        user_uuid = uuid.uuid4()
        with logger.contextualize(uid=str(user_uuid)):
            logger.info("authenticated diagnostic line")
        logger.complete()
        path = os.path.join(settings.BASE_DIR, "logs", "diagnostic", f"{user_uuid}.log")
        self.assertTrue(os.path.exists(path))
        self.cleanup_paths.append(path)


class FeatureTicketIncidentTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self._notify_patcher = patch_support_notify_delay()
        self._notify_patcher.start()
        self.addCleanup(self._notify_patcher.stop)
        self.url = reverse("support_tickets")

    @override_settings(BETA_FEATURE_REQUESTS_ENABLED=True)
    def test_feature_ticket_does_not_create_incident_dump(self):
        payload = {
            "report_type": "FEATURE",
            "nature": "Add export",
            "comment": "Please add CSV export for transactions.",
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        ticket_id = response.data["id"]
        incident_paths = [
            os.path.join(settings.BASE_DIR, "logs", "incidents", f"incident_{ticket_id}.log"),
            os.path.join(settings.BASE_DIR, "finance", "logs", "incidents", f"incident_{ticket_id}.log"),
        ]
        self.assertFalse(any(os.path.exists(path) for path in incident_paths))
        self.assertIsNone(response.data.get("diagnostic_log_key"))

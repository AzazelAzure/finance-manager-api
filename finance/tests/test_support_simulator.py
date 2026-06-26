from django.urls import reverse
from django.conf import settings
from django.test import override_settings
from rest_framework import status
from django.core.cache import cache
from finance.tests.basetest import BaseTestCase
from finance.models import SupportTicket
from finance.factories import UserFactory
import logging

logger = logging.getLogger(__name__)

class SupportTicketSimulatorTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        self.url = reverse("support_tickets")
        self.profile_url = reverse("appprofile")

    def tearDown(self):
        cache.clear()
        super().tearDown()

    def test_validation_rules_comment_bounds(self):
        """
        Verify validation rules on the comment field:
        - min_length = 10
        - max_length = 5000
        """
        # 1. Comment too short: 9 characters (fail)
        payload_short = {
            "report_type": "BUG",
            "nature": "Valid bug nature",
            "comment": "123456789"
        }
        res = self.client.post(self.url, payload_short, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("comment", res.data)
        logger.info("Validated: 9 character comment is blocked.")

        # 2. Comment exactly at min threshold: 10 characters (pass)
        payload_min = {
            "report_type": "BUG",
            "nature": "Valid bug nature",
            "comment": "1234567890"
        }
        res = self.client.post(self.url, payload_min, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        logger.info("Validated: 10 character comment is accepted.")

        # Clear cache to reset throttle
        cache.clear()

        # 3. Comment exactly at max threshold: 5000 characters (pass)
        payload_max = {
            "report_type": "BUG",
            "nature": "Valid bug nature",
            "comment": "c" * 5000
        }
        res = self.client.post(self.url, payload_max, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        logger.info("Validated: 5000 character comment is accepted.")

        # Clear cache to reset throttle
        cache.clear()

        # 4. Comment over limit: 5001 characters (fail)
        payload_over = {
            "report_type": "BUG",
            "nature": "Valid bug nature",
            "comment": "c" * 5001
        }
        res = self.client.post(self.url, payload_over, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("comment", res.data)
        logger.info("Validated: 5001 character comment is blocked.")

    def test_validation_rules_nature_bounds(self):
        """
        Verify validation rules on the nature field:
        - non-empty
        - max_length = 255
        """
        # 1. Nature empty (fail)
        payload_empty = {
            "report_type": "BUG",
            "nature": "",
            "comment": "This is a valid length comment."
        }
        res = self.client.post(self.url, payload_empty, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("nature", res.data)
        logger.info("Validated: Empty nature is blocked.")

        # 2. Nature exactly at max threshold: 255 characters (pass)
        payload_max = {
            "report_type": "BUG",
            "nature": "n" * 255,
            "comment": "This is a valid length comment."
        }
        res = self.client.post(self.url, payload_max, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        logger.info("Validated: 255 character nature is accepted.")

        # Clear cache to reset throttle
        cache.clear()

        # 3. Nature over limit: 256 characters (fail)
        payload_over = {
            "report_type": "BUG",
            "nature": "n" * 256,
            "comment": "This is a valid length comment."
        }
        res = self.client.post(self.url, payload_over, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("nature", res.data)
        logger.info("Validated: 256 character nature is blocked.")

    def test_validation_rules_diagnostic_log_key(self):
        """
        Verify validation rules on the diagnostic_log_key field:
        - max_length = 255
        """
        # 1. diagnostic_log_key exactly at max threshold: 255 characters (pass)
        payload_max = {
            "report_type": "BUG",
            "nature": "Valid nature",
            "comment": "This is a valid length comment.",
            "diagnostic_log_key": "d" * 255
        }
        res = self.client.post(self.url, payload_max, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        logger.info("Validated: 255 character diagnostic_log_key is accepted.")

        # Clear cache to reset throttle
        cache.clear()

        # 2. diagnostic_log_key over limit: 256 characters (fail)
        payload_over = {
            "report_type": "BUG",
            "nature": "Valid nature",
            "comment": "This is a valid length comment.",
            "diagnostic_log_key": "d" * 256
        }
        res = self.client.post(self.url, payload_over, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("diagnostic_log_key", res.data)
        logger.info("Validated: 256 character diagnostic_log_key is blocked.")

    def test_validation_invalid_choices(self):
        """
        Verify that invalid report types and severities are rejected.
        """
        # 1. Invalid report type (fail)
        payload_type = {
            "report_type": "CRASH",
            "nature": "Valid nature",
            "comment": "This is a valid length comment."
        }
        res = self.client.post(self.url, payload_type, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("report_type", res.data)

        # 2. Invalid severity choice (fail)
        payload_sev = {
            "report_type": "BUG",
            "severity": "CRITICAL",
            "nature": "Valid nature",
            "comment": "This is a valid length comment."
        }
        res = self.client.post(self.url, payload_sev, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("severity", res.data)
        logger.info("Validated: Invalid choices (report_type/severity) are blocked.")

    def test_rate_limiting_and_isolation_simulator(self):
        """
        Simulate multiple client requests to verify rate-limiting per user context:
        - First 20 requests by User A succeed.
        - 21st request by User A fails with 429.
        - 1st request by User B succeeds (isolation).
        """
        payload = {
            "report_type": "BUG",
            "nature": "Spam ticket nature",
            "comment": "This is a valid description comment."
        }

        # User A sends 20 requests
        for i in range(20):
            res = self.client.post(self.url, payload, format="json")
            self.assertEqual(res.status_code, status.HTTP_201_CREATED, f"Failed at request {i+1}")

        # User A's 21st request
        res = self.client.post(self.url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        logger.info("Validated: 21st request from User A throttled with 429.")

        # User B sends request (should succeed)
        user_b = UserFactory()
        client_b = self.client_class()
        client_b.force_authenticate(user=user_b)
        res_b = client_b.post(self.url, payload, format="json")
        self.assertEqual(res_b.status_code, status.HTTP_201_CREATED)
        logger.info("Validated: User B's request succeeds despite User A being throttled (isolation).")

    @override_settings(BETA_FEATURE_REQUESTS_ENABLED=True)
    def test_gated_feature_requests_enabled(self):
        """
        When feature requests are enabled:
        - FEATURE tickets should be accepted.
        - appprofile details should return feature_requests_enabled = True.
        """
        # GET profile details
        res_profile = self.client.get(self.profile_url)
        self.assertEqual(res_profile.status_code, status.HTTP_200_OK)
        self.assertTrue(res_profile.data["feature_requests_enabled"])

        # POST feature ticket
        payload_feat = {
            "report_type": "FEATURE",
            "nature": "Dark mode support",
            "comment": "Please implement dark mode in the UI."
        }
        res_feat = self.client.post(self.url, payload_feat, format="json")
        self.assertEqual(res_feat.status_code, status.HTTP_201_CREATED)
        logger.info("Validated: Feature requests are accepted when BETA_FEATURE_REQUESTS_ENABLED=True.")

    @override_settings(BETA_FEATURE_REQUESTS_ENABLED=False)
    def test_gated_feature_requests_disabled(self):
        """
        When feature requests are disabled:
        - FEATURE tickets should be rejected with 400 Bad Request.
        - appprofile details should return feature_requests_enabled = False.
        """
        # GET profile details
        res_profile = self.client.get(self.profile_url)
        self.assertEqual(res_profile.status_code, status.HTTP_200_OK)
        self.assertFalse(res_profile.data["feature_requests_enabled"])

        # POST feature ticket
        payload_feat = {
            "report_type": "FEATURE",
            "nature": "Dark mode support",
            "comment": "Please implement dark mode in the UI."
        }
        res_feat = self.client.post(self.url, payload_feat, format="json")
        self.assertEqual(res_feat.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("report_type", res_feat.data)
        self.assertEqual(res_feat.data["report_type"][0], "Feature requests are currently disabled.")
        logger.info("Validated: Feature requests are rejected when BETA_FEATURE_REQUESTS_ENABLED=False.")

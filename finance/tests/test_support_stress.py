from django.urls import reverse
from django.conf import settings
from django.test import override_settings
from rest_framework import status
from django.core.cache import cache
from finance.tests.basetest import BaseTestCase
from finance.models import SupportTicket
from finance.factories import UserFactory

class SupportTicketStressTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        self.url = reverse("support_tickets")

    def tearDown(self):
        cache.clear()
        super().tearDown()

    @override_settings(BETA_FEATURE_REQUESTS_ENABLED=True)
    def test_gate_feature_requests_when_enabled(self):
        # When enabled, both BUG and FEATURE should succeed
        payload_bug = {
            "report_type": "BUG",
            "nature": "Test bug subject",
            "comment": "This is a detailed bug description.",
        }
        payload_feat = {
            "report_type": "FEATURE",
            "nature": "Test feature subject",
            "comment": "This is a detailed feature description.",
        }
        res_bug = self.client.post(self.url, payload_bug, format="json")
        self.assertEqual(res_bug.status_code, status.HTTP_201_CREATED)

        res_feat = self.client.post(self.url, payload_feat, format="json")
        self.assertEqual(res_feat.status_code, status.HTTP_201_CREATED)

    @override_settings(BETA_FEATURE_REQUESTS_ENABLED=False)
    def test_gate_feature_requests_when_disabled(self):
        # When disabled, BUG should succeed, but FEATURE should fail
        payload_bug = {
            "report_type": "BUG",
            "nature": "Test bug subject",
            "comment": "This is a detailed bug description.",
        }
        payload_feat = {
            "report_type": "FEATURE",
            "nature": "Test feature subject",
            "comment": "This is a detailed feature description.",
        }
        res_bug = self.client.post(self.url, payload_bug, format="json")
        self.assertEqual(res_bug.status_code, status.HTTP_201_CREATED)

        res_feat = self.client.post(self.url, payload_feat, format="json")
        self.assertEqual(res_feat.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("report_type", res_feat.data)

    def test_boundary_nature_length(self):
        # nature max_length is 255
        # 0 chars (empty) -> 400
        payload_empty = {
            "report_type": "BUG",
            "nature": "",
            "comment": "This is a detailed bug description.",
        }
        res_empty = self.client.post(self.url, payload_empty, format="json")
        self.assertEqual(res_empty.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("nature", res_empty.data)

        # exactly 255 chars -> 201
        nature_255 = "a" * 255
        payload_255 = {
            "report_type": "BUG",
            "nature": nature_255,
            "comment": "This is a detailed bug description.",
        }
        res_255 = self.client.post(self.url, payload_255, format="json")
        self.assertEqual(res_255.status_code, status.HTTP_201_CREATED)

        # 256 chars -> 400
        nature_256 = "a" * 256
        payload_256 = {
            "report_type": "BUG",
            "nature": nature_256,
            "comment": "This is a detailed bug description.",
        }
        res_256 = self.client.post(self.url, payload_256, format="json")
        self.assertEqual(res_256.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("nature", res_256.data)

        # Unicode/Special chars -> 201
        nature_unicode = "🐛 Bug in system! 💰 Balance is negative. 中文 한국어 日本語"
        payload_unicode = {
            "report_type": "BUG",
            "nature": nature_unicode,
            "comment": "This is a detailed bug description.",
        }
        res_unicode = self.client.post(self.url, payload_unicode, format="json")
        self.assertEqual(res_unicode.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_unicode.data["nature"], nature_unicode)

    def test_boundary_comment_length(self):
        # comment min_length is 10
        # 9 chars -> 400
        payload_9 = {
            "report_type": "BUG",
            "nature": "Valid nature string",
            "comment": "123456789",
        }
        res_9 = self.client.post(self.url, payload_9, format="json")
        self.assertEqual(res_9.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("comment", res_9.data)

        # exactly 10 chars -> 201
        payload_10 = {
            "report_type": "BUG",
            "nature": "Valid nature string",
            "comment": "1234567890",
        }
        res_10 = self.client.post(self.url, payload_10, format="json")
        self.assertEqual(res_10.status_code, status.HTTP_201_CREATED)

        # comment max_length is 5000
        # exactly 5000 chars -> 201
        payload_5000 = {
            "report_type": "BUG",
            "nature": "Valid nature string",
            "comment": "c" * 5000,
        }
        res_5000 = self.client.post(self.url, payload_5000, format="json")
        self.assertEqual(res_5000.status_code, status.HTTP_201_CREATED)

        # 5001 chars -> 400
        payload_5001 = {
            "report_type": "BUG",
            "nature": "Valid nature string",
            "comment": "c" * 5001,
        }
        res_5001 = self.client.post(self.url, payload_5001, format="json")
        self.assertEqual(res_5001.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("comment", res_5001.data)

    def test_field_choices_validation(self):
        # invalid report_type
        payload_invalid_type = {
            "report_type": "RANDO",
            "nature": "Valid nature string",
            "comment": "This is a detailed bug description.",
        }
        res_invalid_type = self.client.post(self.url, payload_invalid_type, format="json")
        self.assertEqual(res_invalid_type.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("report_type", res_invalid_type.data)

        # case sensitivity of report_type
        payload_lowercase = {
            "report_type": "bug",
            "nature": "Valid nature string",
            "comment": "This is a detailed bug description.",
        }
        res_lowercase = self.client.post(self.url, payload_lowercase, format="json")
        self.assertEqual(res_lowercase.status_code, status.HTTP_400_BAD_REQUEST)

        # invalid severity choices (choices are LOW, MEDIUM, HIGH)
        payload_invalid_severity = {
            "report_type": "BUG",
            "severity": "CRITICAL",
            "nature": "Valid nature string",
            "comment": "This is a detailed bug description.",
        }
        res_invalid_severity = self.client.post(self.url, payload_invalid_severity, format="json")
        self.assertEqual(res_invalid_severity.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("severity", res_invalid_severity.data)

        # valid severity choices should succeed
        for sev in ["LOW", "MEDIUM", "HIGH"]:
            payload_sev = {
                "report_type": "BUG",
                "severity": sev,
                "nature": "Valid nature string",
                "comment": "This is a detailed bug description.",
            }
            res_sev = self.client.post(self.url, payload_sev, format="json")
            self.assertEqual(res_sev.status_code, status.HTTP_201_CREATED)

    def test_boundary_diagnostic_log_key(self):
        # diagnostic_log_key max_length is 255
        # exactly 255 chars -> 201
        payload_255 = {
            "report_type": "BUG",
            "nature": "Valid nature string",
            "comment": "This is a detailed bug description.",
            "diagnostic_log_key": "k" * 255,
        }
        res_255 = self.client.post(self.url, payload_255, format="json")
        self.assertEqual(res_255.status_code, status.HTTP_201_CREATED)

        # 256 chars -> 400
        payload_256 = {
            "report_type": "BUG",
            "nature": "Valid nature string",
            "comment": "This is a detailed bug description.",
            "diagnostic_log_key": "k" * 256,
        }
        res_256 = self.client.post(self.url, payload_256, format="json")
        self.assertEqual(res_256.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("diagnostic_log_key", res_256.data)

    def test_rate_limiting_user_isolation(self):
        payload = {
            "report_type": "BUG",
            "nature": "Valid subject line",
            "comment": "This is a valid description with at least 10 chars.",
        }

        # Send 20 requests in a burst for self.user (limit is 20/minute)
        for i in range(20):
            response = self.client.post(self.url, payload, format="json")
            self.assertEqual(response.status_code, status.HTTP_201_CREATED, f"Request {i+1} failed")

        # The 21st request should be throttled
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        # Create another user and authenticate
        other_user = UserFactory()
        self.client.force_authenticate(user=other_user)

        # The other user's requests should succeed, showing rate-limit isolation
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

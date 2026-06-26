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
        self.profile_url = reverse("appprofile")

    def test_support_ticket_post_rate_limiting_per_user(self):
        """
        Verify the rate limiting (20/min) is enforced per user context.
        User A hitting the limit gets 429, but User B can still successfully POST.
        """
        payload = {
            "report_type": "BUG",
            "nature": "Critical bug in transactions page",
            "comment": "The page crashes when clicking the calendar view.",
        }

        # User A makes 20 requests
        for _ in range(20):
            response = self.client.post(self.url, payload, format="json")
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # 21st request by User A must be throttled
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        # User B makes a request
        user_b = UserFactory()
        client_b = self.client_class()
        client_b.force_authenticate(user=user_b)
        response_b = client_b.post(self.url, payload, format="json")
        
        # User B's request must succeed (proving throttle is per-user)
        self.assertEqual(response_b.status_code, status.HTTP_201_CREATED)

    def test_validation_boundary_conditions(self):
        """
        Verify boundary conditions for inputs (nature length, comment length, options).
        """
        # Nature boundary: exactly 255 characters (pass)
        payload = {
            "report_type": "BUG",
            "nature": "a" * 255,
            "comment": "Valid description length.",
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Nature boundary: 256 characters (fail)
        payload["nature"] = "a" * 256
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("nature", response.data)

        # Comment boundary: exactly 10 characters (pass)
        payload = {
            "report_type": "BUG",
            "nature": "Valid nature",
            "comment": "b" * 10,
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Comment boundary: 9 characters (fail)
        payload["comment"] = "b" * 9
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("comment", response.data)

        # Invalid report_type choice (fail)
        payload = {
            "report_type": "SUGGESTION",
            "nature": "Valid nature",
            "comment": "Valid comment description.",
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("report_type", response.data)

        # Invalid severity choice (fail)
        payload = {
            "report_type": "BUG",
            "severity": "CRITICAL",
            "nature": "Valid nature",
            "comment": "Valid comment description.",
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("severity", response.data)

        # Extremely large comment (fail, max_length=5000)
        payload = {
            "report_type": "BUG",
            "nature": "Valid nature",
            "comment": "x" * 5001,
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("comment", response.data)

    @override_settings(BETA_FEATURE_REQUESTS_ENABLED=False)
    def test_gated_feature_requests_when_disabled(self):
        """
        Verify that feature requests are blocked and profiles reflect feature requests are disabled.
        """
        # GET profile details
        profile_response = self.client.get(self.profile_url)
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        self.assertFalse(profile_response.data["feature_requests_enabled"])

        # POST bug report (succeeds)
        payload_bug = {
            "report_type": "BUG",
            "nature": "Valid nature",
            "comment": "Valid comment description.",
        }
        response_bug = self.client.post(self.url, payload_bug, format="json")
        self.assertEqual(response_bug.status_code, status.HTTP_201_CREATED)

        # POST feature request (blocked)
        payload_feature = {
            "report_type": "FEATURE",
            "nature": "Add dark mode",
            "comment": "We need dark mode urgently.",
        }
        response_feature = self.client.post(self.url, payload_feature, format="json")
        self.assertEqual(response_feature.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("report_type", response_feature.data)
        self.assertEqual(response_feature.data["report_type"][0], "Feature requests are currently disabled.")

    @override_settings(BETA_FEATURE_REQUESTS_ENABLED=True)
    def test_gated_feature_requests_when_enabled(self):
        """
        Verify that feature requests are allowed and profiles reflect feature requests are enabled.
        """
        # GET profile details
        profile_response = self.client.get(self.profile_url)
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        self.assertTrue(profile_response.data["feature_requests_enabled"])

        # POST feature request (succeeds)
        payload_feature = {
            "report_type": "FEATURE",
            "nature": "Add dark mode",
            "comment": "We need dark mode urgently.",
        }
        response_feature = self.client.post(self.url, payload_feature, format="json")
        self.assertEqual(response_feature.status_code, status.HTTP_201_CREATED)

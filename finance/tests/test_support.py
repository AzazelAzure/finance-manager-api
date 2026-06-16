from django.urls import reverse
from django.conf import settings
from django.test import override_settings
from rest_framework import status
from finance.tests.basetest import BaseTestCase
from finance.models import SupportTicket

class SupportTicketTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        from django.core.cache import cache
        cache.clear()
        self.url = reverse("support_tickets")

    def test_unauthenticated_user_rejected(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(self.url, {
            "report_type": "BUG",
            "nature": "Test bug subject",
            "comment": "This is a detailed bug description.",
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_bug_report_success(self):
        payload = {
            "report_type": "BUG",
            "nature": "Unable to save transaction",
            "comment": "When trying to save an expense, the app crashes.",
            "diagnostic_log_key": "some-log-key-123",
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)
        self.assertEqual(response.data["report_type"], "BUG")
        self.assertEqual(response.data["nature"], payload["nature"])
        self.assertEqual(response.data["comment"], payload["comment"])
        
        expected_key = f"logs/incidents/incident_{response.data['id']}.log"
        self.assertEqual(response.data["diagnostic_log_key"], expected_key)

        # Check DB
        ticket = SupportTicket.objects.get(id=response.data["id"])
        self.assertEqual(ticket.uid, str(self.profile.user_id))
        self.assertEqual(ticket.report_type, "BUG")
        self.assertEqual(ticket.nature, payload["nature"])
        self.assertEqual(ticket.comment, payload["comment"])
        self.assertEqual(ticket.diagnostic_log_key, expected_key)

    @override_settings(BETA_FEATURE_REQUESTS_ENABLED=True)
    def test_create_feature_request_when_enabled(self):
        payload = {
            "report_type": "FEATURE",
            "nature": "Support dark mode",
            "comment": "I would like to have a dark theme for the user interface.",
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["report_type"], "FEATURE")

        ticket = SupportTicket.objects.get(id=response.data["id"])
        self.assertEqual(ticket.uid, str(self.profile.user_id))
        self.assertEqual(ticket.report_type, "FEATURE")

    @override_settings(BETA_FEATURE_REQUESTS_ENABLED=False)
    def test_create_feature_request_when_disabled(self):
        payload = {
            "report_type": "FEATURE",
            "nature": "Support dark mode",
            "comment": "I would like to have a dark theme for the user interface.",
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("report_type", response.data)

    def test_validation_empty_and_short_fields(self):
        payload = {
            "report_type": "BUG",
            "nature": "",
            "comment": "short",
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("nature", response.data)
        self.assertIn("comment", response.data)

    def test_rate_limiting(self):
        payload = {
            "report_type": "BUG",
            "nature": "Valid subject line",
            "comment": "This is a valid description with at least 10 chars.",
        }
        # Send 25 requests in burst to exceed the 20/minute throttle limit
        throttled = False
        for _ in range(25):
            response = self.client.post(self.url, payload, format="json")
            if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                throttled = True
                break
        self.assertTrue(throttled, "Request burst should have triggered 429 Too Many Requests")

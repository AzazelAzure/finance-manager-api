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

class SupportTicketAdversarialTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        self.url = reverse("support_tickets")
        self.profile_url = reverse("appprofile")

    def tearDown(self):
        cache.clear()
        super().tearDown()

    def test_parameter_injection_spoofing_uid(self):
        """
        Adversarial test: Attempt to submit a ticket with a spoofed uid or read-only fields.
        The backend should ignore user-provided 'uid', 'id', 'emailed', and 'created_at'.
        It must associate the ticket with the authenticated user's uid.
        """
        other_user_uuid = "00000000-0000-0000-0000-000000000000"
        payload = {
            "report_type": "BUG",
            "nature": "Attempting to spoof user identity",
            "comment": "This ticket has a spoofed user identifier.",
            "uid": other_user_uuid,
            "id": "11111111-1111-1111-1111-111111111111",
            "emailed": True,
        }
        res = self.client.post(self.url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        # Retrieve the created ticket and check values
        ticket_id = res.data["id"]
        ticket = SupportTicket.objects.get(id=ticket_id)

        # The ticket UID must be the authenticated user's profile UUID, NOT the spoofed one
        self.assertEqual(ticket.uid, str(self.profile.user_id))
        self.assertNotEqual(ticket.uid, other_user_uuid)

        # The ticket ID must be auto-generated, NOT the spoofed one
        self.assertNotEqual(str(ticket.id), "11111111-1111-1111-1111-111111111111")

        # The emailed status must default to False
        self.assertFalse(ticket.emailed)

    def test_unauthenticated_request_handling(self):
        """
        Adversarial test: Verify that an unauthenticated client cannot submit tickets.
        It should fail with 401 Unauthorized.
        """
        self.client.force_authenticate(user=None)
        payload = {
            "report_type": "BUG",
            "nature": "Valid bug report",
            "comment": "Valid length description for testing.",
        }
        res = self.client.post(self.url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_malformed_json_payload(self):
        """
        Adversarial test: Send malformed JSON payload (bad syntax).
        The API should return 400 Bad Request instead of raising a 500 error.
        """
        malformed_data = "{'report_type': 'BUG', 'nature': 'bad json', 'comment':"
        res = self.client.post(
            self.url,
            data=malformed_data,
            content_type="application/json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_extreme_comment_length_under_limit(self):
        """
        Boundary condition: Verify comment is accepted at exactly 5000 characters.
        """
        payload = {
            "report_type": "BUG",
            "nature": "Boundary check",
            "comment": "x" * 5000
        }
        res = self.client.post(self.url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_extreme_comment_length_over_limit(self):
        """
        Boundary condition: Verify comment is blocked at 5001 characters.
        """
        payload = {
            "report_type": "BUG",
            "nature": "Boundary check",
            "comment": "x" * 5001
        }
        res = self.client.post(self.url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("comment", res.data)

    def test_extreme_nature_length_over_limit(self):
        """
        Boundary condition: Verify nature is blocked at 256 characters.
        """
        payload = {
            "report_type": "BUG",
            "nature": "n" * 256,
            "comment": "Valid description length."
        }
        res = self.client.post(self.url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("nature", res.data)

    def test_invalid_severity_rejected(self):
        """
        Verify that unsupported severity levels are rejected.
        """
        payload = {
            "report_type": "BUG",
            "severity": "CRITICAL",
            "nature": "Critical issue",
            "comment": "Valid description length."
        }
        res = self.client.post(self.url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("severity", res.data)

    def test_blank_and_null_severity_accepted(self):
        """
        Severity is optional; null or blank severity values should be accepted.
        """
        payload = {
            "report_type": "BUG",
            "severity": "",
            "nature": "Optional severity check",
            "comment": "Valid description length."
        }
        res = self.client.post(self.url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["severity"], "")

        # Reset cache throttle
        cache.clear()

        payload_null = {
            "report_type": "BUG",
            "severity": None,
            "nature": "Optional severity check null",
            "comment": "Valid description length."
        }
        res_null = self.client.post(self.url, payload_null, format="json")
        self.assertEqual(res_null.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(res_null.data["severity"])

    def test_empty_payload(self):
        """
        Adversarial test: Send empty dict.
        Should return 400 with validation errors for required fields.
        """
        res = self.client.post(self.url, {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("report_type", res.data)
        self.assertIn("nature", res.data)
        self.assertIn("comment", res.data)

    def test_xss_injection_payload_handled_safely(self):
        """
        Adversarial test: Check that XSS script tags can be stored safely in DB.
        The application must store them exactly as inputted, and serialise them cleanly.
        """
        xss_nature = "<script>alert('xss_nature')</script>"
        xss_comment = "<iframe src='javascript:alert(1)'>Valid description length</iframe>"
        payload = {
            "report_type": "BUG",
            "nature": xss_nature,
            "comment": xss_comment,
        }
        res = self.client.post(self.url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["nature"], xss_nature)
        self.assertEqual(res.data["comment"], xss_comment)

        # Check stored database value is not modified or stripped by backend DB layer
        ticket = SupportTicket.objects.get(id=res.data["id"])
        self.assertEqual(ticket.nature, xss_nature)
        self.assertEqual(ticket.comment, xss_comment)

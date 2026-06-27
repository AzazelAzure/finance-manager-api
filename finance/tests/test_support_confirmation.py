from datetime import timedelta
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from finance.models import SupportTicket
from finance.tasks.notify import should_send_support_confirmation
from finance.tests.basetest import BaseTestCase
from finance.tests.support_test_helpers import patch_all_support_delays, patch_support_confirmation_delay


class SupportConfirmationEmailTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self._notify_patcher, self._confirm_patcher, self._confirm_mock = patch_all_support_delays()
        self.addCleanup(self._notify_patcher.stop)
        self.addCleanup(self._confirm_patcher.stop)
        from django.core.cache import cache

        cache.clear()
        self.url = reverse("support_tickets")

    def test_first_bug_report_queues_confirmation(self):
        response = self.client.post(
            self.url,
            {
                "report_type": "BUG",
                "nature": "Unable to save transaction",
                "comment": "When trying to save an expense, the app crashes.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self._confirm_mock.assert_called_once()

    def test_second_bug_within_five_minutes_skips_confirmation(self):
        payload = {
            "report_type": "BUG",
            "nature": "Valid subject line",
            "comment": "This is a valid description with at least 10 chars.",
        }
        first = self.client.post(self.url, payload, format="json")
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self._confirm_mock.reset_mock()

        second = self.client.post(self.url, payload, format="json")
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self._confirm_mock.assert_not_called()

    def test_should_send_confirmation_helper(self):
        uid = str(self.profile.user_id)
        SupportTicket.objects.create(
            uid=uid,
            report_type=SupportTicket.ReportType.BUG,
            nature="First ticket",
            comment="Detailed enough comment here.",
        )
        self.assertTrue(should_send_support_confirmation(uid, "BUG"))

        SupportTicket.objects.create(
            uid=uid,
            report_type=SupportTicket.ReportType.BUG,
            nature="Second ticket",
            comment="Another detailed enough comment.",
        )
        self.assertFalse(should_send_support_confirmation(uid, "BUG"))

    @patch("finance.tasks.notify.send_mail")
    def test_confirmation_task_sends_email(self, mock_send_mail):
        from finance.tasks.notify import send_user_support_confirmation

        send_user_support_confirmation.run(
            user_id=self.user.id,
            ticket_type="BUG",
            nature="Test nature",
        )
        mock_send_mail.assert_called_once()
        _, kwargs = mock_send_mail.call_args
        self.assertEqual(kwargs["recipient_list"], [self.user.email])

    def test_confirmation_allowed_after_cooldown_window(self):
        uid = str(self.profile.user_id)
        old = SupportTicket.objects.create(
            uid=uid,
            report_type=SupportTicket.ReportType.BUG,
            nature="Old ticket",
            comment="Old ticket with enough detail.",
        )
        SupportTicket.objects.filter(id=old.id).update(
            created_at=timezone.now() - timedelta(minutes=6)
        )
        self.assertTrue(should_send_support_confirmation(uid, "BUG"))

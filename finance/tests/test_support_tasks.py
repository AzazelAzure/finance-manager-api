from django.test import TestCase, override_settings
from django.utils import timezone
from unittest.mock import patch
from datetime import timedelta
from django.contrib.auth import get_user_model
from finance.models import SupportTicket, AppProfile
from finance.tasks.support_digest import send_weekly_feature_requests_email

class SupportDigestTaskTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="test_digest_user", email="digest@test.com", password="password123")
        self.profile = AppProfile.objects.filter(username=self.user).first()
        if not self.profile:
            self.profile = AppProfile.objects.create(username=self.user)

    @override_settings(SUPPORT_DIGEST_TO_EMAIL="")
    @override_settings(BUG_REPORT_TO_EMAIL="")
    def test_task_skips_when_no_recipient(self):
        with patch("finance.tasks.support_digest.send_mail") as mock_send_mail:
            res = send_weekly_feature_requests_email()
            self.assertIn("No recipient email configured", res)
            mock_send_mail.assert_not_called()

    @override_settings(SUPPORT_DIGEST_TO_EMAIL="operator@financemanager.local")
    def test_task_sends_empty_digest_when_no_tickets(self):
        with patch("finance.tasks.support_digest.send_mail") as mock_send_mail:
            res = send_weekly_feature_requests_email()
            self.assertIn("Digest email sent", res)
            self.assertIn("0 feature requests", res)
            mock_send_mail.assert_called_once()
            args, kwargs = mock_send_mail.call_args
            self.assertEqual(kwargs["recipient_list"], ["operator@financemanager.local"])
            self.assertIn("No feature requests", kwargs["message"])

    @override_settings(SUPPORT_DIGEST_TO_EMAIL="operator@financemanager.local")
    def test_task_sends_digest_with_valid_tickets_only(self):
        # 1. Feature request within 7 days
        f1 = SupportTicket.objects.create(
            uid=str(self.profile.user_id),
            report_type=SupportTicket.ReportType.FEATURE,
            nature="Add charts",
            comment="Please add more charts to transaction history.",
            created_at=timezone.now() - timedelta(days=2)
        )
        # 2. Another feature request within 7 days
        f2 = SupportTicket.objects.create(
            uid=str(self.profile.user_id),
            report_type=SupportTicket.ReportType.FEATURE,
            nature="Export CSV",
            comment="Please support exporting transaction history to CSV format.",
            created_at=timezone.now() - timedelta(days=5)
        )
        # 3. Bug report within 7 days (should be ignored)
        b1 = SupportTicket.objects.create(
            uid=str(self.profile.user_id),
            report_type=SupportTicket.ReportType.BUG,
            nature="Page crash",
            comment="The dashboard page crashed on refresh.",
            created_at=timezone.now() - timedelta(days=1)
        )
        # 4. Old feature request > 7 days ago with emailed=True (ignored)
        f_old_emailed = SupportTicket.objects.create(
            uid=str(self.profile.user_id),
            report_type=SupportTicket.ReportType.FEATURE,
            nature="Support PDF",
            comment="PDF support please.",
            emailed=True,
        )
        SupportTicket.objects.filter(id=f_old_emailed.id).update(
            created_at=timezone.now() - timedelta(days=10)
        )
        # 5. Old feature request > 7 days ago, not yet emailed (outside window)
        f_stale = SupportTicket.objects.create(
            uid=str(self.profile.user_id),
            report_type=SupportTicket.ReportType.FEATURE,
            nature="Stale request",
            comment="This request is older than seven days and should wait.",
            emailed=False,
        )
        SupportTicket.objects.filter(id=f_stale.id).update(
            created_at=timezone.now() - timedelta(days=10)
        )

        with patch("finance.tasks.support_digest.send_mail") as mock_send_mail:
            res = send_weekly_feature_requests_email()
            self.assertIn("2 feature requests", res)
            mock_send_mail.assert_called_once()
            args, kwargs = mock_send_mail.call_args
            self.assertEqual(kwargs["recipient_list"], ["operator@financemanager.local"])
            
            # Verify body contains f1 and f2, but not b1 or f_old
            self.assertIn("Add charts", kwargs["message"])
            self.assertIn("Export CSV", kwargs["message"])
            self.assertNotIn("Page crash", kwargs["message"])
            self.assertNotIn("Support PDF", kwargs["message"])
            self.assertNotIn("Stale request", kwargs["message"])

            # Verify HTML message contains tables/content
            self.assertIn("html_message", kwargs)
            self.assertIn("Add charts", kwargs["html_message"])
            self.assertIn("Export CSV", kwargs["html_message"])
            self.assertNotIn("Page crash", kwargs["html_message"])
            self.assertNotIn("Support PDF", kwargs["html_message"])
            self.assertNotIn("Stale request", kwargs["html_message"])

            # Verify that processed tickets have been set to emailed=True, while others remain False
            f1.refresh_from_db()
            f2.refresh_from_db()
            b1.refresh_from_db()
            self.assertTrue(f1.emailed)
            self.assertTrue(f2.emailed)
            self.assertFalse(b1.emailed)

    @override_settings(SUPPORT_DIGEST_TO_EMAIL="operator@financemanager.local")
    def test_digest_html_escapes_user_submitted_ticket_fields(self):
        SupportTicket.objects.create(
            uid=str(self.profile.user_id),
            report_type=SupportTicket.ReportType.FEATURE,
            nature='<img src=x onerror="alert(1)">',
            comment='<a href="https://evil.example/phish">click</a><script>alert(2)</script>',
            created_at=timezone.now() - timedelta(days=1),
        )

        with patch("finance.tasks.support_digest.send_mail") as mock_send_mail:
            send_weekly_feature_requests_email()

        _, kwargs = mock_send_mail.call_args
        html_message = kwargs["html_message"]
        self.assertNotIn("<img", html_message)
        self.assertNotIn("<a href=", html_message)
        self.assertNotIn("<script>", html_message)
        self.assertIn("&lt;img src=x", html_message)
        self.assertIn("onerror=&quot;alert(1)&quot;", html_message)
        self.assertIn("&lt;a href=&quot;https://evil.example/phish&quot;&gt;click&lt;/a&gt;", html_message)
        self.assertIn("&lt;script&gt;alert(2)&lt;/script&gt;", html_message)

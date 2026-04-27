from django.test import override_settings
from django.urls import resolve, reverse
from rest_framework import status
from rest_framework_simplejwt.views import TokenVerifyView

from finance.tests.user_tests.user_base import UserBase


class BetaPhase2ApiContractsTests(UserBase):
    def test_token_verify_route_uses_verify_view(self):
        match = resolve(reverse("token_verify"))
        self.assertIs(match.func.view_class, TokenVerifyView)

    @override_settings(
        BUG_REPORT_TO_EMAIL="admin@example.com",
        DEFAULT_FROM_EMAIL="noreply@example.com",
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    )
    def test_bug_report_endpoint_sends_email(self):
        from django.core import mail

        response = self.client.post(
            reverse("bug_report"),
            {"subject": "Widget crash", "message": "Repro: open dashboard and click refresh twice."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Widget crash", mail.outbox[0].subject)
        self.assertIn(self.user.username, mail.outbox[0].body)

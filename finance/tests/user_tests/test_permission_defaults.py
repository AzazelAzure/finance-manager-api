from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from uuid import uuid4

from finance.tests.basetest import BaseTestCase


class PermissionDefaultsTests(BaseTestCase):
    def test_finance_endpoints_require_authentication(self):
        self.client.force_authenticate(user=None)

        protected_urls = [
            reverse("transactions_list_create"),
            reverse("appprofile"),
            reverse("appprofile_snapshot"),
            reverse("sources_list_create"),
            reverse("upcoming_expenses"),
            reverse("categories"),
            reverse("tags"),
            reverse("bug_report"),
        ]

        for url in protected_urls:
            response = self.client.get(url)
            self.assertEqual(
                response.status_code,
                status.HTTP_401_UNAUTHORIZED,
                msg=f"Expected 401 for {url}, got {response.status_code}",
            )

    def test_user_create_remains_public(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            reverse("user"),
            {
                "username": f"public-signup-{uuid4().hex[:8]}",
                "user_email": f"public-signup-{uuid4().hex[:8]}@example.com",
                "password": "StrongPass1!",
                "tos_version": "1.0",
                "tos_accepted_at": timezone.now().isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_user_create_rejects_duplicate_username_or_email(self):
        self.client.force_authenticate(user=None)

        duplicate_username = self.client.post(
            reverse("user"),
            {
                "username": self.user.username,
                "user_email": f"new-{uuid4().hex[:8]}@example.com",
                "password": "StrongPass1!",
                "tos_version": "1.0",
                "tos_accepted_at": timezone.now().isoformat(),
            },
            format="json",
        )
        self.assertEqual(duplicate_username.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", duplicate_username.data)

        duplicate_email = self.client.post(
            reverse("user"),
            {
                "username": f"new-user-{uuid4().hex[:8]}",
                "user_email": self.user.email,
                "password": "StrongPass1!",
                "tos_version": "1.0",
                "tos_accepted_at": timezone.now().isoformat(),
            },
            format="json",
        )
        self.assertEqual(duplicate_email.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("user_email", duplicate_email.data)

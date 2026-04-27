from django.urls import reverse
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
            reverse("upcoming_expenses_list_create"),
            reverse("categories_list_create"),
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
                "password": "passphrase-1234",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

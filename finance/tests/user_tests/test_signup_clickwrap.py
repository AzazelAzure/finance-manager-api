from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase


class SignupClickwrapTests(APITestCase):
    def setUp(self):
        self.user_url = reverse("user")

    def test_registration_requires_tos_accepted_at(self):
        response = self.client.post(
            self.user_url,
            {
                "username": "newclickwrap",
                "user_email": "clickwrap@example.com",
                "password": "StrongPass1!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("tos_accepted_at", response.data)

    def test_registration_stores_tos_fields(self):
        accepted_at = timezone.now().isoformat()
        response = self.client.post(
            self.user_url,
            {
                "username": "clickwrapok",
                "user_email": "clickwrapok@example.com",
                "password": "StrongPass1!",
                "tos_version": "1.0",
                "tos_accepted_at": accepted_at,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.get(username="clickwrapok")
        self.assertEqual(user.appprofile.tos_version, "1.0")
        self.assertIsNotNone(user.appprofile.tos_accepted_at)

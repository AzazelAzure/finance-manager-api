from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase


class TokenLoginIdentifierTests(APITestCase):
    def test_token_obtain_accepts_email_identifier(self):
        user = get_user_model().objects.create_user(
            username="email-login-user",
            email="email-login-user@example.com",
            password="test-pass-12345",
        )

        response = self.client.post(
            "/api/token/",
            {"username": user.email, "password": "test-pass-12345"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

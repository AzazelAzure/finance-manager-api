from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken


class TokenRefreshResilienceTests(APITestCase):
    def test_refresh_with_deleted_user_returns_auth_error_not_500(self):
        user = get_user_model().objects.create_user(
            username="refresh-missing-user",
            email="refresh-missing-user@example.com",
            password="test-pass-12345",
        )
        refresh = str(RefreshToken.for_user(user))
        user.delete()

        for endpoint in ("/api/token/refresh/", "/api/auth/token/refresh/"):
            with self.subTest(endpoint=endpoint):
                response = self.client.post(
                    endpoint,
                    {"refresh": refresh},
                    format="json",
                )
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
                self.assertIn("detail", response.data)

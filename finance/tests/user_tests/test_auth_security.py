from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import identify_hasher
from django.conf import settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

try:
    from axes.models import AccessAttempt, AccessFailureLog
except ImportError:  # pragma: no cover - axes is a runtime dependency for this suite
    AccessAttempt = None
    AccessFailureLog = None


class AuthSecurityTests(APITestCase):
    def tearDown(self):
        if AccessAttempt is not None:
            AccessAttempt.objects.all().delete()
        if AccessFailureLog is not None:
            AccessFailureLog.objects.all().delete()
        super().tearDown()

    def test_login_lockout_after_repeated_bad_passwords(self):
        user_model = get_user_model()
        user_model.objects.create_user(username="lockout-user", password="StrongPass1!")
        url = reverse("token_auth")

        response = None
        for _ in range(6):
            response = self.client.post(
                url,
                {"username": "lockout-user", "password": "WrongPass1!"},
                format="json",
                REMOTE_ADDR="203.0.113.10",
            )

        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        attempt = AccessAttempt.objects.get(username="lockout-user")
        self.assertGreaterEqual(
            attempt.failures_since_start,
            settings.AXES_FAILURE_LIMIT,
        )

    def test_registration_rejects_weak_password(self):
        response = self.client.post(
            reverse("user"),
            {
                "username": "weak-signup",
                "user_email": "weak-signup@example.com",
                "password": "abc",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_new_passwords_use_argon2_hasher(self):
        user = get_user_model().objects.create_user(
            username="argon2-user",
            email="argon2@example.com",
            password="StrongPass1!",
        )

        self.assertEqual(identify_hasher(user.password).algorithm, "argon2")

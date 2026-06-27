from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from finance.factories import UserFactory


def _signup_payload(**overrides):
    payload = {
        "username": "newuser",
        "user_email": "same@example.com",
        "password": "StrongPass1!",
        "tos_version": "1.0",
        "tos_accepted_at": timezone.now().isoformat(),
    }
    payload.update(overrides)
    return payload


class EmailUniquenessTests(APITestCase):
    def setUp(self):
        self.user_url = reverse("user")
        self.registration_url = reverse("rest_register")

    def test_user_post_duplicate_email_returns_field_error(self):
        UserFactory(username="existing", email="same@example.com")
        response = self.client.post(
            self.user_url,
            _signup_payload(username="newuser", user_email="Same@Example.com"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("user_email", response.data)
        self.assertIn("already registered", str(response.data["user_email"]).lower())

    def test_user_post_duplicate_username_returns_field_error(self):
        UserFactory(username="taken", email="a@example.com")
        response = self.client.post(
            self.user_url,
            _signup_payload(username="Taken", user_email="b@example.com"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)

    def test_registration_rejects_duplicate_email_case_insensitive(self):
        User = get_user_model()
        User.objects.create_user(
            username="first",
            email="dup@example.com",
            password="x" * 12,
        )
        response = self.client.post(
            self.registration_url,
            {
                "username": "second",
                "email": "DUP@example.com",
                "password1": "StrongPass1!",
                "password2": "StrongPass1!",
                "tos_version": "1.0",
                "tos_accepted_at": timezone.now().isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

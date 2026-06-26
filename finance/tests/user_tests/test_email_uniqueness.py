from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from finance.factories import UserFactory


class EmailUniquenessTests(APITestCase):
    def setUp(self):
        self.user_url = reverse("user")
        self.registration_url = reverse("rest_register")

    def test_user_post_duplicate_email_returns_field_error(self):
        UserFactory(username="existing", email="same@example.com")
        response = self.client.post(
            self.user_url,
            {
                "username": "newuser",
                "user_email": "Same@Example.com",
                "password": "StrongPass1!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("user_email", response.data)
        self.assertIn("already registered", str(response.data["user_email"]).lower())

    def test_user_post_duplicate_username_returns_field_error(self):
        UserFactory(username="taken", email="a@example.com")
        response = self.client.post(
            self.user_url,
            {
                "username": "Taken",
                "user_email": "b@example.com",
                "password": "StrongPass1!",
            },
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
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

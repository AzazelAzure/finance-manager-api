from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase


class SignupClickwrapTests(APITestCase):
    def setUp(self):
        self.user_url = reverse("user")
        self.registration_url = reverse("rest_register")

    def test_registration_requires_tos_acceptance(self):
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
        self.assertTrue(
            "tos_accepted_at" in response.data or "tos_version" in response.data,
            msg=response.data,
        )

    def test_registration_rejects_missing_tos_accepted_at_when_version_present(self):
        response = self.client.post(
            self.user_url,
            {
                "username": "newclickwrap2",
                "user_email": "clickwrap2@example.com",
                "password": "StrongPass1!",
                "tos_version": "1.0",
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

    def test_public_registration_requires_tos_acceptance(self):
        response = self.client.post(
            self.registration_url,
            {
                "username": "pubnoTos",
                "email": "pubnotos@example.com",
                "password1": "StrongPass1!",
                "password2": "StrongPass1!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(
            "tos_version" in response.data or "tos_accepted_at" in response.data,
            msg=response.data,
        )
        from django.contrib.auth import get_user_model

        self.assertFalse(
            get_user_model().objects.filter(username="pubnoTos").exists(),
            msg="account must not be created without ToS acceptance",
        )

    def test_public_registration_rejects_unsupported_tos_version(self):
        response = self.client.post(
            self.registration_url,
            {
                "username": "pubbadver",
                "email": "pubbadver@example.com",
                "password1": "StrongPass1!",
                "password2": "StrongPass1!",
                "tos_version": "9.9",
                "tos_accepted_at": timezone.now().isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("tos_version", response.data)

    def test_public_registration_stores_tos_fields_server_set_timestamp(self):
        client_ts = "2000-01-01T00:00:00Z"
        response = self.client.post(
            self.registration_url,
            {
                "username": "pubok",
                "email": "pubok@example.com",
                "password1": "StrongPass1!",
                "password2": "StrongPass1!",
                "tos_version": "1.0",
                "tos_accepted_at": client_ts,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, msg=response.data)
        from django.contrib.auth import get_user_model

        user = get_user_model().objects.get(username="pubok")
        self.assertEqual(user.appprofile.tos_version, "1.0")
        self.assertIsNotNone(user.appprofile.tos_accepted_at)
        # Server must set the timestamp, not trust the (stale) client-supplied value.
        self.assertGreater(user.appprofile.tos_accepted_at.year, 2000)

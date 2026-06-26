from rest_framework.test import APITestCase
from django.contrib.auth.models import User
from rest_framework import status
from django.urls import reverse

class PasswordChangeTests(APITestCase):
    def setUp(self):
        self.username = "testuser"
        self.password = "Old_password1!"
        self.user = User.objects.create_user(username=self.username, password=self.password)
        self.client.force_authenticate(user=self.user)
        self.url = reverse('user')

    def test_password_change_success(self):
        data = {
            "old_password": "Old_password1!",
            "new_password": "New_password2@"
        }
        response = self.client.patch(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify password actually changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("New_password2@"))

    def test_password_change_wrong_old_password(self):
        data = {
            "old_password": "wrong_password",
            "new_password": "new_password456"
        }
        response = self.client.patch(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Incorrect current password", str(response.data))

    def test_password_change_rejects_weak_new_password(self):
        data = {
            "old_password": "Old_password1!",
            "new_password": "short",
        }
        response = self.client.patch(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_password", response.data)

    def test_password_change_missing_fields(self):
        data = {
            "old_password": "Old_password1!"
        }
        response = self.client.patch(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

from django.urls import reverse
from rest_framework import status

from finance.models import AppProfile
from finance.tests.user_tests.user_base import UserBase


class UserAuthorizationTests(UserBase):
    def test_user_patch_rejects_other_username(self):
        response = self.client.patch(
            self.user_url,
            {"username": self.other_user.username, "password": "new-pass-123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_delete_rejects_other_username(self):
        response = self.client.delete(
            self.user_url,
            {"username": self.other_user.username},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(AppProfile.objects.filter(user_id=self.other_profile.user_id).exists())

    def test_user_cannot_modify_other_users_transaction(self):
        # Grab another user's tx id and ensure authenticated caller cannot patch it.
        from finance.models import Transaction

        other_tx_id = Transaction.objects.for_user(self.other_uid).first().tx_id
        response = self.client.patch(
            reverse(self.tx_detail_url_name, kwargs={"tx_id": other_tx_id}),
            {"date": "2025-01-02", "amount": "1.00", "source": "cash", "currency": "USD", "tx_type": "INCOME"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

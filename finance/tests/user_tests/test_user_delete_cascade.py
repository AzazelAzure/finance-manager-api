from django.contrib.auth import get_user_model
from rest_framework import status

from finance.models import (
    AppProfile,
    Category,
    FinancialSnapshot,
    PaymentSource,
    Tag,
    Transaction,
    UpcomingExpense,
)
from finance.tests.user_tests.user_base import UserBase


class UserDeleteCascadeTests(UserBase):
    def test_delete_user_removes_linked_finance_data(self):
        uid = str(self.profile.user_id)
        self.assertTrue(AppProfile.objects.filter(user_id=self.profile.user_id).exists())
        self.assertTrue(FinancialSnapshot.objects.filter(uid=uid).exists())
        self.assertTrue(PaymentSource.objects.filter(uid=uid).exists())

        response = self.client.delete(
            self.user_url,
            {"username": self.user.username},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        User = get_user_model()
        self.assertFalse(User.objects.filter(username=self.user.username).exists())
        self.assertFalse(AppProfile.objects.filter(user_id=self.profile.user_id).exists())
        self.assertFalse(FinancialSnapshot.objects.filter(uid=uid).exists())
        self.assertFalse(Transaction.objects.filter(uid=uid).exists())
        self.assertFalse(PaymentSource.objects.filter(uid=uid).exists())
        self.assertFalse(UpcomingExpense.objects.filter(uid=uid).exists())
        self.assertFalse(Category.objects.filter(uid=uid).exists())
        self.assertFalse(Tag.objects.filter(uid=uid).exists())

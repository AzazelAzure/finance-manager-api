from rest_framework.test import APITestCase
from django.contrib.auth.models import User
from rest_framework import status
from django.urls import reverse
from finance.models import Transaction, PaymentSource, Category, AppProfile

class AccountDeletionTests(APITestCase):
    def setUp(self):
        self.username = "deleteuser"
        self.password = "password123"
        self.user = User.objects.create_user(username=self.username, password=self.password)
        self.client.force_authenticate(user=self.user)
        self.url = reverse('user')
        
        # Create some data
        self.uid = str(self.user.appprofile.user_id)
        Category.objects.create(name="Food", uid=self.uid)
        PaymentSource.objects.create(source="Cash", uid=self.uid, acc_type="CASH")
        Transaction.objects.create(
            date="2026-01-01",
            description="Test",
            amount=10.00,
            created_on="2026-01-01",
            category="Food",
            source="Cash",
            currency="USD",
            tx_id="TX9999",
            uid=self.uid,
            tx_type="EXPENSE"
        )

    def test_delete_account_success(self):
        # Verify data exists
        self.assertEqual(Transaction.objects.filter(uid=self.uid).count(), 1)
        
        data = {"password": "password123"}
        response = self.client.delete(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify user is gone
        self.assertFalse(User.objects.filter(username=self.username).exists())
        
        # Verify data is wiped
        self.assertEqual(Transaction.objects.filter(uid=self.uid).count(), 0)
        self.assertEqual(Category.objects.filter(uid=self.uid).count(), 0)
        self.assertEqual(PaymentSource.objects.filter(uid=self.uid).count(), 0)
        self.assertFalse(AppProfile.objects.filter(user_id=self.uid).exists())

    def test_delete_account_wrong_password(self):
        data = {"password": "wrong_password"}
        response = self.client.delete(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Verify user and data still exist
        self.assertTrue(User.objects.filter(username=self.username).exists())
        self.assertEqual(Transaction.objects.filter(uid=self.uid).count(), 1)

from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from finance.models import *
from django.contrib.auth.models import User
from loguru import logger


# Create your tests here.

class TransactionTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@test.com",
            password="testpassword",
        )
        self.profile = AppProfile.objects.create(username=self.user)
        self.currency = Currency.objects.create(code="USD", name="US Dollar", symbol="$", uid=self.profile)
        self.category = Category.objects.create(name="Test Category", cat_type="BILL", uid=self.profile)
        self.account = PaymentSource.objects.create(
            source="Test Account",
            acc_type="CHECKING",
            uid=self.profile,
        )
        self.asset = CurrentAsset.objects.create(
            source=self.account,
            amount=1000,
            currency=self.currency,
            uid=self.profile,
        )
        self.profile.base_currency = Currency.objects.get(code="USD")
        self.profile.spend_accounts.set(PaymentSource.objects.filter(acc_type="CHECKING"))
        self.profile.save()
        logger.debug(f"Base currency: {self.profile.base_currency}")
        logger.debug(f"Spend accounts: {self.profile.spend_accounts}")
        self.client.force_authenticate(user=self.user)
        self.url = reverse("transaction")

    def test_transaction_add(self):
        logger.debug(f"Beginning expense test")
        data = {
            "uid": self.profile.user_id,
            "date": "2023-01-01",
            "description": "Test Transaction",
            "amount": 100,
            "category": "Test Category",
            "source": self.account.source,
            "currency": self.currency.code,
            "tags": "Test Tag",
            "tx_type": "EXPENSE",
            "is_income": False,
        }
        response = self.client.post(self.url, data, format='json')
        print(response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_transaction_add_income(self):
        logger.debug(f"Beginning income test")
        data = {
            "uid": self.profile.user_id,
            "date": "2023-01-01",
            "description": "Test Transaction",
            "amount": 100,
            "category": "Test Category",
            "source": self.account.source,
            "currency": self.currency.code,
            "tags": "Test Tag",
            "tx_type": "INCOME",
            "is_income": True,
        }
        response = self.client.post(self.url, data, format='json')
        print(response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_bad_format(self):
        logger.debug(f"Beginning bad format test")
        data = {
            "uid": self.profile.user_id,
            "date": "2023-01-01",
            "description": "Test Transaction",
            "amount": 'test',
            "category": "Test Category",
            "source": self.account.source,
            "currency": self.currency.code,
            "tags": "Test Tag",
            "tx_type": "EXPENSE",
            "is_income": False,
        }
        response = self.client.post(self.url, data, format='json')
        print(response.data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_transfer(self):
        logger.debug(f"Beginning transfer test")
        data = [
            {
                "uid": self.profile.user_id,
                "date": "2023-01-01",
                "description": "Test Transaction 1",
                "amount": 100,
                "category": "Test Category",
                "source": self.account.source,
                "currency": self.currency.code,
                "tags": "Test Tag",
                "tx_type": "XFER",
                "is_income": False,
            },
            {
                "uid": self.profile.user_id,
                "date": "2023-01-01",
                "description": "Test Transaction 2",
                "amount": 100,
                "category": "Test Category",
                "source": self.account.source,
                "currency": self.currency.code,
                "tags": "Test Tag",
                "tx_type": "XFER",
                "is_income": True,
            }
        ]
        response = self.client.post(self.url, data, format='json')
        print(response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
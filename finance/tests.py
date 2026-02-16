from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from finance.models import *
from django.contrib.auth.models import User
from finance.factories import *
from loguru import logger

class TransactionTestCase(APITestCase):
    def setUp(self):
        self.user = UserFactory()
        self.profile = self.user.appprofile
        self.category = CategoryFactory.create(uid=self.profile)
        self.source = PaymentSourceFactory.create(uid=self.profile)
        self.currency = self.profile.base_currency
        self.asset = CurrentAssetFactory.create(uid=self.profile, source=self.source, currency=self.currency)
        self.tags = TagFactory.create_batch(2, uid=self.profile)
        self.tag_list = [tag.name for tag in self.tags]
        logger.warning(f"Setup complete.  Tags: {self.tag_list}")
        self.client.force_authenticate(user=self.user)
        self.url = reverse("transaction")

    def test_transaction_add(self):
        logger.debug("Beginning expense test")
    
        tx = TransactionFactory.build(
            uid=self.profile, 
            tx_type='EXPENSE',
            currency=self.currency,
            category=self.category,
            source=self.source,
            )
        
        data = {
            "uid": str(self.profile.user_id),
            "date": tx.date,
            "description": tx.description,
            "amount": tx.amount,
            "category": tx.category.name, 
            "source": tx.source.source,     
            "currency": tx.currency.code,
            "tx_type": tx.tx_type,
            "tags": self.tag_list
        }
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_transaction_add_income(self):
        logger.debug("Beginning income test")
        
        tx = TransactionFactory.build(
            uid=self.profile, 
            tx_type='INCOME',
            currency=self.currency,
            category=self.category,
            source=self.source,
            )
        data = {
            "uid": str(self.profile.user_id),
            "date": tx.date,
            "description": tx.description,
            "amount": tx.amount,
            "category": tx.category.name,
            "source": tx.source.source,
            "currency": tx.currency.code,
            "tx_type": tx.tx_type,
            "tags": self.tag_list,
        }
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_bad_format(self):
        logger.debug("Beginning bad format test")
        # Fixed the AttributeError by using a hardcoded string instead of self.account
        data = {
            "uid": str(self.profile.user_id),
            "date": "2023-01-01",
            "description": "Test Transaction",
            "amount": 'test', # Invalid type
            "category": "Test Category",
            "source": "Invalid Source", 
            "currency": "USD",
            "tags": "Test Tag",
            "tx_type": "EXPENSE",
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_transfer(self):
        logger.debug("Beginning transfer test")
        
        tx_out = TransactionFactory.build(
            uid=self.profile, 
            tx_type='XFER_OUT',
            currency=self.currency,
            category=self.category,
            source=self.source,
            )
        tx_in = TransactionFactory.build(
            uid=self.profile, 
            tx_type='XFER_IN',
            currency=self.currency,
            category=self.category,
            source=self.source,
            )
        
        data = [
            {
                "uid": str(self.profile.user_id),
                "date": tx_out.date,
                "description": tx_out.description,
                "amount": tx_out.amount,
                "category": tx_out.category.name,
                "source": tx_out.source.source,
                "currency": tx_out.currency.code,
                "tx_type": tx_out.tx_type,
                "tags": self.tag_list,
            },
            {
                "uid": str(self.profile.user_id),
                "date": tx_in.date,
                "description": tx_in.description,
                "amount": tx_in.amount,
                "category": tx_in.category.name,
                "source": tx_in.source.source,
                "currency": tx_in.currency.code,
                "tx_type": tx_in.tx_type,
                "tags": self.tag_list,
            }
        ]
        
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
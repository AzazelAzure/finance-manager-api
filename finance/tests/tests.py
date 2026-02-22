from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.forms.models import model_to_dict
from finance.models import *
from django.contrib.auth.models import User
from django.conf import settings
from finance.tests.factories import *
from decimal import Decimal
from currency_converter import CurrencyConverter
from loguru import logger
import random
import os
 # TODO: Reformat docstrings to add line breaks

class BaseTestCase(APITestCase):
    """
    Base test case for all tests.
    Sets up the user and profile.
    """
    def setUp(self):
        self.user = UserFactory()
        self.profile = self.user.appprofile
        self.client.force_authenticate(user=self.user)
        self.url = reverse("transaction")


class TransactionTestCase(BaseTestCase):
    """
    Test case for the Transaction model.
    Creates a transaction, and tests the following:
        - Adding a transaction
        - Updating a transaction
        - Deleting a transaction
        - Retrieving a transaction
        - Verifying data integrity
        - Verifying database integrity
        - Verify calculations are correct
    """
    def setUp(self):
        super.setUp()
        self.source = PaymentSourceFactory.create(uid=self.profile)
        self.currency = self.profile.base_currency
        self.asset = CurrentAsset.objects.for_user(self.profile).get_asset(source=self.source).get()
        self.asset.amount = 100
        self.asset.currency = self.currency
        self.asset.save()
        self.tags = TagFactory.create_batch(2, uid=self.profile)
        self.tag_list = [tag.name for tag in self.tags]
        logger.info(f"Setup complete.  Tags: {self.tag_list}")

    def test_transaction_add(self):
        """
        Tests adding a transaction with tx_type EXPENSE
        
        Passes if:
            - The transaction is created
            - The transaction is correct to what was sent
            - The transaction is in the database
            - The asset amount is correct
            - The database is correct
            - The calculations are correct
        
        Fails if:
            - The transaction is not created
            - The transaction is not correct to what was sent
            - The transaction is not in the database
            - The asset amount is not correct
            - The database is not correct
            - The calculations are not correct
        """
        logger.info("Beginning single transaction test")
    
        tx = TransactionFactory.build(
            uid=self.profile, 
            tx_type='EXPENSE',
            currency=self.currency,
            source=self.source,
            )
        old_amount = self.asset.amount
        data = {
            "uid": str(self.profile.user_id),
            "date": tx.date,
            "description": tx.description,
            "amount": tx.amount,
            "source": tx.source.source,     
            "currency": tx.currency.code,
            "tx_type": tx.tx_type,
            "tags": self.tag_list
        }
        success=True
        response = self.client.post(self.url, data, format='json')
        logger.info(f'Transaction Added: {response.data}')

        # Assertion 1: General assertions
        self._assert_tx(response, data, code=201)

        # Assertion 2: Calcuation assertions
        expected_amount = old_amount - tx.amount
        self.assertEqual(self.asset.amount, expected_amount)
        
    def test_transaction_add_income(self):
        """
        Tests adding a transaction with tx_type INCOME
        
        Passes if:
            - The transaction is created
            - The transaction is correct to what was sent
            - The transaction is in the database
            - The asset amount is correct
            - The database is correct
            - The calculations are correct
        
        Fails if:
            - The transaction is not created
            - The transaction is not correct to what was sent
            - The transaction is not in the database
            - The asset amount is not correct
            - The database is not correct
            - The calculations are not correct
        """
        logger.info("Beginning income test")
        
        tx = TransactionFactory.build(
            uid=self.profile, 
            tx_type='INCOME',
            currency=self.currency,
            source=self.source,
            )
        old_amount = self.asset.amount
        data = {
            "uid": str(self.profile.user_id),
            "date": tx.date,
            "description": tx.description,
            "amount": tx.amount,
            "source": tx.source.source,
            "currency": tx.currency.code,
            "tx_type": tx.tx_type,
            "tags": self.tag_list,
        }
        
        response = self.client.post(self.url, data, format='json')
        logger.info(f'Income Transaction Added: {response.data}')

        # Assertion 1: General assertions
        self._assert_tx(response, data, code=200)

        # Assertion 2: Calcuation assertions
        expected_amount = old_amount + tx.amount
        expected_amount = Decimal(expected_amount)
        logger.info(f'Calculation test: Old Amount: {old_amount}, New Amount: {tx.amount}, Expected Amount: {expected_amount}, Actual Amount: {self.asset.amount}')
        self.assertEqual(self.asset.amount, expected_amount)

    def test_tx_update_source(self):
        """
        Tests updating a transaction's source
        
        Passes if:
            - The transaction is updated
            - The transaction is correct to what was sent
            - The transaction is in the database
            - The asset amount is correct
            - The database is correct
            - The calculations are correct
            - Assets are updated correctly
        
        Fails if:
            - The transaction is not updated
            - The transaction is not correct to what was sent
            - The transaction is not in the database
            - The asset amount is not correct
            - The database is not correct
            - The calculations are not correct
            - Assets are not updated correctly
        """
        logger.info("Beginning transaction update source test")
        
        tx = TransactionFactory.build(
            uid=self.profile, 
            tx_type='EXPENSE',
            currency=self.currency,
            source=self.source,
            )
        new_source = PaymentSourceFactory.create(uid=self.profile)
        new_asset = CurrentAsset.objects.for_user(self.profile).get_asset(source=new_source.source).get()
        new_asset.amount = 1000
        new_asset.currency = self.currency
        new_asset.save()
        old_new_asset_amount = new_asset.amount
        old_amount = self.asset.amount
        self.url = reverse(f'transaction/{tx.tx_id}')
        data = {
            "uid": str(self.profile.user_id),
            "date": tx.date,
            "description": tx.description,
            "amount": tx.amount,
            "source": new_source.source,
            "currency": tx.currency.code,
            "tx_type": tx.tx_type,
            "tags": self.tag_list
        } 
        response = self.client.put(self.url, data, format='json')
        logger.info(f'Transaction Source Updated: {response.data}')

        # Assertion 1: General assertions
        self._assert_tx(response, data, code=200)

        # Assertion 2: Calcuation assertions
        old_expected_amount = old_amount - tx.amount
        new_expected_amount = old_new_asset_amount + tx.amount
        old_expected_amount = Decimal(old_expected_amount)
        new_expected_amount = Decimal(new_expected_amount)
        logger.info(
            f'Calculation test:'
            f'Old Source Amount: {old_amount}.  Expected: {old_expected_amount}, Actual: {self.asset.amount}'
            f'New Source Amount: {old_new_asset_amount}.  Expected: {new_expected_amount}, Actual: {new_asset.amount}'
        )
        self.assertEqual(self.asset.amount, old_expected_amount)
        self.assertEqual(new_asset.amount, new_expected_amount)
    
    def test_tx_update_description(self):
        """
        Tests updating a transaction's description
        
        Passes if:
            - The transaction is updated
            - The transaction is correct to what was sent
            - The transaction is in the database
            - The asset amount was not changed
            - The database is correct
            - The description is updated correctly
        
        Fails if:
            - The transaction is not updated
            - The transaction is not correct to what was sent
            - The transaction is not in the database
            - The asset amount is changed
            - The database is not correct
            - The description is not updated correctly
        """
        logger.info("Beginning transaction update description test")
        
        tx = TransactionFactory.build(
            uid=self.profile, 
            tx_type='EXPENSE',
            currency=self.currency,
            source=self.source,
            )
        self.url = reverse(f'transaction/{tx.tx_id}')
        old_description = tx.description
        old_amount = self.asset.amount
        data = {
            "uid": str(self.profile.user_id),
            "date": tx.date,
            "description": "Updated Description",
            "amount": tx.amount,
            "source": tx.source.source,
            "currency": tx.currency.code,
            "tx_type": tx.tx_type,
            "tags": self.tag_list
        }
        
        response = self.client.put(self.url, data, format='json')
        logger.info(f'Transaction Description Updated: {response.data}')

        # Assertion 1: General assertions
        self._assert_tx(response, data, code=200)

        # Assertion 2: Check if the asset amount was changed
        self.assertEqual(self.asset.amount, old_amount)

        # Assertion 3: Check if the description was changed
        self.assertNotEqual(response.data['description'], old_description)

    def test_tx_update_amount(self):
        """
        Test for updating a transaction's amount
        
        Passes if:
            - The transaction is updated
            - The transaction is correct to what was sent
            - The transaction is in the database
            - The asset amount is correct
            - The database is correct
            - The calculations are correct
            - Assets are updated correctly
        
        Fails if:
            - The transaction is not updated
            - The transaction is not correct to what was sent
            - The transaction is not in the database
            - The asset amount is not correct
            - The database is not correct
            - The calculations are not correct
            - Assets are not updated correctly
        """
        logger.info("Beginning transaction update amount test")
        
        tx = TransactionFactory.build(
            uid=self.profile, 
            tx_type='EXPENSE',
            currency=self.currency,
            source=self.source,
            amount=100,
            )
        old_amount = self.asset.amount
        self.url = reverse(f'transaction/{tx.tx_id}')
        data = {
            "uid": str(self.profile.user_id),
            "date": tx.date,
            "description": tx.description,
            "amount": 1,
            "source": tx.source.source,
            "currency": tx.currency.code,
            "tx_type": tx.tx_type,
            "tags": self.tag_list
        }
        expected_new_amount = old_amount - tx.amount
        expected_new_amount = Decimal(expected_new_amount)
        response = self.client.put(self.url, data, format='json')
        logger.info(f'Transaction Amount Updated: {response.data}')

        # Assertion 1: General assertions
        self._assert_tx(response, data, code=200)

        # Assertion 2: Check if the asset amount is correct
        logger.info(f'Old Amount: {old_amount}, New Amount: {tx.amount}, Expected Amount: {expected_new_amount}, Actual Amount: {self.asset.amount}')
        self.assertEqual(self.asset.amount, expected_new_amount)
    
    def test_tx_update_tags(self):
        """
        Tests updating a transaction's tags
        
        Passes if:
            - The transaction is updated
            - The transaction is correct to what was sent
            - The transaction is in the database
            - The asset amount was not changed
            - The database is correct
            - The tags are updated correctly
        
        Fails if:
            - The transaction is not updated
            - The transaction is not correct to what was sent
            - The transaction is not in the database
            - The asset amount is changed
            - The database is not correct
            - The tags are not updated correctly
        """
        logger.info("Beginning transaction update tags test")
        
        tx = TransactionFactory.build(
            uid=self.profile, 
            tx_type='EXPENSE',
            currency=self.currency,
            source=self.source,
            )
        old_amount = self.asset.amount
        self.url = reverse(f'transaction/{tx.tx_id}')
        data = {
            "uid": str(self.profile.user_id),
            "date": tx.date,
            "description": tx.description,
            "amount": tx.amount,
            "source": tx.source.source,
            "currency": tx.currency.code,
            "tx_type": tx.tx_type,
            "tags": ["Test Tag"]
        }
        response = self.client.put(self.url, data, format='json')
        logger.info(f'Transaction Tags Updated: {response.data}')
        
        # Assertion 1: General assertions
        self._assert_tx(response, data, code=200)

        # Assertion 2: Check if the tags are updated correctly
        self.assertEqual(response.data['tags'], ['Test Tag'])

        # Assertion 3: Check if the asset amount has changed
        self.assertEqual(self.asset.amount, old_amount)
    
    def test_tx_update_date(self):
        """
        Tests updating a transaction's date
        
        Passes if:
            - The transaction is updated
            - The transaction is correct to what was sent
            - The transaction is in the database
            - The asset amount was not changed
            - The database is correct
            - The date is updated correctly
        
        Fails if:
            - The transaction is not updated
            - The transaction is not correct to what was sent
            - The transaction is not in the database
            - The asset amount is changed
            - The database is not correct
            - The date is not updated correctly
        """
        logger.info("Beginning transaction update date test")
        
        tx = TransactionFactory.build(
            uid=self.profile, 
            tx_type='EXPENSE',
            currency=self.currency,
            source=self.source,
            )
        old_amount = self.asset.amount
        old_date = tx.date
        self.url = reverse(f'transaction/{tx.tx_id}')
        data = {
            "uid": str(self.profile.user_id),
            "date": "2023-01-02",
            "description": tx.description,
            "amount": tx.amount,
            "source": tx.source.source,
            "currency": tx.currency.code,
            "tx_type": tx.tx_type,
            "tags": self.tag_list
        }
        
        response = self.client.put(self.url, data, format='json')
        logger.info(f'Transaction Date Updated: {response.data}')
        
        # Assertion 1: General assertions
        self._assert_tx(response, data, code=200)

        # Assertion 2: Check if the date is updated correctly
        self.assertNotEqual(response.data['date'], old_date)

        # Assertion 3: Check if the asset amount has changed
        self.assertEqual(self.asset.amount, old_amount)

    def test_tx_update_type(self):
        """
        Tests updating a transaction's type.
        This tests specifically for changing a transaction from an expense to an income.
        If test is passed, then it can be assumed other transaction types are working correctly.
        
        Passes if:
            - The transaction is updated
            - The transaction is correct to what was sent
            - The transaction is in the database
            - The asset amount is correct. 
            - The database is correct
            - The type is updated correctly
        
        Fails if:
            - The transaction is not updated
            - The transaction is not correct to what was sent
            - The transaction is not in the database
            - The asset amount is not correct
            - The database is not correct
            - The type is not updated correctly
        """
        logger.info("Beginning transaction update type test")
        
        tx = TransactionFactory.build(
            uid=self.profile, 
            tx_type='EXPENSE',
            currency=self.currency,
            source=self.source,
            )
        old_amount = self.asset.amount
        self.url = reverse(f'transaction/{tx.tx_id}')
        data = {
            "uid": str(self.profile.user_id),
            "date": tx.date,
            "description": tx.description,
            "amount": tx.amount,
            "source": tx.source.source,
            "currency": tx.currency.code,
            "tx_type": "INCOME",
            "tags": self.tag_list
        }

        # Calculations for changing an amount first revert the old tranction.
        # They then add the new transation.
        # So expected amount is (old_amount + tx.amount) + tx.amount
        # Since amount isn't changed, you can use the same amount for the calculation.
        expected_amount = (old_amount + tx.amount) + tx.amount

        response = self.client.put(self.url, data, format='json')
        logger.info(f'Transaction Type Updated: {response.data}')
        
        # Assertion 1: General assertions
        self._assert_tx(response, data, code=200)

        # Assertion 2: Check if the transaction type is updated correctly
        self.assertEqual(response.data['tx_type'], 'INCOME')

        # Assertion 3: Check if the asset amount is correct
        self.assertEqual(self.asset.amount, expected_amount)

    def test_bad_amount(self):
        """
        Tests sending a transaction with an invalid amount type.

        Passes if:
            - The transaction is not created
        
        Fails if:
            - The transaction is created
        """
        logger.info("Beginning bad format test")
        data = {
            "uid": str(self.profile.user_id),
            "date": "2023-01-01",
            "description": "Test Transaction",
            "amount": 'test', 
            "source": self.source, 
            "currency": "USD",
            "tags": "Test Tag",
            "tx_type": "EXPENSE",
        }
        response = self.client.post(self.url, data, format='json')
        logger.info(f'Bad Amount Response: {response.data}')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_tags(self):
        """
        Tests sending a transaction with no tags.

        Passes if:
            - The transaction is created
            - The transaction is correct to what was sent
            - The transaction is in the database
            - The asset amount is correct
            - The database is correct
            - Returns and empty list of tags

        Fails if:
            - The transaction is not created
            - The transaction is not correct to what was sent
            - The transaction is not in the database
            - The asset amount is not correct
            - The database is not correct
            - Returns a list of tags or None
            - The list of tags is not empty
        """
        logger.info("Beginning no tags test")
        old_amount = self.asset.amount
        data = {
            "uid": str(self.profile.user_id),
            "date": "2023-01-01",
            "description": "Test Transaction",
            "amount": 100,
            "source": self.source, 
            "currency": "USD",
            "tx_type": "EXPENSE",
        }
        expected_amount = old_amount - data['amount']
        expected_amount = Decimal(expected_amount)
        response = self.client.post(self.url, data, format='json')
        logger.info(f'No Tags Response: {response.data}')

        # Assertions are handled here due to unique case of sending no tags, but expecting tags returned
        # This is a valid case, and should not fail.

        # Assertion 1: Check if the transaction is created
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Assertion 2: Check if the tags are empty
        self.assertEqual(response.data['tags'], [])

        # Assertion 3: Check if returned data matches sent data
        for key in data.keys():
            self.assertEqual(response.data[key], data[key])
        
        # Assertion 4: Check if the transaction is in the database
        tx = Transaction.objects.for_user(self.profile).get_tx(response.data['tx_id']).get()
        tx = model_to_dict(tx)
        for key in data.keys():
            self.assertEqual(tx[key], data[key])

        # Assertion 5: Check if the asset amount is correct
        logger.info(f'Calculation test: Old Amount: {old_amount}, New Amount: {data["amount"]}, Expected Amount: {expected_amount}, Actual Amount: {self.asset.amount}')
        self.assertEqual(self.asset.amount, expected_amount)

    def test_empty_tags(self):
        """
        Tests sending a transaction with and empty list of tags.

        Passes if:
            - The transaction is created
            - The transaction is correct to what was sent
            - The transaction is in the database
            - The asset amount is correct
            - The database is correct
            - Returns and empty list of tags

        Fails if:
            - The transaction is not created
            - The transaction is not correct to what was sent
            - The transaction is not in the database
            - The asset amount is not correct
            - The database is not correct
            - Returns a list of tags or None
            - The list of tags is not empty
        """
        logger.info("Beginning empty tags test")
        old_amount = self.asset.amount
        data = {
            "uid": str(self.profile.user_id),
            "date": "2023-01-01",
            "description": "Test Transaction",
            "amount": 100,
            "source": "Invalid Source", 
            "currency": "USD",
            "tx_type": "EXPENSE",
            "tags": [],
        }
        expected_amount = old_amount - data['amount']
        expected_amount = Decimal(expected_amount)
        response = self.client.post(self.url, data, format='json')
        logger.info(f'Empty Tags Response: {response.data}')

        # Assertion 1: General assertions
        self._assert_tx(response, data, code=201)

        # Assertion 2: Check if the tags are empty
        self.assertEqual(response.data['tags'], [])

        # Assertion 3: Check if the asset amount is correct
        logger.info(f'Calculation test: Old Amount: {old_amount}, New Amount: {data["amount"]}, Expected Amount: {expected_amount}, Actual Amount: {self.asset.amount}')
        self.assertEqual(self.asset.amount, expected_amount)

    def test_tags_are_none(self):
        """
        Tests sending a transaction with tags set to None.

        Passes if:
            - The transaction is created
            - The transaction is correct to what was sent
            - The transaction is in the database
            - The asset amount is correct
            - The database is correct
            - Returns and empty list of tags

        Fails if:
            - The transaction is not created
            - The transaction is not correct to what was sent
            - The transaction is not in the database
            - The asset amount is not correct
            - The database is not correct
            - Returns a list of tags or None
            - The list of tags is not empty
        """
        logger.info("Beginning tags are None test")
        old_amount = self.asset.amount
        data = {
            "uid": str(self.profile.user_id),
            "date": "2023-01-01",
            "description": "Test Transaction",
            "amount": 100,
            "source": self.source, 
            "currency": "USD",
            "tx_type": "EXPENSE",
            "tags": None,
        }
        expected_amount = old_amount - data['amount']
        expected_amount = Decimal(expected_amount)
        response = self.client.post(self.url, data, format='json')
        logger.info(f'Tags are None Response: {response.data}')

        # Assertion 1: General assertions
        self._assert_tx(response, data, code=201)

        # Assertion 2: Check if the tags are empty
        self.assertEqual(response.data['tags'], [])

        # Assertion 3: Check if the asset amount is correct
        logger.info(f'Calculation test: Old Amount: {old_amount}, New Amount: {data["amount"]}, Expected Amount: {expected_amount}, Actual Amount: {self.asset.amount}')
        self.assertEqual(self.asset.amount, expected_amount)

    def test_add_transfer(self):
        """
        Tests adding a transfer transaction.
        Generates two transactions, one for the transfer out and one for the transfer in.
        While not required for the calculations, structured this way as this should be the most common use case.
        In general, each type of transfer should have the opposite type of transaction. 
        However, if this is not the case, this is a user error, the database will calculate the transfer without issue.
        This test also tests the bulk transaction creation, for two transactions. 

        Passes if:
            - The transactions are created
            - The transactions are correct to what was sent
            - The transactions are in the database
            - The asset amounts are correct
            - The database is correct
            - The calculations are correct
        
        Fails if:
            - The transactions are not created
            - The transactions are not correct to what was sent
            - The transactions are not in the database
            - The asset amounts are not correct
            - The database is not correct
            - The calculations are not correct
        """
        logger.info("Beginning transfer test")
        
        # Create transfer out transaction and grab amount
        tx_out = TransactionFactory.build(
            uid=self.profile, 
            tx_type='XFER_OUT',
            currency=self.currency,
            source=self.source,
            )
        tx_out_amount = tx_out.amount
        out_source_amount = self.asset.amount

        # Create new source for transfer in transaction
        tx_in_source = PaymentSourceFactory.create(uid=self.profile)
        tx_in_currency = self.profile.base_currency
        tx_in_asset = CurrentAsset.objects.for_user(self.profile).get_asset(source=tx_in_source).get()
        tx_in_asset.amount = 1000
        tx_in_asset.currency = tx_in_currency
        tx_in_asset.save()

        # Create transfer in transaction and grab amount
        tx_in = TransactionFactory.build(
            uid=self.profile, 
            tx_type='XFER_IN',
            currency=self.currency,
            source=tx_in_source,
            )
        tx_in_amount = tx_in.amount
        in_source_amount = tx_in_asset.amount

        # Send transactions.
        # This tests both transfers, and bulk transactions.
        data = [
            {
                "uid": str(self.profile.user_id),
                "date": tx_out.date,
                "description": tx_out.description,
                "amount": tx_out.amount,
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
                "source": tx_in.source.source,
                "currency": tx_in.currency.code,
                "tx_type": tx_in.tx_type,
                "tags": self.tag_list,
            }
        ]
        out_source_expected_amount = out_source_amount - tx_out_amount
        out_source_expected_amount = Decimal(out_source_expected_amount)
        in_source_expected_amount = in_source_amount + tx_in_amount
        in_source_expected_amount = Decimal(in_source_expected_amount)
        response = self.client.post(self.url, data, format='json')
        logger.info(f'Transfer Response: {response.data}')

        # Assertions are handled here to manage bulk transaction creation.
        # Assertion 1: Verify that the transactions were created
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Assertion 2: Check if the transactions were created correctly
        data[0]['date'] = str(data[0]['date'])
        data[1]['date'] = str(data[1]['date'])
        for i in range(len(data)):
            for key in data[i].keys():
                self.assertIn(key, response.data[i].keys())
                self.assertEqual(response.data[i][key], data[i][key])

        # Assertion 3: check if the database was updated correctly
        tx_out = Transaction.objects.for_user(self.profile).get_tx(response.data[0]['tx_id']).get()
        tx_out = self._normalize_data(model_to_dict(tx_out))
        for key in data[0].keys():
            self.assertIn(key, tx_out.keys())
            self.assertEqual(tx_out[key], data[0][key])
        tx_in = Transaction.objects.for_user(self.profile).get_tx(response.data[1]['tx_id']).get()
        tx_in = self._normalize_data(model_to_dict(tx_in))
        for key in data[1].keys():
            self.assertIn(key, tx_in.keys())
            self.assertEqual(tx_in[key], data[1][key])

        # Assertion 4: Check if the amounts are correct
        self.assertEqual(self.asset.amount, out_source_expected_amount)
        self.assertEqual(tx_in_asset.amount, in_source_expected_amount)

    def test_add_bulk_transactions(self):
        """
        Tests adding a large number of transactions.
        Generates 100 transactions, each with a random source, amount, currency, and transaction type.
        Designed to fully stress test the system by testing ability to handle large numbers of transactions with random data.

        Passes if:
            - The transactions are created
            - The transactions are correct to what was sent
            - The transactions are in the database
            - The asset amounts are correct
            - The database is correct
            - The calculations are correct
        
        Fails if:
            - The transactions are not created
            - The transactions are not correct to what was sent
            - The transactions are not in the database
            - The asset amounts are not correct
            - The database is not correct
            - The calculations are not correct
        """
        logger.info("Beginning bulk transaction test")

        # Create a batch of sources
        sources = PaymentSourceFactory.create_batch(10, uid=self.profile)
        currencies = list(Currency.objects.all())
        expected_amounts = {}
        asset_currencies = {}

        # Set up the assets
        for source in sources:
            asset = CurrentAsset.objects.for_user(self.profile).get_asset(source=source).get()
            asset.amount = Decimal(random.randint(100, 1000)).quantize(Decimal("0.01"))
            asset.currency = random.choice(currencies)
            asset.save()
            expected_amounts[source.source] = asset.amount
            asset_currencies[source.source] = asset.currency.code

        # Create a batch of transactions
        txs = TransactionFactory.build_batch(
            100,
            uid=self.profile,
            currency= random.choice(currencies),
            source=random.choice(sources),
            )
        
        # Set up data packets and declare the amounts list for later.
        data = []
        amounts = []
        for tx in txs:
            data.append({
                "uid": str(self.profile.user_id),
                "date": tx.date,
                "description": tx.description,
                "amount": tx.amount,
                "source": tx.source.source,     
                "currency": tx.currency.code,
                "tx_type": tx.tx_type,
                "tags": self.tag_list,
            })
            multiplier = 1 if tx.tx_type in ['EXPENSE', 'XFER_OUT'] else -1
            amounts.append(tx.amount * multiplier)
        


        # Calculate the expected amounts
    
        for i in range(len(data)):
            if data[i]['currency'] != asset_currencies[data[i]['source']]:
                amounts[i] = self._convert_currency(amounts[i], data[i]['currency'], asset_currencies[data[i]['source']])
            expected_amounts[data[i]['source']] -= amounts[i]
            expected_amounts[data[i]['source']] = Decimal(expected_amounts[data[i]['source']]).quantize(Decimal("0.01"))
            
        
        response = self.client.post(self.url, data, format='json')
        logger.info(f'Bulk Transfer Response: {response.data}')

        # Assertions are handled here to manage bulk transaction creation.
        # Assertion 1: Verify that the transactions were created
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Assertion 2: Check if the transactions were created correctly
        for i in range(len(data)):
            data[i]['date'] = str(data[i]['date'])
            for key in data[i].keys():
                self.assertIn(key, response.data[i].keys())
                self.assertEqual(response.data[i][key], data[i][key])

        # Assertion 3: Check if the database was updated correctly
        tx_ids = []
        for item in response.data:
            tx_ids.append(item['tx_id'])
        response_data_by_tx_id = {item['tx_id']: item for item in response.data}
        txs = Transaction.objects.for_user(self.profile).filter(tx_id__in=tx_ids)
        for tx in txs:
            tx_data = self._normalize_data(model_to_dict(tx))
            for key in response_data_by_tx_id[tx.tx_id].keys():
                self.assertIn(key, tx_data.keys())
                self.assertEqual(tx_data[key], response_data_by_tx_id[tx.tx_id][key])


        # Assertion 4: Check if the amounts are correct
        assets = CurrentAsset.objects.for_user(self.profile)
        asset_amounts = {}
        for asset in assets:
            asset_amounts[asset.source.source] = asset.amount
        for key in asset_amounts.keys():
            self.assertEqual(asset_amounts[key], expected_amounts[key])

    def test_bad_source(self):
        """
        Tests sending a transaction with an invalid source.

        Passes if:
            - The transaction is not created
        
        Fails if:    
            - The transaction is created
        """
        logger.info("Beginning bad source test")
        data = {
            "uid": str(self.profile.user_id),
            "date": "2023-01-01",
            "description": "Test Transaction",
            "amount": 100,
            "source": "Invalid Source", 
            "currency": "USD",
            "tx_type": "EXPENSE",
            "tags": self.tag_list,
        }
        response = self.client.post(self.url, data, format='json')
        logger.info(f'Bad Source Response: {response.data}')

        # Asertion: Check if the transaction is not created
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bad_currency(self):
        """
        Tests sending a transaction with an invalid currency.
        
        Passes if:
            - The transaction is not created
        
        Fails if:
            - The transaction is created
        """
        logger.info("Beginning bad currency test")
        data = {
            "uid": str(self.profile.user_id),
            "date": "2023-01-01",
            "description": "Test Transaction",
            "amount": 100,
            "source": self.source, 
            "currency": "Invalid Currency",
            "tx_type": "EXPENSE",
            "tags": self.tag_list,
        }
        response = self.client.post(self.url, data, format='json')
        logger.info(f'Bad Currency Response: {response.data}')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bad_tx_type(self):
        """
        Tests sending a transaction with an invalid transaction type.
        
        Passes if:
            - The transaction is not created
        
        Fails if:
            - The transaction is created
        """
        logger.info("Beginning bad tx_type test")
        data = {
            "uid": str(self.profile.user_id),
            "date": "2023-01-01",
            "description": "Test Transaction",
            "amount": 100,
            "source": self.source, 
            "currency": "USD",
            "tx_type": "Invalid Tx Type",
            "tags": self.tag_list,
        }
        response = self.client.post(self.url, data, format='json')
        logger.info(f'Bad Tx Type Response: {response.data}')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bad_uid(self):
        """
        Tests sending a transaction with an invalid user id.

        Passes if:
            - The transaction is not created
        
        Fails if:
            - The transaction is created
        """
        logger.info("Beginning bad uid test")
        data = {
            "uid": "Invalid UID",
            "date": "2023-01-01",
            "description": "Test Transaction",
            "amount": 100,
            "source": self.source, 
            "currency": "USD",
            "tx_type": "EXPENSE",
            "tags": self.tag_list,
        }
        response = self.client.post(self.url, data, format='json')
        logger.info(f'Bad UID Response: {response.data}')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_bad_date(self):
        """
        Tests sending a transaction with an invalid date.

        Passes if:
            - The transaction is not created
        
        Fails if:
            - The transaction is created
        """
        logger.info("Beginning bad date test")
        data = {
            "uid": str(self.profile.user_id),
            "date": "Invalid Date",
            "description": "Test Transaction",
            "amount": 100,
            "source": self.source, 
            "currency": "USD",
            "tx_type": "EXPENSE",
            "tags": self.tag_list,
        }
        response = self.client.post(self.url, data, format='json')
        logger.info(f'Bad Date Response: {response.data}')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_date(self):
        """
        Tests sending a transaction with an empty date.\n
        While the system is designed to accept transactions without a date,\n
        the serializer should reject this due to being empty.

        Passes if:
            - The transaction is not created
        
        Fails if:
            - The transaction is created
        """
        logger.info("Beginning empty date test")
        data = {
            "uid": str(self.profile.user_id),
            "date": "",
            "description": "Test Transaction",
            "amount": 100,
            "source": self.source, 
            "currency": "USD",
            "tx_type": "EXPENSE",
            "tags": self.tag_list,
        }
        response = self.client.post(self.url, data, format='json')
        logger.info(f'Empty Date Response: {response.data}')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_date_is_none(self):
        """
        Tests sending a transaction with a None date.\n
        While the system is designed to accept transactions without a date,\n
        the serializer should reject this due to being None.

        Passes if:
            - The transaction is not created
        
        Fails if:    
            - The transaction is created
        """
        logger.info("Beginning no date test")
        data = {
            "uid": str(self.profile.user_id),
            "date": None,
            "description": "Test Transaction",
            "amount": 100,
            "source": self.source, 
            "currency": "USD",
            "tx_type": "EXPENSE",
            "tags": self.tag_list,
        }
        response = self.client.post(self.url, data, format='json')
        logger.info(f'None Date Response: {response.data}')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_date_missing(self):
        """
        Tests sending a transaction with a missing date.\n
        This should generate a date for the transaction.

        Passes if:
            - The transaction is created
            - The transaction is correct to what was sent
            - The transaction is in the database
            - The asset amount is correct
            - The database is correct
            - The date is created
        
        Fails if:
            - The transaction is not created
            - The transaction is not correct to what was sent
            - The transaction is not in the database
            - The asset amount is not correct
            - The database is not correct
            - The date is not created
        """
        logger.info("Beginning missing date test")
        data = {
            "uid": str(self.profile.user_id),
            "description": "Test Transaction",
            "amount": 100,
            "source": self.source, 
            "currency": "USD",
            "tx_type": "EXPENSE",
            "tags": self.tag_list,
        }
        old_amount = self.asset.amount
        expected_amount = old_amount - data['amount']
        expected_amount = Decimal(expected_amount)
        response = self.client.post(self.url, data, format='json')
        logger.info(f'Missing Date Response: {response.data}')

        # Assertion 1: General assertions
        self._assert_tx(response, data, code=201)

        # Assertion 2: Check if the date was created
        self.assertNotEqual(response.data['date'], None)

        # Assertion 3: Check if the asset amount is correct
        self.assertEqual(self.asset.amount, expected_amount)
    
    def test_source_missing(self):
        """
        Tests sending a transaction with a missing source.

        Passes if:
            - The transaction is not created

        Fails if:
            - The transaction is created
        """
        logger.info("Beginning missing source test")
        data = {
            "uid": str(self.profile.user_id),
            "date": "2023-01-01",
            "description": "Test Transaction",
            "amount": 100,
            "currency": "USD",
            "tx_type": "EXPENSE",
            "tags": self.tag_list,
        }
        response = self.client.post(self.url, data, format='json')
        logger.info(f'Missing Source Response: {response.data}')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_currency_missing(self):
        """
        Tests sending a transaction with a missing currency.

        Passes if:
            - The transaction is not created

        Fails if:
            - The transaction is created
        """
        logger.info("Beginning missing currency test")
        data = {
            "uid": str(self.profile.user_id),
            "date": "2023-01-01",
            "description": "Test Transaction",
            "amount": 100,
            "source": self.source, 
            "tx_type": "EXPENSE",
            "tags": self.tag_list,
        }
        response = self.client.post(self.url, data, format='json')
        logger.info(f'Missing Currency Response: {response.data}')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_tx_type_missing(self):
        """
        Tests sending a transaction with a missing transaction type.

        Passes if:
            - The transaction is not created

        Fails if:
            - The transaction is created
        """
        logger.info("Beginning missing tx_type test")
        data = {
            "uid": str(self.profile.user_id),
            "date": "2023-01-01",
            "description": "Test Transaction",
            "amount": 100,
            "source": self.source, 
            "currency": "USD",
            "tags": self.tag_list,
        }
        response = self.client.post(self.url, data, format='json')
        logger.info(f'Missing Tx Type Response: {response.data}')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_uid_missing(self):
        """
        Tests sending a transaction with a missing user id.

        Passes if:
            - The transaction is not created

        Fails if:
            - The transaction is created
        """
        logger.info("Beginning missing uid test")
        data = {
            "date": "2023-01-01",
            "description": "Test Transaction",
            "amount": 100,
            "source": self.source, 
            "currency": "USD",
            "tx_type": "EXPENSE",
            "tags": self.tag_list,
        }
        response = self.client.post(self.url, data, format='json')
        logger.info(f'Missing UID Response: {response.data}')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_amount_missing(self):
        """
        Tests sending a transaction with a missing amount.

        Passes if:
            - The transaction is not created

        Fails if:
            - The transaction is created
        """
        logger.info("Beginning missing amount test")
        data = {
            "uid": str(self.profile.user_id),
            "date": "2023-01-01",
            "description": "Test Transaction",
            "source": self.source, 
            "currency": "USD",
            "tx_type": "EXPENSE",
            "tags": self.tag_list,
        }
        response = self.client.post(self.url, data, format='json')
        logger.info(f'Missing Amount Response: {response.data}')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_amount_is_none(self):
        """
        Tests sending a transaction with an amount of None.

        Passes if:
            - The transaction is not created

        Fails if:
            - The transaction is created
        """
        logger.info("Beginning None amount test")
        data = {
            "uid": str(self.profile.user_id),
            "date": "2023-01-01",
            "description": "Test Transaction",
            "amount": None,
            "source": self.source, 
            "currency": "USD",
            "tx_type": "EXPENSE",
            "tags": self.tag_list,
        }
        response = self.client.post(self.url, data, format='json')
        logger.info(f'None Amount Response: {response.data}')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_amount_is_string(self):
        """
        Tests sending a transaction with an amount of a string.\n
        This should generate a decimal amount for the transaction.

        Passes if:
            - The transaction is created
            - The transaction is correct to what was sent
            - The transaction is in the database
            - The asset amount is correct
            - The database is correct
            - The calculations are correct

        Fails if:
            - The transaction is not created
            - The transaction is not correct to what was sent
            - The transaction is not in the database
            - The asset amount is not correct
            - The database is not correct
            - The calculations are not correct
        """
        logger.info("Beginning string amount test")
        data = {
            "uid": str(self.profile.user_id),
            "date": "2023-01-01",
            "description": "Test Transaction",
            "amount": "100",
            "source": self.source, 
            "currency": "USD",
            "tx_type": "EXPENSE",
            "tags": self.tag_list,
        }
        old_amount = self.asset.amount
        expected_amount = old_amount - Decimal(data['amount'])
        expected_amount = Decimal(expected_amount)
        response = self.client.post(self.url, data, format='json')
        logger.info(f'String Amount Response: {response.data}')

        # Assertion 1: General assertions
        self._assert_tx(response, data, code=201)

        # Assertion 2: Check if the transaction is created correctly
        self.assertEqual(response.data['amount'], Decimal(data['amount']))

        # Assertion 3: Check if the asset amount is correct
        self.assertEqual(self.asset.amount, expected_amount)

    def test_amount_is_float(self):
        """
        Tests sending a transaction with an amount of a float.\n
        This should generate a decimal amount for the transaction.

        Passes if:
            - The transaction is created
            - The transaction is correct to what was sent
            - The transaction is in the database
            - The asset amount is correct
            - The database is correct
            - The calculations are correct

        Fails if:
            - The transaction is not created
            - The transaction is not correct to what was sent
            - The transaction is not in the database
            - The asset amount is not correct
            - The database is not correct            
            - The calculations are not correct
        """
        logger.info("Beginning float amount test")
        data = {
            "uid": str(self.profile.user_id),
            "date": "2023-01-01",
            "description": "Test Transaction",
            "amount": 100.0,
            "source": self.source, 
            "currency": "USD",
            "tx_type": "EXPENSE",
            "tags": self.tag_list,
        }
        old_amount = self.asset.amount
        expected_amount = old_amount - Decimal(data['amount'])
        expected_amount = Decimal(expected_amount)
        response = self.client.post(self.url, data, format='json')
        logger.info(f'Float Amount Response: {response.data}')
        
        # Assertion 1: General assertions
        self._assert_tx(response, data, code=201)

        # Assertion 2: Check if the transaction is created correctly
        self.assertEqual(response.data['amount'], Decimal(data['amount']))

        # Assertion 3: Check if the asset amount is correct
        self.assertEqual(self.asset.amount, expected_amount)

    def test_amount_is_int(self):
        """
        Tests sending a transaction with an amount of an int.\n
        This should generate a decimal amount for the transaction.

        Passes if:
            - The transaction is created
            - The transaction is correct to what was sent
            - The transaction is in the database
            - The asset amount is correct
            - The database is correct
            - The calculations are correct

        Fails if:
            - The transaction is not created
            - The transaction is not correct to what was sent
            - The transaction is not in the database
            - The asset amount is not correct
            - The database is not correct
            - The calculations are not correct
        """
        logger.info("Beginning int amount test")
        data = {
            "uid": str(self.profile.user_id),
            "date": "2023-01-01",
            "description": "Test Transaction",
            "amount": 100,
            "source": self.source, 
            "currency": "USD",
            "tx_type": "EXPENSE",
            "tags": self.tag_list,
        }
        old_amount = self.asset.amount
        expected_amount = old_amount - Decimal(data['amount'])
        expected_amount = Decimal(expected_amount)
        response = self.client.post(self.url, data, format='json')
        logger.info(f'Int Amount Response: {response.data}')
        
        # Assertion 1: General assertions
        self._assert_tx(response, data, code=201)

        # Assertion 2: Check if the transaction is created correctly
        self.assertEqual(response.data['amount'], Decimal(data['amount']))

        # Assertion 3: Check if the asset amount is correct
        self.assertEqual(self.asset.amount, expected_amount)

    def test_uid_is_none(self):
        """
        Tests sending a transaction with a None user id.

        Passes if:
            - The transaction is not created

        Fails if:
            - The transaction is created
        """
        logger.info("Beginning no uid test")
        data = {
            "uid": None,
            "date": "2023-01-01",
            "description": "Test Transaction",
            "amount": 100,
            "source": self.source, 
            "currency": "USD",
            "tx_type": "EXPENSE",
            "tags": self.tag_list,
        }
        response = self.client.post(self.url, data, format='json')
        logger.info(f'None UID Response: {response.data}')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_tx_type_is_none(self):
        """
        Tests sending a transaction with a None transaction type.

        Passes if:
            - The transaction is not created

        Fails if:
            - The transaction is created
        """
        logger.info("Beginning none tx_type test")
        data = {
            "uid": str(self.profile.user_id),
            "date": "2023-01-01",
            "description": "Test Transaction",
            "amount": 100,
            "source": self.source, 
            "currency": "USD",
            "tx_type": None,
            "tags": self.tag_list,
        }
        response = self.client.post(self.url, data, format='json')
        logger.info(f'None Tx Type Response: {response.data}')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_currency_is_none(self):
        """
        Tests sending a transaction with a None currency.

        Passes if:
            - The transaction is not created

        Fails if:
            - The transaction is created
        """
        logger.info("Beginning none currency test")
        data = {
            "uid": str(self.profile.user_id),
            "date": "2023-01-01",
            "description": "Test Transaction",
            "amount": 100,
            "source": self.source, 
            "currency": None,
            "tx_type": "EXPENSE",
            "tags": self.tag_list,
        }
        response = self.client.post(self.url, data, format='json')
        logger.info(f'None Currency Response: {response.data}')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_source_is_none(self):
        """
        Tests sending a transaction with a None source.

        Passes if:
            - The transaction is not created

        Fails if:
            - The transaction is created
        """
        logger.info("Beginning none source test")
        data = {
            "uid": str(self.profile.user_id),
            "date": "2023-01-01",
            "description": "Test Transaction",
            "amount": 100,
            "source": None, 
            "currency": "USD",
            "tx_type": "EXPENSE",
            "tags": self.tag_list,
        }
        response = self.client.post(self.url, data, format='json')
        logger.info(f'None Source Response: {response.data}')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_description_is_none(self):
        """
        Tests sending a transaction with a None description.
        This should be valid, but should not be used.

        Passes if:
            - The transaction is created
            - The transaction is correct to what was sent
            - The transaction is in the database
            - The asset amount is correct
            - The database is correct

        Fails if:
            - The transaction is not created
            - The transaction is not correct to what was sent
            - The transaction is not in the database
            - The asset amount is not correct
            - The database is not correct
        """
        logger.info("Beginning none description test")
        data = {
            "uid": str(self.profile.user_id),
            "date": "2023-01-01",
            "description": None,
            "amount": 100,
            "source": self.source, 
            "currency": "USD",
            "tx_type": "EXPENSE",
            "tags": self.tag_list,
        }
        old_amount = self.asset.amount
        expected_amount = old_amount - data['amount']
        expected_amount = Decimal(expected_amount)
        response = self.client.post(self.url, data, format='json')
        logger.info(f'None Description Response: {response.data}')
        
        # Assertion 1: General assertions
        self._assert_tx(response, data, code=201)

        # Assertion 2: Check if the transaction is created correctly
        self.assertEqual(response.data['amount'], Decimal(data['amount']))

        # Assertion 3: Check if the asset amount is correct
        self.assertEqual(self.asset.amount, expected_amount)

    def test_delete_tx(self):
        """
        Tests deleting a transaction.\n
        The delete endpoint returns the deleted transaction with the response.\n
        This allows testing to verify the deleted transaction was correct.
        
        Passes if:
            - The transaction is deleted
            - The transaction is correct to what was sent
            - The transaction is not in the database
            - The asset amount is correct
            - The database is correct
        
        Fails if:
            - The transaction is not deleted
            - The transaction is not correct to what was sent
            - The transaction is in the database
            - The asset amount is not correct
            - The database is not correct
        """
        logger.info("Beginning delete transaction test")
        old_amount = self.asset.amount
        tx = TransactionFactory.build(
            uid=self.profile, 
            tx_type='EXPENSE',
            currency=self.currency,
            source=self.source,
            amount=100,
            )
        data ={
            "uid": str(self.profile.user_id),
            "date": tx.date,
            "description": tx.description,
            "amount": tx.amount,
            "source": tx.source.source,     
            "currency": tx.currency.code,
            "tx_type": tx.tx_type,
            "tags": self.tag_list,
        }
        response = self.client.delete(self.url, data, format='json')
        logger.info(f'Delete Transaction Response: {response.data}')

        # Assertion 1: General assertions
        self._assert_tx(response, data, code=200)

        # Assertion 2: Check if the transaction is deleted correctly
        if Transaction.objects.filter(tx_id=response.data['tx_id']).exists():
            self.fail("Transaction not deleted")
        else:
            self.assertTrue("Transaction deleted")

        # Assertion 3: Check if the asset amount is correct
        self.assertEqual(self.asset.amount, old_amount)
        
    def _assert_tx(self, response, tx, code=200):

        # Assertion 1: Check if proper response code was returned
        if code == 200:
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        elif code == 201:
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        elif code == 400:
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            return

        # Assertion 2: Check if data was added correctly
        for key in response.data.keys():
            self.assertIn(key, tx.keys())
            self.assertEqual(response.data[key], tx[key])
    
        # Assertion 3: Check if the transaction was added to the database
        tx_instance = Transaction.objects.for_user(self.profile).get_tx(response.data['tx_id']).get()
        tx_dict = self._normalize_data(model_to_dict(tx_instance))
        tx['date'] = str(tx['date'])
        for key in response.data.keys():
            self.assertIn(key, tx_dict.keys())
            self.assertEqual(response.data[key], tx_dict[key])
        
    def _convert_currency(self, amount, from_currency, to_currency):
        """
        Converts an amount from one currency to base_currency.
        This is a helper for the test_bulk_transactions test.
        """
        rate = os.path.join(settings.BASE_DIR, 'finance', 'data', 'exchange_rates.zip')
        if from_currency == to_currency:
            return Decimal(amount)
        c = CurrencyConverter(rate, decimal=True)
        amount = c.convert(amount, from_currency, to_currency)
        return Decimal(amount)

    def _normalize_data(self, data:dict):
        data['uid'] =  data['uid'].user_id
        data['date'] = str(data['date'])
        data['currency'] = data['currency'].code
        data['source'] = data['source'].source
        if 'tags' in data.keys():
            data['tags'] = [tag.name for tag in data['tags']]
        return data
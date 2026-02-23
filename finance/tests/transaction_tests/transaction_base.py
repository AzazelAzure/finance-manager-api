from finance.tests.basetest import BaseTestCase
from finance.logic.convert_currency import convert_currency

from finance.factories import (
    PaymentSourceFactory, 
    TransactionFactory, 
)
from faker import Faker

from finance.models import(
    CurrentAsset, 
    Currency, 
    Transaction
)

from django.forms.models import model_to_dict
from django.db.models.functions import Abs
from django.urls import reverse
from rest_framework import status

from decimal import Decimal
import random
from loguru import logger

class TransactionBase(BaseTestCase):

    def setUp(self):
        super().setUp()
        # Create random selection pools
        self.currencies = list(Currency.objects.all())
        self.sources = PaymentSourceFactory.create_batch(10, uid=self.profile)
        self.assets = CurrentAsset.objects.for_user(self.profile)
        for asset in self.assets:
            asset.amount = Decimal(random.randint(100, 1000)).quantize(Decimal("0.01"))
            asset.currency = random.choice(self.currencies)
            asset.save()

        # Create transactions
        self.tx_expense = TransactionFactory.build(
            uid=self.profile, 
            tx_type='EXPENSE',
            currency=random.choice(self.currencies),
            source=random.choice(self.sources),
            )
        self.tx_income = TransactionFactory.build(
            uid=self.profile, 
            tx_type='INCOME',
            currency=random.choice(self.currencies),
            source=random.choice(self.sources),
            )
        self.tx_xfer_out = TransactionFactory.build(
            uid=self.profile, 
            tx_type='XFER_OUT',
            currency=random.choice(self.currencies),
            source=random.choice(self.sources),
            )
        self.tx_xfer_in = TransactionFactory.build(
            uid=self.profile, 
            tx_type='XFER_IN',
            currency=random.choice(self.currencies),
            source=random.choice(self.sources),
            )
        self.bulk_tx = TransactionFactory.build_batch(
            100,
            uid=self.profile,
            currency= random.choice(self.currencies),
            source=random.choice(self.sources),
            )
        
        # Create data packets
        self.expense_data = {
            "uid": str(self.profile.user_id),
            "date": self.tx_expense.date,
            "description": self.tx_expense,
            "amount": self.tx_expense.amount,
            "source": self.tx_expense.source.source, 
            "currency": self.tx_expense.currency.code,
            "tx_type": self.tx_expense.tx_type,
            "tags": self.tag_list,
        }
        self.income_data = {
            "uid": str(self.profile.user_id),
            "date": self.tx_income.date,
            "description": self.tx_income.description,
            "amount": self.tx_income.amount,
            "source": self.tx_income.source.source,
            "currency": self.tx_income.currency.code,
            "tx_type": self.tx_income.tx_type,
            "tags": self.tag_list,
        }
        self.xfer_out_data = {
            "uid": str(self.profile.user_id),
            "date": self.tx_xfer_out.date,
            "description": self.tx_xfer_out.description,
            "amount": self.tx_xfer_out.amount,
            "source": self.tx_xfer_out.source.source,
            "currency": self.tx_xfer_out.currency.code,
            "tx_type": self.tx_xfer_out.tx_type,
            "tags": self.tag_list,
        }
        self.xfer_in_data = {
            "uid": str(self.profile.user_id),
            "date": self.tx_xfer_in.date,
            "description": self.tx_xfer_in.description,
            "amount": self.tx_xfer_in.amount,
            "source": self.tx_xfer_in.source.source,
            "currency": self.tx_xfer_in.currency.code,
            "tx_type": self.tx_xfer_in.tx_type,
            "tags": self.tag_list,
        }
        self.bulk_tx_data = [
            {
                "uid": str(self.profile.user_id),
                "date": tx.date,
                "description": tx.description,
                "amount": tx.amount,
                "source": tx.source.source,     
                "currency": tx.currency.code,
                "tx_type": tx.tx_type,
                "tags": self.tag_list,
            }
            for tx in self.bulk_tx
        ]
        self.transfer_data=[self.xfer_out_data, self.xfer_in_data]

        # Set up the URL
        self.url = reverse("transaction")

        # Generate expected amounts
        self.expense_expected_amount = self._calculated_expected_amount(self.expense_data)
        self.income_expected_amount = self._calculated_expected_amount(self.income_data)
        self.xfer_out_expected_amount = self._calculated_expected_amount(self.xfer_out_data)
        self.xfer_in_expected_amount = self._calculated_expected_amount(self.xfer_in_data)

        # Generate expected amounts for bulk transactions
        self.bulk_expected_amounts ={}
        amounts = []
        for i in range(len(self.bulk_tx_data)):
            amounts[i] = self._calculated_expected_amount(self.bulk_tx_data[i])
            self.bulk_expected_amounts[self.bulk_tx_data[i]['source']] = amounts[i]
        
        # Set up normalized tx data
        self.expense_normalized_data = self._normalize_tx_data(self.expense_data)
        self.income_normalized_data = self._normalize_tx_data(self.income_data)
        self.xfer_out_normalized_data = self._normalize_tx_data(self.xfer_out_data)
        self.xfer_in_normalized_data = self._normalize_tx_data(self.xfer_in_data)
        self.bulk_normalized_data = [self._normalize_tx_data(item) for item in self.bulk_tx_data]

    def assert_tx(self, response, data, expected_amount, code=200, bulk=False):
        # Assertion 1: Check if proper response code was returned
        if code == 200:
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        elif code == 201:
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        elif code == 400:
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            return
        elif code == 403:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            return
        
        if bulk:
            self._assert_bulk(response, data, expected_amount)
            return

        # Assertion 2: Check if data was added correctly
        for key in response.data.keys():
            self.assertIn(key, data.keys())
            self.assertEqual(response.data[key], data[key])    

        # Assertion 3: Check if the transaction was added to the database
        tx_instance = Transaction.objects.for_user(self.profile).get_tx(response.data['tx_id']).get()
        tx_dict = self._normalize_tx_data(model_to_dict(tx_instance))
        for key in data.keys():
            self.assertIn(key, tx_dict.keys())
            self.assertEqual(response.data[key], tx_dict[key])

        # Assertion 4: Check if the amount is correct
        self.assertEqual(self.asset.amount, expected_amount)

    def _calculated_expected_amount(self, data):
        
        # Fix amount to positive/negative based on tx_type
        data['amount'] = Decimal(Abs(data['amount']))
        if data['tx_type'] in ['EXPENSE', 'XFER_OUT']:
            data['amount'] = data['amount'] * -1

        # Convert currency if necessary
        asset_currency = self.assets.get_by_source(source=data['source']).get().currency
        if asset_currency != data['currency']:
            data['amount'] = convert_currency(data['amount'], data['currency'], asset_currency.code)

        
        # Return expected amount
        return self.assets.get_asset(source=data['source']).get().amount + data['amount']
    
    def _normalize_tx_data(data):
        data['uid'] =  data['uid'].user_id
        data['date'] = str(data['date'])
        data['currency'] = data['currency'].code
        data['source'] = data['source'].source
        if 'tags' in data.keys():
            data['tags'] = [tag.name for tag in data['tags']]
        if 'bill' in data.keys():
            data['bill'] = data['bill'].name
        return data
    
    def _assert_bulk(self, response, data, expected_amount):

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
            tx_data = self._normalize_tx_data(model_to_dict(tx))
            for key in response_data_by_tx_id[tx.tx_id].keys():
                self.assertIn(key, tx_data.keys())
                self.assertEqual(tx_data[key], response_data_by_tx_id[tx.tx_id][key])


        # Assertion 4: Check if the amounts are correct
        asset_amounts = {}
        for asset in self.assets:
            asset_amounts[asset.source.source] = asset.amount
        for key in asset_amounts.keys():
            self.assertEqual(asset_amounts[key], expected_amount[key])

class TransactionPatchBase(TransactionBase):
    def setUp(self):
        super().setUp()
        # Seed initial transaction to modify
        self.response = self.client.post(self.url, self.expense_data, format='json')
        self.tx_id = self.response.data['tx_id']
        self.url = reverse(f'transaction/{self.tx_id}')

        # Generate updated data packets
        # Update by currency, and ensure new currency is different
        self.update_by_currency = self.expense_data.copy()
        self.new_curency = random.choice(self.currencies)
        while self.new_currency == self.update_by_currency['currency']:
            self.new_currency = random.choice(self.currencies)
        self.update_by_currency['currency'] = self.new_currency.code

        # Update by source, and ensure new source is different
        self.update_by_source = self.expense_data.copy()
        self.new_source = random.choice(self.sources)
        while self.new_source == self.update_by_source['source']:
            self.new_source = random.choice(self.sources)
        self.update_by_source['source'] = self.new_source.source
        
        # Update by date, and ensure new date is different
        self.update_by_date = self.expense_data.copy()
        self.new_date = Faker("date")
        while self.new_date == self.update_by_date['date']:
            self.new_date = Faker("date")
        self.update_by_date['date'] = self.new_date

        # Update by amount, and ensure new amount is different
        self.update_by_amount = self.expense_data.copy()
        self.new_amount = random.randint(100, 1000)
        while self.new_amount == self.update_by_amount['amount']:
            self.new_amount = random.randint(100, 1000)
        self.update_by_amount['amount'] = self.new_amount

        # Update by tags, and ensure new tags are different
        self.update_by_tags = self.expense_data.copy()
        self.new_tags = Faker("words", nb=2)
        while self.new_tags == self.update_by_tags['tags']:
            self.new_tags = Faker("words", nb=2)
        self.update_by_tags['tags'] = self.new_tags
        
        # Update by tx_type, and ensure new tx_type is different
        self.update_by_tx_type = self.expense_data.copy()
        self.new_tx_type = random.choice(['INCOME', 'XFER_IN'])
        self.update_by_tx_type['tx_type'] = self.new_tx_type

        # Generate Updated Data Packets
        self.update_currency_data = {
            "uid": str(self.profile.user_id),
            "date": self.update_by_currency['date'],
            "description": self.update_by_currency['description'],
            "amount": self.update_by_currency['amount'],
            "source": self.update_by_currency['source'],
            "currency": self.update_by_currency['currency'],
            "tx_type": self.update_by_currency['tx_type'],
            "tags": self.update_by_currency['tags']
        }
        self.update_source_data = {
            "uid": str(self.profile.user_id),
            "date": self.update_by_source['date'],
            "description": self.update_by_source['description'],
            "amount": self.update_by_source['amount'],
            "source": self.update_by_source['source'],
            "currency": self.update_by_source['currency'],
            "tx_type": self.update_by_source['tx_type'],
            "tags": self.update_by_source['tags']
        }
        self.update_date_data = {
            "uid": str(self.profile.user_id),
            "date": self.update_by_date['date'],
            "description": self.update_by_date['description'],
            "amount": self.update_by_date['amount'],
            "source": self.update_by_date['source'],
            "currency": self.update_by_date['currency'],
            "tx_type": self.update_by_date['tx_type'],
            "tags": self.update_by_date['tags']
        }
        self.update_amount_data = {
            "uid": str(self.profile.user_id),
            "date": self.update_by_amount['date'],
            "description": self.update_by_amount['description'],
            "amount": self.update_by_amount['amount'],
            "source": self.update_by_amount['source'],
            "currency": self.update_by_amount['currency'],
            "tx_type": self.update_by_amount['tx_type'],
            "tags": self.update_by_amount['tags']
        }
        self.update_tags_data = {
            "uid": str(self.profile.user_id),
            "date": self.update_by_tags['date'],
            "description": self.update_by_tags['description'],
            "amount": self.update_by_tags['amount'],
            "source": self.update_by_tags['source'],
            "currency": self.update_by_tags['currency'],
            "tx_type": self.update_by_tags['tx_type'],
            "tags": self.update_by_tags['tags']
        }
        self.update_tx_type_data = {
            "uid": str(self.profile.user_id),
            "date": self.update_by_tx_type['date'],
            "description": self.update_by_tx_type['description'],
            "amount": self.update_by_tx_type['amount'],
            "source": self.update_by_tx_type['source'],
            "currency": self.update_by_tx_type['currency'],
            "tx_type": self.update_by_tx_type['tx_type'],
            "tags": self.update_by_tx_type['tags']
        }

        # Generate Expected Amounts
        # Get amounts that shouldn't change first
        self.update_date_expected_amount = CurrentAsset.objects.for_user(self.profile.user_id).get_asset(source=self.update_by_date['source']).get().amount
        self.update_tags_expected_amount = CurrentAsset.objects.for_user(self.profile.user_id).get_asset(source=self.update_by_tags['source']).get().amount

        # Get amounts that should change
        self.update_currency_expected_amount = self._calculated_expected_amount(self.update_currency_data)
        self.update_source_expected_amount = self._calculated_expected_amount(self.update_source_data)
        self.update_amount_expected_amount = self._calculated_expected_amount(self.update_amount_data)
        self.update_tx_type_expected_amount = self._calculated_expected_amount(self.update_tx_type_data)
        self.previous_amount = CurrentAsset.objects.for_user(self.profile.user_id).get_asset(source=self.expense_data['source']).get().amount
        self.previous_expected_amount = self.previous_amount + self.expense_data['amount']


        # Generate normalized data
        self.update_currency_normalized_data = self._normalize_tx_data(self.update_currency_data)
        self.update_source_normalized_data = self._normalize_tx_data(self.update_source_data)
        self.update_amount_normalized_data = self._normalize_tx_data(self.update_amount_data)
        self.update_tags_normalized_data = self._normalize_tx_data(self.update_tags_data)
        self.update_tx_type_normalized_data = self._normalize_tx_data(self.update_tx_type_data)
        self.update_date_normalized_data = self._normalize_tx_data(self.update_date_data)
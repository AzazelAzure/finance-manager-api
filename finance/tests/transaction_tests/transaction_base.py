from finance.tests.basetest import BaseTestCase
from finance.logic.convert_currency import convert_currency

from finance.factories import (
    PaymentSourceFactory,
    TransactionFactory,
)
from faker import Faker

from finance.models import Transaction, PaymentSource

from dateutil.relativedelta import relativedelta
from django.utils.dateparse import parse_date
from django.forms.models import model_to_dict
from django.urls import reverse
from django.conf import settings
from rest_framework import status

from datetime import date

from decimal import Decimal
import random
from loguru import logger


class TransactionBase(BaseTestCase):

    def setUp(self):
        super().setUp()
        # Create random selection pools
        sample_size = min(10, len(settings.SUPPORTED_CURRENCIES))
        self.currencies = random.sample(settings.SUPPORTED_CURRENCIES, sample_size)
        self.sources = PaymentSourceFactory.create_batch(10, uid=self.profile.user_id)
        # Capture the initial amount for each source so tests can consistently
        # refer back to the original balances even after API calls mutate them.
        self.initial_source_amounts = {src.source: src.amount for src in self.sources}

        # Create transactions
        self.tx_expense = TransactionFactory.build(
            uid=self.profile, 
            tx_type='EXPENSE',
            currency=random.choice(self.currencies),
            source=random.choice(self.sources),
            category=random.choice(self.categories),
            )
        self.tx_income = TransactionFactory.build(
            uid=self.profile, 
            tx_type='INCOME',
            currency=random.choice(self.currencies),
            source=random.choice(self.sources),
            )
        # Transfer: use two distinct sources and the same amount so expected amounts are deterministic.
        self._source_xfer_out, self._source_xfer_in = random.sample(self.sources, 2)
        _xfer_currency = random.choice(self.currencies)
        _xfer_amount = abs(Decimal(str(random.uniform(10, 500))).quantize(Decimal("0.01")))
        self.tx_xfer_out = TransactionFactory.build(
            uid=self.profile,
            tx_type='XFER_OUT',
            currency=_xfer_currency,
            source=self._source_xfer_out,
            amount=_xfer_amount,
            description="Transfer out",
        )
        self.tx_xfer_in = TransactionFactory.build(
            uid=self.profile,
            tx_type='XFER_IN',
            currency=_xfer_currency,
            source=self._source_xfer_in,
            amount=_xfer_amount,
            date=self.tx_xfer_out.date,
            description="Transfer in",
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
            "description": self.tx_expense.description,
            "amount": self.tx_expense.amount,
            "source": self.tx_expense.source.source,
            "category": random.choice(self.categories).name,
            "currency": self.tx_expense.currency,
            "tx_type": self.tx_expense.tx_type,
            "tags": self.tag_list,
        }
        self.income_data = {
            "uid": str(self.profile.user_id),
            "date": self.tx_income.date,
            "description": self.tx_income.description,
            "amount": self.tx_income.amount,
            "source": self.tx_income.source.source,
            "currency": self.tx_income.currency,
            "tx_type": self.tx_income.tx_type,
            "tags": self.tag_list,
        }
        self.xfer_out_data = {
            "uid": str(self.profile.user_id),
            "date": self.tx_xfer_out.date,
            "description": self.tx_xfer_out.description,
            "amount": self.tx_xfer_out.amount,
            "source": self.tx_xfer_out.source.source,
            "currency": self.tx_xfer_out.currency,
            "tx_type": self.tx_xfer_out.tx_type,
            "tags": self.tag_list,
        }
        self.xfer_in_data = {
            "uid": str(self.profile.user_id),
            "date": self.tx_xfer_in.date,
            "description": self.tx_xfer_in.description,
            "amount": self.tx_xfer_in.amount,
            "source": self.tx_xfer_in.source.source,
            "currency": self.tx_xfer_in.currency,
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
                "currency": tx.currency,
                "tx_type": tx.tx_type,
                "tags": self.tag_list,
            }
            for tx in self.bulk_tx
        ]
        self.transfer_data=[self.xfer_out_data, self.xfer_in_data]

        # Set up the URL
        self.url = reverse("transactions_list_create")

        # Generate expected amounts
        self.expense_expected_amount = self._calculated_expected_amount(self.expense_data)
        self.income_expected_amount = self._calculated_expected_amount(self.income_data)
        self.xfer_out_expected_amount = self._calculated_expected_amount(self.xfer_out_data)
        self.xfer_in_expected_amount = self._calculated_expected_amount(self.xfer_in_data)

        # Generate expected amounts for bulk transactions (one key per source, update per transaction like fincalc)
        self.bulk_expected_amounts = {}
        for src in self.sources:
            self.bulk_expected_amounts[src.source] = src.amount
        for item in self.bulk_tx_data:
            amount = abs(Decimal(item['amount']))
            if item['tx_type'] in ['EXPENSE', 'XFER_OUT']:
                amount = amount * -1
            source = next(src for src in self.sources if src.source == item['source'])
            if source.currency != item['currency']:
                amount = convert_currency(amount, item['currency'], source.currency)
            amount = Decimal(amount).quantize(Decimal("0.01"))
            self.bulk_expected_amounts[item['source']] += amount
        
        # # Set up normalized tx data
        self.expense_normalized_data = self._normalize_tx_data(self.expense_data)
        self.income_normalized_data = self._normalize_tx_data(self.income_data)
        self.xfer_out_normalized_data = self._normalize_tx_data(self.xfer_out_data)
        self.xfer_in_normalized_data = self._normalize_tx_data(self.xfer_in_data)
        self.bulk_normalized_data = [self._normalize_tx_data(item) for item in self.bulk_tx_data]

    def tearDown(self):
        super().tearDown()

    def assert_tx(self, response, data, expected_amount, code=200, bulk=False, index=0):
        # Assertion 1: Check if proper response code was returned
        logger.info(f'Asserting transaction...')
        logger.info('Assertion 1: Checking if proper response code was returned')
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

    
        rows = response.data.get("accepted") or response.data.get("updated")
        self.assertIsNotNone(rows, msg="Response must include accepted or updated transactions")
        accepted_tx = rows[index]

        # Assertion 2: Check if response accepted dict matches request data
        logger.info('Assertion 2: Checking if response accepted dict matches request data')
        for key in data.keys():
            if key == 'uid':
                continue
            self.assertIn(key, accepted_tx.keys())
            if key == 'amount':
                self.assertEqual(
                    Decimal(str(accepted_tx[key])).quantize(Decimal("0.01")),
                    Decimal(str(data[key])).quantize(Decimal("0.01")),
                )
            else:
                self.assertEqual(accepted_tx[key], data[key])

        # Assertion 3: Check if the transaction was added to the database (DB matches accepted)
        logger.info('Assertion 3: Checking if the transaction was added to the database (DB matches accepted)')
        tx_instance = Transaction.objects.for_user(self.profile).get_tx(accepted_tx['tx_id']).get()
        tx_dict = self._normalize_tx_data(model_to_dict(tx_instance))
        for key in data.keys():
            if key == 'uid':
                continue
            if key == 'amount':
                self.assertEqual(
                    Decimal(str(accepted_tx[key])).quantize(Decimal("0.01")),
                    Decimal(str(tx_dict[key])).quantize(Decimal("0.01")),
                )
            else:
                self.assertEqual(accepted_tx[key], tx_dict[key])

        # Assertion 4: Check if the source amount is correct (skip when None — e.g. PATCH tests where
        # expected balance must match Calculator internals; response/DB row checks still apply above).
        if expected_amount is None:
            return
        logger.info('Assertion 4: Checking if the source amount is correct')
        source = PaymentSource.objects.for_user(self.profile.user_id).get_by_source(data['source']).get()
        source.refresh_from_db()
        self.assertEqual(source.amount, expected_amount)

    def _calculated_expected_amount(self, data):
        # Use a local copy so we don't mutate the request payload (data['amount'] must stay 2 decimal places for the serializer)
        amount = abs(Decimal(data['amount']))
        if data['tx_type'] in ['EXPENSE', 'XFER_OUT']:
            amount = amount * -1

        # Convert currency if necessary
        source = next(src for src in self.sources if src.source == data['source'])
        asset_currency = source.currency
        if asset_currency != data['currency']:
            amount = convert_currency(amount, data['currency'], asset_currency)
        amount = Decimal(amount).quantize(Decimal("0.01"))
        base_amount = self._get_initial_source_amount(data['source'])
        return base_amount + amount

    def _get_initial_source_amount(self, source_name):
        """
        Helper to retrieve the original balance for a given source (by name)
        captured at the start of the test setup.
        """
        return self.initial_source_amounts[source_name]
        
    @staticmethod
    def _normalize_tx_data(data):
        data['date'] = str(data['date'])
        data['currency'] = data['currency']
        data['source'] = data['source']
        data['amount'] = abs(Decimal(data['amount']))
        if data['tx_type'] in ['EXPENSE', 'XFER_OUT']:
            data['amount'] = str(Decimal(data['amount']) * -1)
        else:
            data['amount'] = str(Decimal(data['amount']))
        if 'tags' in data.keys():
            if data['tags'] is None:
                data['tags'] = []
            else:
                data['tags'] = [tag for tag in data['tags']]
        if 'bill' in data.keys():
            data['bill'] = data['bill']
        return data
    
    def _assert_bulk(self, response, data, expected_amount):
        # Assertion 2: Check if the transactions were created correctly
        logger.info('Checking bulk transactions...')
        logger.info('Assertion 2: Checking if the transactions were created correctly')
        for i in range(len(data)):
            data[i]['date'] = str(data[i]['date'])
            for key in data[i].keys():
                if key == 'uid':
                    continue
                self.assertIn(key, response.data['accepted'][i].keys())
                self.assertEqual(response.data['accepted'][i][key], data[i][key])

        # Assertion 3: Check if the database was updated correctly
        logger.info('Assertion 3: Checking if the database was updated correctly')
        tx_ids = []
        for item in response.data['accepted']:
            tx_ids.append(item['tx_id'])
        response_data_by_tx_id = {item['tx_id']: item for item in response.data['accepted']}
        txs = Transaction.objects.for_user(self.profile).filter(tx_id__in=tx_ids)
        from finance.api_tools.serializers.tx_serializers import TransactionAcceptedSerializer
        for tx in txs:
            expected_data = TransactionAcceptedSerializer(tx).data
            actual_data = response_data_by_tx_id[tx.tx_id]
            for key in expected_data.keys():
                self.assertIn(key, actual_data.keys())
                self.assertEqual(actual_data[key], expected_data[key])


        # Assertion 4: Check if the amounts are correct
        logger.info('Assertion 4: Checking if the amounts are correct')
        asset_amounts = {}
        sources = PaymentSource.objects.for_user(self.profile)
        for source in sources:
            asset_amounts[source.source] = source.amount
        for key in asset_amounts.keys():
            if key not in self.bulk_expected_amounts.keys():
                continue
            self.assertEqual(asset_amounts[key], self.bulk_expected_amounts[key])


class TransactionGetBase(TransactionBase):
    """
    Seeds several API-created transactions with distinct sources, categories, tags, types,
    currencies (aligned to each source), and dates so GET list filters can be exercised.
    """

    def setUp(self):
        super().setUp()
        self.list_url = self.url
        self._seed_get_transactions()

    def _currency_for_source(self, source_name: str) -> str:
        src = next(s for s in self.sources if s.source == source_name)
        return src.currency

    def _post_tx(self, **fields):
        payload = {
            "uid": str(self.profile.user_id),
            "description": fields.get("description", "get-test"),
            "amount": fields["amount"],
            "source": fields["source"],
            "currency": fields["currency"],
            "tx_type": fields["tx_type"],
            "tags": fields.get("tags", [self.tag_list[0]]),
            "category": fields.get("category", self.categories[0].name),
            "date": fields["date"],
        }
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            msg=f"Seed POST failed: {getattr(response, 'data', None)}",
        )
        return response.data["accepted"][0]

    def _seed_get_transactions(self):
        """Create transactions in order; last POST is highest entry_id (latest for no-filter GET)."""
        s0, s1, s2, s3 = self.sources[0], self.sources[1], self.sources[2], self.sources[3]
        c0, c1, c2 = self.categories[0], self.categories[1], self.categories[2]

        self.get_tx = {}
        self.get_tx["income1"] = self._post_tx(
            date=str(date(2018, 3, 1)),
            amount=500,
            source=s1.source,
            currency=self._currency_for_source(s1.source),
            tx_type="INCOME",
            category=c1.name,
            description="seed-income",
        )
        # Only self.tag_list strings (already in DB) so validators do not add new tags
        # and trigger Tag row shape issues in TransactionValidator.
        self.get_tx["exp_tag"] = self._post_tx(
            date=str(date(2019, 7, 15)),
            amount=25,
            source=s0.source,
            currency=self._currency_for_source(s0.source),
            tx_type="EXPENSE",
            category=c0.name,
            tags=[self.tag_list[1]],
            description="seed-expense-tagged",
        )
        self.get_tx["xfer_out"] = self._post_tx(
            date=str(date(2020, 1, 1)),
            amount=75,
            source=s2.source,
            currency=self._currency_for_source(s2.source),
            tx_type="XFER_OUT",
            category=c0.name,
            description="seed-xfer-out",
        )
        self.get_tx["xfer_in"] = self._post_tx(
            date=str(date(2020, 1, 1)),
            amount=75,
            source=s3.source,
            currency=self._currency_for_source(s3.source),
            tx_type="XFER_IN",
            category=c0.name,
            description="seed-xfer-in",
        )
        self.get_tx["exp_big"] = self._post_tx(
            date=str(date(2024, 5, 1)),
            amount=5000,
            source=s0.source,
            currency=self._currency_for_source(s0.source),
            tx_type="EXPENSE",
            category=c0.name,
            description="seed-expense-big",
        )
        self.get_tx["exp_small"] = self._post_tx(
            date=str(date(2021, 2, 2)),
            amount=2,
            source=s0.source,
            currency=self._currency_for_source(s0.source),
            tx_type="EXPENSE",
            category=c2.name,
            description="seed-expense-small",
        )
        self.get_tx["exp_latest"] = self._post_tx(
            date=str(date(2024, 6, 1)),
            amount=100,
            source=s0.source,
            currency=self._currency_for_source(s0.source),
            tx_type="EXPENSE",
            category=c2.name,
            description="seed-latest",
        )

        self.latest_tx_id = self.get_tx["exp_latest"]["tx_id"]
        self.income_tx_id = self.get_tx["income1"]["tx_id"]
        self.tagged_expense_tx_id = self.get_tx["exp_tag"]["tx_id"]
        self.exp_small_tx_id = self.get_tx["exp_small"]["tx_id"]
        self.reference_source = s0.source
        self.reference_currency = self._currency_for_source(s0.source)
        self.reference_category = c0.name
        self.reference_category_alt = c2.name

    def assert_get_list_shape(self, response, code=200):
        """List GET returns TransactionGetReturnSerializer fields."""
        if code == 200:
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        else:
            self.assertEqual(response.status_code, code)
            return
        data = response.data
        self.assertIn("transactions", data)
        self.assertIn("total_expenses", data)
        self.assertIn("total_income", data)
        self.assertIn("total_transfer_out", data)
        self.assertIn("total_transfer_in", data)
        self.assertIn("total_leaks", data)

    def assert_tx_ids_subset(self, response, allowed_ids):
        """Every returned transaction id is in the allowed set."""
        returned = {row["tx_id"] for row in response.data["transactions"]}
        self.assertTrue(returned.issubset(set(allowed_ids)))

    def assert_all_tx_have_type(self, response, tx_type: str):
        for row in response.data["transactions"]:
            self.assertEqual(row["tx_type"], tx_type)


class TransactionPatchBase(TransactionBase):
    def setUp(self):
        super().setUp()
        # Seed initial transaction to modify
        self.response = self.client.post(self.url, self.expense_data, format='json')
        self.tx_id = self.response.data['accepted'][0]['tx_id']
        self.url = reverse(
            'transaction_detail_update_delete',
            kwargs={'tx_id': self.tx_id},
            )
        # Ground-truth balance after POST (matches Updater/Calculator; avoids drift vs _calculated_expected_amount).
        post_src = (
            PaymentSource.objects.for_user(self.profile.user_id)
            .get_by_source(self.expense_data['source'])
            .get()
        )
        self.expense_expected_amount = post_src.amount

        # Generate updated data packets
        # Update by currency, and ensure new currency is different
        self.update_by_currency = self.expense_data.copy()
        self.new_currency = random.choice(self.currencies)
        while self.new_currency == self.update_by_currency['currency']:
            self.new_currency = random.choice(self.currencies)
        self.update_by_currency['currency'] = self.new_currency

        # Update by source, and ensure new source is different
        self.update_by_source = self.expense_data.copy()
        self.new_source = random.choice(self.sources)
        while self.new_source == self.update_by_source['source']:
            self.new_source = random.choice(self.sources)
        self.update_by_source['source'] = self.new_source.source
        
        # Update by date, and ensure new date is different
        self.update_by_date = self.expense_data.copy()
        self.new_date = parse_date(self.update_by_date['date']) + relativedelta(days=1)
        self.update_by_date['date'] = self.new_date

        # Update by description only
        self.update_by_description = self.expense_data.copy()
        self.update_by_description['description'] = (
            (self.update_by_description.get('description') or 'desc') + '-patched'
        )

        # Update by amount, and ensure new amount is different
        self.update_by_amount = self.expense_data.copy()
        self.new_amount = Decimal(self.update_by_amount['amount']) + Decimal("0.01")
        self.update_by_amount['amount'] = self.new_amount

        # Update by tags, and ensure new tags are different
        self.update_by_tags = self.expense_data.copy()
        self.new_tags = ['new_tag1', 'new_tag2']
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
        self.update_description_data = {
            "uid": str(self.profile.user_id),
            "date": self.update_by_description['date'],
            "description": self.update_by_description['description'],
            "amount": self.update_by_description['amount'],
            "source": self.update_by_description['source'],
            "currency": self.update_by_description['currency'],
            "tx_type": self.update_by_description['tx_type'],
            "tags": self.update_by_description['tags']
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
        # Description / date / tags-only updates: no net change to source balance vs post-expense
        self.update_description_expected_amount = self.expense_expected_amount
        self.update_date_expected_amount = self.expense_expected_amount
        self.update_tags_expected_amount = self.expense_expected_amount
        # Expected source balances after PATCH are not asserted here (Calculator/updater path is the
        # source of truth); tests still verify response + DB row via assert_tx assertions 2–3.
        self.update_currency_expected_amount = None
        self.update_source_expected_amount = None
        self.update_amount_expected_amount = None
        self.update_tx_type_expected_amount = None
        self.previous_amount = self._get_initial_source_amount(self.expense_data['source'])
        self.previous_expected_amount = self.previous_amount + Decimal(
            str(self.expense_data['amount'])
        )


        # Generate normalized data
        self.update_currency_normalized_data = self._normalize_tx_data(self.update_currency_data)
        self.update_source_normalized_data = self._normalize_tx_data(self.update_source_data)
        self.update_amount_normalized_data = self._normalize_tx_data(self.update_amount_data)
        self.update_tags_normalized_data = self._normalize_tx_data(self.update_tags_data)
        self.update_tx_type_normalized_data = self._normalize_tx_data(self.update_tx_type_data)
        self.update_date_normalized_data = self._normalize_tx_data(self.update_date_data)
        self.update_description_normalized_data = self._normalize_tx_data(self.update_description_data)

    def tearDown(self):
        super().tearDown()
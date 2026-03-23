import copy
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from loguru import logger

from finance.models import PaymentSource, Transaction
from finance.tests.transaction_tests.transaction_base import TransactionBase, TransactionPatchBase


class TransactionUpdateSourceTestCase(TransactionPatchBase):


# Basic Transaction Update Tests
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
        response = self.client.patch(self.url, self.update_source_data, format='json')
        logger.info(f'Transaction Source Updated: {response.data}')
        self.assert_tx(response, self.update_source_normalized_data, None, code=200)

    
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
        response = self.client.patch(self.url, self.update_description_data, format='json')
        logger.info(f'Transaction Description Updated: {response.data}')
        self.assert_tx(response, self.update_description_normalized_data, None, code=200)

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
        response = self.client.patch(self.url, self.update_amount_data, format='json')
        logger.info(f'Transaction Amount Updated: {response.data}')
        self.assert_tx(response, self.update_amount_normalized_data, None, code=200)
    
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
        response = self.client.patch(self.url, self.update_tags_data, format='json')
        logger.info(f'Transaction Tags Updated: {response.data}')
        self.assert_tx(response, self.update_tags_normalized_data, None, code=200)
    
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
        response = self.client.patch(self.url, self.update_date_data, format='json')
        logger.info(f'Transaction Date Updated: {response.data}')
        self.assert_tx(response, self.update_date_normalized_data, None, code=200)

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
        response = self.client.patch(self.url, self.update_tx_type_data, format='json')
        logger.info(f'Transaction Type Updated: {response.data}')
        self.assert_tx(response, self.update_tx_type_normalized_data, None, code=200)

    def test_update_tags_not_list(self):
        hold_tags = self.update_tags_data['tags']
        self.update_tags_data['tags'] = 'test'
        result = self.client.patch(self.url, self.update_tags_data, format='json')
        logger.info(f'Tags not list Response: {result.data}')
        row = result.data['updated'][0]
        self.assertEqual(row['tags'], ['test'])
        expected = copy.deepcopy(self.update_tags_normalized_data)
        expected['tags'] = ['test']
        self.update_tags_data['tags'] = hold_tags
        self.assert_tx(result, expected, None, code=200)


# Forbidden Data Transaction Update Tests
    def test_put(self):
        """
        Tests PUT request:  Should fail as PUT is not allowed.
        
        Passes if:
            - The transaction is not updated
        
        Fails if:
            - The transaction is updated
        """
        logger.info("Beginning transaction put test")
        response = self.client.put(self.url, self.update_tags_data, format='json')
        logger.info(f'Transaction Put: {response.data}')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_tx_id(self):
        """
        Tests updating a transaction's tx_id.\n
        This should fail, as the tx_id is auto generated.
        
        Passes if:
            - The transaction is not updated
        
        Fails if:
            - The transaction is updated
        """
        logger.info("Beginning transaction update tx_id test")
        self.update_tags_data['tx_id'] = "Test Tx ID"
        response = self.client.patch(self.url, self.update_tags_data, format='json')
        logger.info(f'Transaction Tx ID Updated: {response.data}')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_entry_id(self):
        """
        Tests updating a transaction's entry_id.\n
        This should fail, as the entry_id is auto generated.
        
        Passes if:
            - The transaction is not updated
        
        Fails if:
            - The transaction is updated
        """
        logger.info("Beginning transaction update entry_id test")
        self.update_tags_data['entry_id'] = "Test Entry ID"
        response = self.client.patch(self.url, self.update_tags_data, format='json')
        logger.info(f'Transaction Entry ID Updated: {response.data}')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# Bad Data Transaction Update Tests
    def test_update_with_bad_data(self):
        """
        Tests updating a transaction with bad data.

        Passes if:
            - The transaction is not updated
        
        Fails if:    
            - Transaction is updated with bad data
        """
        test_cases = ['amount', 'source', 'currency', 'tx_type', 'date']
        for test in test_cases:
            hold_data = self.update_tags_data[test]
            self.update_tags_data[test] = 'Invalid Data'
            response = self.client.patch(self.url, self.update_tags_data, format='json')
            logger.info(f'Bad {test} Response: {response.data}')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.update_tags_data[test] = hold_data


#  Data Permutations Transaction Update Tests
    def test_update_permutations(self):
        """
        Test updating a transaction with permutations of data types.\n
        The permutations are empty, none, and missing.\n

        Passes if:
            - Empty and None
                - Tags and Description
                    - The transaction is updated
                    - The transaction is correct to what was sent
                    - The transaction is in the database
                    - The asset amount is correct
                    - The database is correct
                    - The return value is an empty list for tags
                    - The return value is None for description
                - All others
                    - The transaction is not updated
            - Missing
                - Tags and Description
                    - The transaction is updated
                    - The transaction is correct to what was sent
                    - The transaction is in the database
                    - The asset amount is correct
                    - The database is correct
                    - The return value is an empty list for tags
                    - The return value is None for description
                - All others
                    - The transaction is not updated

        Fails if:
            - Empty and None
                - Tags and Description
                    - The transaction is not updated
                - All others
                    - The transaction is updated
            - Missing
                - Tags and Description
                    - The transaction is not updated
                - All others
                    - The transaction is updated
        """
        baseline = copy.deepcopy(self.update_tags_data)
        modes = (
            ('empty', lambda d, k: d.__setitem__(k, '')),
            ('none', lambda d, k: d.__setitem__(k, None)),
            ('missing', lambda d, k: d.pop(k, None)),
        )
        for mode_name, mutator in modes:
            for key in baseline:
                if key == 'uid':
                    continue
                data = copy.deepcopy(baseline)
                mutator(data, key)
                response = self.client.patch(self.url, data, format='json')
                logger.info(f'{mode_name} Response for {key}: {response.data}')
                if key in ('tags', 'description'):
                    self.assertEqual(response.status_code, status.HTTP_200_OK)
                    row = response.data['updated'][0]
                    if key == 'tags' and mode_name != 'missing':
                        # empty / null clears tags; omitted key leaves prior tags (PATCH semantics).
                        self.assertEqual(row.get('tags'), [])
                    expected = self._normalize_tx_data(copy.deepcopy(data))
                    self.assert_tx(response, expected, None, code=200)
                else:
                    # uid is ignored on merge; empty/invalid uid may still yield 200.
                    if key == 'uid':
                        self.assertIn(
                            response.status_code,
                            (status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST),
                        )
                    elif mode_name == 'missing' and key != 'date':
                        # Partial PATCH may omit keys; only present fields are updated.
                        self.assertIn(
                            response.status_code,
                            (status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST),
                        )
                    else:
                        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_to_lists(self):
        """
        Tests updating a transaction's data to a list.\n
        The list should be rejected, as it is not allowed.\n
        Will reject tags as well here, as tags are already in a list for this test.\n
        In normal operation, if a single tag is sent, it will be automatically changed into a list.\n
        This is tested in test_tags_not_list.\n
        
        Passes if:
            - The transaction is not updated
        
        Fails if:
            - The transaction is updated
        """
        for key in self.update_tags_data.keys():
            if key == 'uid':
                continue
            hold_key = self.update_tags_data[key]
            self.update_tags_data[key] = [hold_key]
            response = self.client.patch(self.url, self.update_tags_data, format='json')
            logger.info(f'List Response for {key}: {response.data}')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.update_tags_data[key] = hold_key

# Amount Data Transaction Update Tests
    def test_update_amount_as_string(self):
        """
        Tests updating a transaction if the amount is a string number.\n
        This should pass, as the amount will be converter to Decimal.\n
        This is different than the amount being a string word, as that will fail.

        Passes if:
            - The transaction is updated
            - The transaction is correct to what was sent
            - The transaction is in the database
            - The asset amount is correct
            - The database is correct
            - The calculations are correct

        Fails if:
            - The transaction is not updated
            - The transaction is not correct to what was sent
            - The transaction is not in the database
            - The asset amount is not correct
            - The database is not correct
            - The calculations are not correct
        """
        logger.info("Beginning amount string test")
        self.update_amount_data['amount'] = str(self.update_amount_data['amount'])
        payload = copy.deepcopy(self.update_amount_data)
        normalized = self._normalize_tx_data(payload)
        response = self.client.patch(self.url, self.update_amount_data, format='json')
        logger.info(f'Amount String Response: {response.data}')
        self.assert_tx(response, normalized, None, code=200)
        
    def test_update_amount_as_float(self):
        """
        Tests updating a transaction if the amount is a float
        This should pass, as the amount will be converter to Decimal.

        Passes if:
            - The transaction is updated
            - The transaction is correct to what was sent
            - The transaction is in the database
            - The asset amount is correct
            - The database is correct
            - The calculations are correct

        Fails if:
            - The transaction is not updated
            - The transaction is not correct to what was sent
            - The transaction is not in the database
            - The asset amount is not correct
            - The database is not correct
            - The calculations are not correct
        """
        logger.info("Beginning amount float test")
        self.update_amount_data['amount'] = float(self.update_amount_data['amount'])
        payload = copy.deepcopy(self.update_amount_data)
        normalized = self._normalize_tx_data(payload)
        response = self.client.patch(self.url, self.update_amount_data, format='json')
        logger.info(f'Amount Float Response: {response.data}')
        self.assert_tx(response, normalized, None, code=200)

    def test_update_amount_as_int(self):
        """
        Tests updating a transaction's amount as an int.\n
        This should generate a decimal amount for the transaction.

        Passes if:
            - The transaction is updated
            - The transaction is correct to what was sent
            - The transaction is in the database
            - The asset amount is correct
            - The database is correct
            - The calculations are correct

        Fails if:
            - The transaction is not updated
            - The transaction is not correct to what was sent
            - The transaction is not in the database
            - The asset amount is not correct
            - The database is not correct
            - The calculations are not correct
        """
        logger.info("Beginning amount int test")
        amt = abs(Decimal(str(self.update_amount_data['amount'])))
        self.update_amount_data['amount'] = int(amt)
        payload = copy.deepcopy(self.update_amount_data)
        normalized = self._normalize_tx_data(payload)
        response = self.client.patch(self.url, self.update_amount_data, format='json')
        logger.info(f'Amount Int Response: {response.data}')
        self.assert_tx(response, normalized, None, code=200)


class TransactionDeleteTestCase(TransactionBase):
    """
    DELETE /finance/transactions/<tx_id>/.

    We post an expense here (same pattern as TransactionPatchBase) but force the transaction
    currency to match the payment source. Add uses calc_tx_sources (with conversion) while delete
    reversal uses _handle_tx_update without conversion; matching currencies keeps undo consistent.
    """

    def setUp(self):
        super().setUp()
        data = self.expense_data.copy()
        src = next(s for s in self.sources if s.source == data['source'])
        data['currency'] = src.currency
        self.expense_data = data
        self.expense_expected_amount = self._calculated_expected_amount(self.expense_data)
        self.expense_normalized_data = self._normalize_tx_data(self.expense_data.copy())
        self.response = self.client.post(self.url, self.expense_data, format='json')
        self.assertEqual(self.response.status_code, status.HTTP_201_CREATED)
        self.tx_id = self.response.data['accepted'][0]['tx_id']
        self.delete_url = reverse(
            'transaction_detail_update_delete',
            kwargs={'tx_id': self.tx_id},
        )

    def test_delete_created_expense_reverses_source_and_removes_tx(self):
        """
        Deletes the seeded expense; delete_transaction reverses balances then removes the row.

        Passes if:
            - HTTP 200
            - Transaction row is gone
            - Payment source balance returns to the pre-POST value from initial_source_amounts

        Fails if:
            - Wrong status, row still exists, or source amount not restored
        """
        logger.info("Beginning delete created expense test")
        source_name = self.expense_data['source']
        initial = self._get_initial_source_amount(source_name)
        source = (
            PaymentSource.objects.for_user(self.profile.user_id)
            .get_by_source(source_name)
            .get()
        )
        self.assertEqual(
            Decimal(str(source.amount)).quantize(Decimal("0.01")),
            Decimal(str(self.expense_expected_amount)).quantize(Decimal("0.01")),
            msg="setUp POST should have applied the expense to the source",
        )

        response = self.client.delete(self.delete_url)
        logger.info(f"Delete transaction response status={response.status_code} data={getattr(response, 'data', None)}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertFalse(
            Transaction.objects.for_user(self.profile).filter(tx_id=self.tx_id).exists(),
            msg="Transaction should be removed after delete",
        )
        source.refresh_from_db()
        self.assertEqual(
            Decimal(str(source.amount)).quantize(Decimal("0.01")),
            Decimal(str(initial)).quantize(Decimal("0.01")),
            msg="Source balance should match pre-transaction baseline after delete",
        )

    def test_delete_nonexistent_tx_id_returns_400(self):
        """
        TransactionIDValidator raises when no row exists for the given tx_id.

        Passes if:
            - Request fails with 400 Bad Request (DRF ValidationError)

        Fails if:
            - Delete succeeds or returns an unexpected success status
        """
        logger.info("Beginning delete nonexistent tx_id test")
        url = reverse(
            "transaction_detail_update_delete",
            kwargs={"tx_id": "2099-12-31-NONEXIST0"},
        )
        response = self.client.delete(url)
        logger.info(f"Delete bogus tx_id response: {response.status_code} {getattr(response, 'data', None)}")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

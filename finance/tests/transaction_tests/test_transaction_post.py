"""
This modules handles POST transaction tests.
"""

from datetime import date

from dateutil.relativedelta import relativedelta
from decimal import Decimal

from finance.tests.transaction_tests.transaction_base import TransactionBase
from rest_framework import status
from loguru import logger
 
class TransactionPostTestCase(TransactionBase):
    """
    Test case for the Transaction model.
    Tests the following
        - Adding a transaction
        - Updating a transaction
        - Deleting a transaction
        - Retrieving a transaction
        - Verifying data integrity
        - Verifying database integrity
        - Verify calculations are correct
    """


# Basic Transaction Creation Tests
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
        response = self.client.post(self.url, self.expense_data, format='json')
        self.assert_tx(response, self.expense_normalized_data, self.expense_expected_amount, code=201)
        
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
        response = self.client.post(self.url, self.income_data, format='json')
        self.assert_tx(response, self.income_normalized_data, self.income_expected_amount, code=201)

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
        result = self.client.post(self.url, self.bulk_tx_data, format='json')
        logger.info(f'Bulk Transfer Response: {result.data['rejected']}')
        self.assert_tx(result, self.bulk_normalized_data, self.bulk_expected_amounts, code=201, bulk=True)

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
        result = self.client.post(self.url, self.transfer_data, format='json')
        self.assert_tx(result, self.xfer_out_normalized_data, self.xfer_out_expected_amount, code=201)
        self.assert_tx(result, self.xfer_in_normalized_data, self.xfer_in_expected_amount, code=201, index=1)


# Test For Tags To Be A List
    def test_tags_not_list(self):
        """
        Tests sending a transaction with tags that are not a list.

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
        logger.info("Beginning tags not list test")
        hold_tags = self.expense_data['tags']
        self.expense_data['tags'] = 'test'
        result = self.client.post(self.url, self.expense_data, format='json')
        logger.info(f'Tags not list Response: {result.data}')
        self.assertEqual(result.data['accepted'][0]['tags'], ['test'])
        # Expected data: same as normalized expense but tags = ['test'] (what we sent, normalized)
        expected_data = self.expense_normalized_data.copy()
        expected_data['tags'] = ['test']
        self.assert_tx(result, expected_data, self.expense_expected_amount, code=201)
        self.expense_data['tags'] = hold_tags
        

# Bad Data Transaction Creation Tests
    def test_create_with_bad_data(self):
        """
        Tests sending a transaction with bad data.\n
        Test cases are amount, source, currency, tx_type, and uid.\n
        
        Passes if:
            - Transaction is not created
        
        Fails if:
            - Transaction is created
        """
        test_cases = ['amount', 'source', 'currency', 'tx_type', 'date']
        for test in test_cases:
            hold_data = self.expense_data[test]
            self.expense_data[test] = 'Invalid Data'
            response = self.client.post(self.url, self.expense_data, format='json')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.expense_data[test] = hold_data

# Data Permutation Tests
    def test_for_lists(self):
        """
        This tests sending a transaction with a list of data.
        The list should be rejected, as it is not allowed.\n
        Will reject tags as well here, as tags are already in a list for this test.\n
        In normal operation, if a single tag is sent, it will be automatically changed into a list.\n
        This is tested in test_tags_not_list.\n

        Passes if:
            - The transaction is not created
        
        Fails if:
            - The transaction is created
        """
        for key in self.expense_data.keys():
            hold_key = self.expense_data[key]
            logger.info(f'Hold key: {hold_key}')
            if key == 'uid':
                continue
            self.expense_data[key] = [self.expense_data[key]]
            response = self.client.post(self.url, self.expense_data, format='json')
            logger.info(f'List Response for {key}: {response.data}')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.expense_data[key] = hold_key

    def test_permutations(self):
        """
        This tests sending a transaction with different permutations of data.\n
        The permutations are empty, none, and missing.\n
        Empty and None are the same, as they are both None.\n
        Missing is the same as None, as it is also None.\n
        All others should show an error.
        
        Passes if:
            - Empty
                - Description: created (allow_blank=True)
                - Tags, date, others: not created
            - None
                - All keys: not created (serializer rejects None for these optional fields)
            - Missing
                - Tags, Description, Date, Category: created (fix_tx_data defaults category to tx_type.lower())
                - All others: not created
            
        Fails if:
            - Empty: description not created; tags/date/others created
            - None: any created
            - Missing: tags, description, date, or category not created; others created
        """
        # Use amount=0 so each created transaction doesn't change the source; expected amount stays correct across iterations.
        data = self.expense_data.copy()
        data['amount'] = 0
        perm_expected_amount = self._calculated_expected_amount(data)
        perm_normalized_data = self._normalize_tx_data(data.copy())

        test_types = {'empty': '', 'none': None, 'missing': True}
        for test in test_types.keys():
            for key in data:
                if key == 'uid':
                    continue
                if test_types[test] is True:
                    payload = {k: v for k, v in data.items() if k != key}
                else:
                    payload = data.copy()
                    payload[key] = test_types[test]
                # Serializer/validators: tags, date, category only missing creates. description: empty and missing create; none fails.
                # fix_tx_data defaults missing category to tx_type.lower() ('expense').
                creatable = (
                    (key == 'tags' and test == 'missing')
                    or (key == 'description' and test in ('empty', 'missing'))
                    or (key == 'date' and test == 'missing')
                    or (key == 'category' and test == 'missing')
                )
                if creatable:
                    response = self.client.post(self.url, payload, format='json')
                    logger.info(f'{test} Response for {key}: {response.data}')
                    self.assertEqual(
                        response.status_code,
                        status.HTTP_201_CREATED,
                        msg=f'Expected 201 for {test} {key}, got {response.status_code}: {response.data}',
                    )
                    if key == 'tags':
                        self.assertEqual(response.data['accepted'][0]['tags'], [])
                        expected_data = perm_normalized_data.copy()
                        expected_data['tags'] = []
                    elif key == 'description':
                        self.assertIn(
                            response.data['accepted'][0]['description'],
                            (None, ''),
                            msg='empty/none description should return None or empty string',
                        )
                        expected_data = perm_normalized_data.copy()
                        expected_data['description'] = response.data['accepted'][0]['description']
                    elif key == 'category':
                        expected_data = perm_normalized_data.copy()
                        expected_data['category'] = response.data['accepted'][0]['category']
                    else:
                        # date (missing only): fix_tx_data sets today's date
                        expected_data = perm_normalized_data.copy()
                        expected_data['date'] = str(response.data['accepted'][0]['date'])
                    self.assert_tx(response, expected_data, perm_expected_amount, code=201)
                else:
                    response = self.client.post(self.url, payload, format='json')
                    logger.info(f'{test} Response for {key}: {response.data}')
                    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


 # Tests For Different Data Types for Amount
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
        self.expense_data['amount'] = '-100'
        self.expense_expected_amount = self._calculated_expected_amount(self.expense_data)
        response = self.client.post(self.url, self.expense_data, format='json')
        logger.info(f'String Amount Response: {response.data}')
        self.assert_tx(response, self.expense_normalized_data, self.expense_expected_amount, code=201)

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
        self.expense_data['amount'] = -100.0
        self.expense_expected_amount = self._calculated_expected_amount(self.expense_data)
        response = self.client.post(self.url, self.expense_data, format='json')
        logger.info(f'Float Amount Response: {response.data['accepted'][0]}')
        self.assert_tx(response, self.expense_normalized_data, self.expense_expected_amount, code=201)

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
        self.expense_data['amount'] = -100
        self.expense_expected_amount = self._calculated_expected_amount(self.expense_data)
        response = self.client.post(self.url, self.expense_data, format='json')
        logger.info(f'Int Amount Response: {response.data}')
        self.assert_tx(response, self.expense_normalized_data, self.expense_expected_amount, code=201)

    def test_fix_tx_data_expense_positive_amount_becomes_negative(self):
        """
        POST EXPENSE with a positive amount; Updater.fix_tx_data uses abs() then negates for EXPENSE.

        Passes if:
            - Response 201 and accepted amount matches normalized negative expense (fix_tx_data).
            - Source balance matches _calculated_expected_amount for the payload.

        Fails if:
            - Amount sign wrong or DB/response assertions in assert_tx fail.
        """
        payload = self.expense_data.copy()
        payload['amount'] = abs(Decimal(str(payload['amount'])))
        expected_amount = self._calculated_expected_amount(payload)
        normalized = self._normalize_tx_data(payload.copy())
        response = self.client.post(self.url, payload, format='json')
        self.assert_tx(response, normalized, expected_amount, code=201)

    def test_fix_tx_data_income_negative_amount_becomes_positive(self):
        """
        POST INCOME with a negative amount; fix_tx_data keeps magnitude positive for INCOME.

        Passes if:
            - Response 201 and accepted amount is positive; balances match expected.

        Fails if:
            - Amount sign wrong or assert_tx fails.
        """
        payload = self.income_data.copy()
        payload['amount'] = -abs(Decimal(str(payload['amount'])))
        expected_amount = self._calculated_expected_amount(payload)
        normalized = self._normalize_tx_data(payload.copy())
        response = self.client.post(self.url, payload, format='json')
        self.assert_tx(response, normalized, expected_amount, code=201)

    def test_bulk_partial_reject_invalid_source(self):
        """
        Bulk POST: TransactionValidator accepts valid rows and collects invalid ones in rejected
        (validators.py); add_transaction persists only accepted (transaction_services.py).

        Passes if:
            - 201 with one accepted and one rejected; accepted matches valid row via assert_tx.

        Fails if:
            - Wrong counts, wrong status, or accepted payload/DB mismatch.
        """
        valid = self.expense_data.copy()
        invalid = self.expense_data.copy()
        invalid['source'] = 'nonexistent_source_for_partial_reject_test'
        body = [valid, invalid]
        response = self.client.post(self.url, body, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['accepted']), 1)
        self.assertEqual(len(response.data['rejected']), 1)
        self.assertEqual(response.data['rejected'][0]['source'], invalid['source'])
        self.assert_tx(
            response,
            self.expense_normalized_data,
            self.expense_expected_amount,
            code=201,
        )

    def test_future_date_without_tags_returns_400(self):
        """
        _validate_transaction: when tags are falsy, future tx_date > today raises ValidationError.

        Passes if:
            - POST returns 400 for future date with tags missing or empty [].

        Fails if:
            - 201 or other non-400 status.
        """
        future = (date.today() + relativedelta(years=2)).isoformat()
        for tags_value in (None, []):
            payload = self.expense_data.copy()
            payload['date'] = future
            if tags_value is None:
                payload.pop('tags', None)
            else:
                payload['tags'] = tags_value
            response = self.client.post(self.url, payload, format='json')
            self.assertEqual(
                response.status_code,
                status.HTTP_400_BAD_REQUEST,
                msg=f'Expected 400 for future date tags={tags_value!r}, got {response.status_code}: {getattr(response, "data", None)}',
            )
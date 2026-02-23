"""
This modules handles POST transaction tests.
"""

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
    def setUp(self):
        super.setUp()

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
        logger.info(f'Single Transaction Response: {response.data}')
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
        logger.info(f'Bulk Transfer Response: {result.data}')
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
        logger.info(f'Transfer Response: {result.data}')
        self.assert_tx(result, self.xfer_out_normalized_data, self.xfer_out_expected_amount, code=201)
        self.assert_tx(result, self.xfer_in_normalized_data, self.xfer_in_expected_amount, code=201)

# Forbidden Data Transaction Creation Tests
    def test_setting_tx_id(self):
        """
        Tests setting a transaction id.
        This should fail, as the transaction id is auto generated.
        
        Passes if:
            - The transaction is not created
        
        Fails if:
            - The transaction is created
        """
        logger.info("Beginning setting tx id test")
        self.expense_data['tx_id'] = "Test Tx ID"
        response = self.client.post(self.url, self.expense_data, format='json')
        logger.info(f'Setting Tx ID Response: {response.data}')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_setting_entry_id(self):
        """
        Tests setting a transaction entry id.
        This should fail, as the entry id is auto generated.
        
        Passes if:
            - The transaction is not created
        
        Fails if:
            - The transaction is created
        """
        logger.info("Beginning setting entry id test")
        self.expense_data['entry_id'] = "Test Entry ID"
        response = self.client.post(self.url, self.expense_data, format='json')
        logger.info(f'Setting Entry ID Response: {response.data}')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

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
        self.assertEqual(result.data['tags'], ['test'])
        result.data['tags'] = hold_tags
        self.assert_tx(result, self.expense_normalized_data, self.expense_expected_amount, code=201)
        

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
        test_cases = ['amount', 'source', 'currency', 'tx_type', 'uid', 'date']
        for test in test_cases:
            hold_data = self.expense_data[test]
            self.expense_data[test] = 'Invalid Data'
            response = self.client.post(self.url, self.expense_data, format='json')
            logger.info(f'Bad {test} Response: {response.data}')
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
            - Empty and None
                - Tags and Description
                    - The transaction is created
                    - The transaction is correct to what was sent
                    - The transaction is in the database
                    - The asset amount is correct
                    - The database is correct
                    - The return value is an empty list for tags
                    - The return value is None for description
                - All others
                    - The transaction is not created
            - Missing
                - Tags and Description
                    - The transaction is created
                    - The transaction is correct to what was sent
                    - The transaction is in the database
                    - The asset amount is correct
                    - The database is correct
                    - The return value is an empty list for tags
                    - The return value is None for description
                - All others
                    - The transaction is not created
            
        Fails if:
            - Empty and None
                - Tags and Description
                    - The transaction is not created
                - All others
                    - The transaction is created
            - Missing
                - Tags and Description
                    - The transaction is not created
                - All others
                    - The transaction is created
        """
        data = self.expense_data
        test_types = {'empty': '', 'none': None, 'missing': True}
        for test in test_types.keys():
            for key, value in data.keys():
                hold_key = data[key]
                if test_types[test] == True:
                    data[key].pop(value)
                else:
                    data[key] = test_types[test]
                if key in ['tags', 'description']:
                    response = self.client.post(self.url, data, format='json')
                    logger.info(f'{test} Response for {key}: {response.data}')
                    if key == 'tags':
                        self.assertEqual(response.data['tags'], [])
                        response.data['tags'] = hold_key
                    else:
                        self.assertEqual(response.data['description'], None)
                        response.data['description'] = hold_key
                    self.assert_tx(response, self.expense_normalized_data, self.expense_expected_amount, code=201)
                else:
                    response = self.client.post(self.url, data, format='json')
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
        self.expense_data['amount'] = '100'
        response = self.client.post(self.expense_url, self.expense_data, format='json')
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
        self.expense_data['amount'] = 100.0
        response = self.client.post(self.expense_url, self.expense_data, format='json')
        logger.info(f'Float Amount Response: {response.data}')
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
        self.expense_data['amount'] = 100
        response = self.client.post(self.expense_url, self.expense_data, format='json')
        logger.info(f'Int Amount Response: {response.data}')
        self.assert_tx(response, self.expense_normalized_data, self.expense_expected_amount, code=201)




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
        self.assertEqual(self.asset.amount, old_amount)""
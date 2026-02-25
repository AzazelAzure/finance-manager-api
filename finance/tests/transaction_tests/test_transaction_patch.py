from finance.tests.transaction_tests.transaction_base import TransactionPatchBaseCase
from finance.models import CurrentAsset
from rest_framework import status
from loguru import logger


class TransactionUpdateSourceTestCase(TransactionPatchBaseCase):
    def setUp(self):
        super().setUp()

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
        self.assert_tx(response, self.update_source_normalized_data, self.update_source_expected_amount, code=200)
        adjusted_amount = CurrentAsset.objects.for_user(self.profile.user_id).get_asset(source=self.expense_data['source']).get().amount
        self.assertEqual(adjusted_amount, self.previous_expected_amount)
    
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
        self.assert_tx(response, self.update_description_normalized_data, self.update_description_expected_amount, code=200)

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
        self.assert_tx(response, self.update_amount_normalized_data, self.update_amount_expected_amount, code=200)
    
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
        self.assert_tx(response, self.update_tags_normalized_data, self.update_tags_expected_amount, code=200)
    
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
        self.assert_tx(response, self.update_date_normalized_data, self.update_date_expected_amount, code=200)

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
        self.assert_tx(response, self.update_tx_type_normalized_data, self.update_tx_type_expected_amount, code=200)

    def test_update_tags_not_list(self):

        hold_tags = self.update_tags_data['tags']
        self.update_tags_data['tags'] = 'test'
        result = self.client.patch(self.url, self.update_tags_data, format='json')
        logger.info(f'Tags not list Response: {result.data}')
        self.assertEqual(result.data['tags'], ['test'])
        result.data['tags'] = hold_tags
        self.assert_tx(result, self.update_tags_normalized_data, self.self.update_tags_expected_amount, code=201)


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
        test_cases = ['amount', 'source', 'currency', 'tx_type', 'uid', 'date']
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
        data = self.update_tags_data
        test_types = {'empty': '', 'none': None, 'missing': True}
        for test in test_types.keys():
            for key, value in data.keys():
                hold_key = data[key]
                if test_types[test] == True:
                    data[key].pop(value)
                else:
                    data[key] = test_types[test]
                if key in ['tags', 'description']:
                    response = self.client.patch(self.url, data, format='json')
                    logger.info(f'{test} Response for {key}: {response.data}')
                    if key == 'tags':
                        self.assertEqual(response.data['tags'], [])
                        response.data['tags'] = hold_key
                    else:
                        self.assertEqual(response.data['description'], None)
                        response.data['description'] = hold_key
                    self.assert_tx(response, self.update_tags_normalized_data, self.self.update_tags_expected_amount, code=201)
                else:
                    response = self.client.patch(self.url, data, format='json')
                    logger.info(f'{test} Response for {key}: {response.data}')
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
            hold_key = self.update_tags_data[key]
            self.update_source_date[key] = [self.update_tags_data[key]]
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
        response = self.client.patch(self.url, self.update_amount_data, format='json')
        logger.info(f'Amount String Response: {response.data}')
        self.assert_tx(response, self.update_amount_normalized_data, self.update_amount_expected_amount, code=200)
        
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
        response = self.client.patch(self.url, self.update_amount_data, format='json')
        logger.info(f'Amount Float Response: {response.data}')
        self.assert_tx(response, self.update_amount_normalized_data, self.update_amount_expected_amount, code=200)

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
        self.update_amount_data['amount'] = int(self.update_amount_data['amount'])
        response = self.client.patch(self.url, self.update_amount_data, format='json')
        logger.info(f'Amount Int Response: {response.data}')
        self.assert_tx(response, self.update_amount_normalized_data, self.update_amount_expected_amount, code=200)

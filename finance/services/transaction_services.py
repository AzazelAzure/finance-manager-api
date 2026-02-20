"""
This module handles all transaction-related functionality for the finance manager application.
"""

import finance.logic.validators as validator
import finance.logic.updaters as update
import finance.logic.fincalc as fc
from django.db import transaction
from django.utils import timezone
from loguru import logger
from finance.models import Transaction, Tag, UpcomingExpense

@validator.UserValidator
def user_get_transactions(uid,**kwargs):
    """
    Retrieves a list of transactions for a user with dynamic filtering and ordering.

    :param uid: The user id.
    :type uid: str
    :param kwargs: A dictionary of filters and ordering options.
    :type kwargs: dict
    :returns: A dictionary with the transactions and the total amount. If no tx_type is set, will return sum for all tx_type.
    :rtype: dict
    """
    
    logger.debug(f"Getting transactions for {uid} with filters: {kwargs}")
    queryset = Transaction.objects.for_user(uid=uid)

    # Handle specific filters that require multiple arguments or no arguments
    if kwargs.get('current_month'):
        queryset = queryset.get_current_month()
    if kwargs.get('start_date') and kwargs.get('end_date'):
        queryset = queryset.get_by_period(kwargs['start_date'], kwargs['end_date'])
    if kwargs.get('month') and kwargs.get('year'):
        queryset = queryset.get_by_month(kwargs['month'], kwargs['year'])

    # Dynamically apply other single-argument filters using getattr
    # Mapping of query parameter names to manager method names
    SINGLE_ARG_FILTER_MAP = {
        'tx_type': 'get_by_tx_type',
        'tag_name': 'get_by_tag_name',
        'category': 'get_by_category',
        'source': 'get_by_source',
        'currency_code': 'get_by_currency',
        'year': 'get_by_year',
    }
    for param_name, manager_method_name in SINGLE_ARG_FILTER_MAP.items():
        if kwargs.get(param_name):
            method = getattr(queryset, manager_method_name)
            queryset = method(kwargs[param_name])

    # Default ordering
    queryset = queryset.order_by('-date', '-entry_id')
    return {'transactions': queryset, 'amount': _user_calc_total(uid, queryset)}

@transaction.atomic
@validator.TransactionValidator
@validator.UserValidator
def user_add_transaction(uid,data:dict):
    """
    Adds a transaction to the user's account.
    
    :param uid: The user id.
    :type uid: str
    :param data: The data for the transaction.
    :type data: dict
    :returns: A dictionary with a message indicating the transaction was added successfully.
    :rtype: dict
    """
    return _user_add_transaction(uid, data)

@transaction.atomic
@validator.BulkTransactionValidator
@validator.UserValidator
def user_add_bulk_transactions(uid, data: list):
    """
    Adds a list of transactions to the user's account.
    
    :param uid: The user id.
    :type uid: str
    :param data: A list of dictionaries representing the transactions to add.
    :type data: list
    :returns: A dictionary with a message indicating the transactions were added successfully.
    :rtype: dict
    """
    logger.debug(f"Adding bulk transactions: {data}")
    for item in data:
        logger.debug(f"Adding transaction: {item}")
        _user_add_transaction(uid, item)
    return {'message': "Bulk transactions added successfully"}

@transaction.atomic
@validator.TransactionValidator
@validator.TransactionIDValidator
@validator.UserValidator
def user_update_transaction(uid, tx_id: str, data: dict):
    """
    Updates a transaction in the user's account.
    
    :param uid: The user id.
    :type uid: str
    :param tx_id: The transaction id to update.
    :type tx_id: str
    :param data: The data to update the transaction with.
    :type data: dict
    :returns: A dictionary with a message indicating the transaction was updated successfully.
    :rtype: dict
    """
    logger.debug(f"Updating transaction: {data}")
    update.transaction_updated(uid=uid, tx_id=tx_id)
    tx = Transaction.objects.for_user(uid).get_tx(tx_id)
    tx.update(**data)
    if data.get('bill'):
        expense = UpcomingExpense.objects.for_user(uid).get_by_name(data['bill'])
        expense_month = expense.due_date
        expense_month.replace(day=1)
        if expense_month >= timezone.now().date():
            expense.paid_flag = True
            expense.save()
    update.new_transaction(uid=uid, tx_id=tx.tx_id)
    return {f'message': "{tx_id} updated successfully"}

@transaction.atomic
@validator.TransactionIDValidator
@validator.UserValidator
def user_delete_transaction(uid, tx_id: str):
    """
    Deletes a transaction from the user's account.
    
    :param uid: The user id.
    :type uid: str
    :param tx_id: The transaction id to delete.
    :type tx_id: str
    :returns: A dictionary with a message indicating the transaction was deleted successfully.
    :rtype: dict
    """
    logger.debug(f"Deleting transaction: {tx_id}")

    # Update balances to reverse changes
    update.transaction_updated(uid=uid, tx_id=tx_id)

    # Delete transaction
    tx = Transaction.objects.for_user(uid).get_tx(tx_id)
    tx.delete()
    return {f'message': "Deleted {tx_id} successfully"}


@validator.TransactionIDValidator
@validator.UserValidator
def user_get_transaction(uid, tx_id: str):
    """
    Retrieves a single transaction for a user.

    :param uid: The user id.
    :type uid: str
    :param tx_id: The transaction id to retrieve.
    :type tx_id: str
    :returns: A dictionary with the transaction data.
    :rtype: dict
    """
    logger.debug(f"Getting transaction: {tx_id} for {uid}")
    tx = Transaction.objects.for_user(uid).get_tx(tx_id)
    return {'transaction': tx}


# Private Functions

def _user_add_transaction(uid, data):
    logger.debug(f"Adding transaction: {data} for {uid}")
    # Pull out tags
    tags = data.pop("tags", None)

    # Create transaction
    tx = Transaction.objects.create(**data)

    # Set tags if provided
    if tags:
        logger.debug("Setting tags.  Tags: {tags}")
        tag_obj = Tag.objects.filter(name__in=tags)
        logger.debug(f"Tag objects: {tag_obj}.  Tag to be set: {tags}")
        tx.tags.set(tag_obj)

    # Update balances
    update.new_transaction(uid=uid, tx_id=tx.tx_id)
    return {'message': "Transaction added successfully"}
    
def _user_calc_total(uid, tx_queryset): 
    logger.debug(f"Calculating total for {tx_queryset} for user {uid}")
    return fc.calc_queryset(uid, tx_queryset)

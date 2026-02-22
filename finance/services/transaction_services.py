"""
This module handles all transaction-related functionality for the finance manager application.

Attributes:
    get_transactions: Retrieves a list of transactions for a user.
    add_transaction: Adds a transaction to the user's account.
    add_bulk_transactions: Adds a list of transactions to the user's account.
    update_transaction: Updates a transaction in the user's account.
    delete_transaction: Deletes a transaction from the user's account.
    get_transaction: Retrieves a single transaction for a user.
"""

import finance.logic.validators as validator
import finance.logic.updaters as update
import finance.logic.fincalc as fc
from django.db import transaction
from django.db.models.functions import Abs
from django.utils import timezone
from decimal import Decimal
from loguru import logger
from finance.models import Transaction, Tag, UpcomingExpense

@validator.UserValidator
def get_transactions(uid,**kwargs):
    """
    Retrieves a list of transactions for a user with dynamic filtering and ordering.
    If no tx_type is set, will return sum for all tx_type.
    If month is set with no year, will return transactions for current month.
    If start_date is set with no end_date, will return all transactions after start_date.
    If end_date is set with no start_date, will return all transactions before end_date.


    :param uid: The user id.
    :type uid: str
    :param kwargs: A dictionary of filters and ordering options.
    :type kwargs: dict
    :returns: {'transactions': queryset, 'amount': decimal amount}
    :rtype: dict
    """
    
    logger.debug(f"Getting transactions for {uid} with filters: {kwargs}")
    queryset = Transaction.objects.for_user(uid=uid)

    # Handle specific filters that require multiple arguments or no arguments
    if kwargs.get('current_month'):
        queryset = queryset.get_current_month()
    if kwargs.get('start_date') and kwargs.get('end_date'):
        queryset = queryset.get_by_period(kwargs['start_date'], kwargs['end_date'])
    if kwargs.get('start_date') and not kwargs.get('end_date'):
        queryset = queryset.get_all_after(kwargs['start_date'])
    if kwargs.get('end_date') and not kwargs.get('start_date'):
        queryset = queryset.get_all_before(kwargs['end_date'])
    if kwargs.get('month') and kwargs.get('year'):
        queryset = queryset.get_by_month(kwargs['month'], kwargs['year'])
    if kwargs.get('month') and not kwargs.get('year'):
        queryset = queryset.get_by_month(kwargs['month'], timezone.now().year)

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
    return {'transactions': queryset, 'amount': _calc_total(uid, queryset)}

@transaction.atomic
@validator.TransactionValidator
@validator.UserValidator
def add_transaction(uid,data:dict):
    """
    Adds a transaction to the user's account.
    
    :param uid: The user id.
    :type uid: str
    :param data: The data for the transaction.
    :type data: dict
    :returns: {'added': queryset}
    :rtype: dict
    """
    return _add_transaction(uid, data)

@transaction.atomic
@validator.BulkTransactionValidator
@validator.UserValidator
def add_bulk_transactions(uid, data: list):
    """
    Adds a list of transactions to the user's account.
    
    :param uid: The user id.
    :type uid: str
    :param data: A list of dictionaries representing the transactions to add.
    :type data: list# TODO: Fix transactions to default to uncategorized if source is deleted. 
    :returns: {'added': [queryset]}
    :rtype: dict
    """
    logger.debug(f"Adding bulk transactions: {data}")
    added = []
    for item in data:
        logger.debug(f"Adding transaction: {item}")
        _add_transaction(uid, item)
        added.append(Transaction.objects.for_user(uid).get_tx(item['tx_id']))
    return {'added': added}

@transaction.atomic
@validator.TransactionValidator
@validator.TransactionIDValidator
@validator.UserValidator
def update_transaction(uid, tx_id: str, data: dict):
    """
    Updates a transaction in the user's account.
    
    :param uid: The user id.
    :type uid: str
    :param tx_id: The transaction id to update.
    :type tx_id: str
    :param data: The data to update the transaction with.
    :type data: dict
    :returns: {'updated': queryset}
    :rtype: dict
    """
    logger.debug(f"Updating transaction: {data}")
    update.transaction_updated(uid=uid, tx_id=tx_id)
    tx = Transaction.objects.for_user(uid).get_tx(tx_id)
    tx.update(**data)
    if data.get('bill'):
        expense = UpcomingExpense.objects.for_user(uid).get_by_name(data['bill']).get()
        expense_month = expense.due_date
        expense_month.replace(day=1)
        if expense_month >= timezone.now().date():
            expense.paid_flag = True
            expense.save()
    update.new_transaction(uid=uid, tx_id=tx.tx_id)
    return {f'updated': tx}

@transaction.atomic
@validator.TransactionIDValidator
@validator.UserValidator
def delete_transaction(uid, tx_id: str):
    """
    Deletes a transaction from the user's account.
    
    :param uid: The user id.
    :type uid: str
    :param tx_id: The transaction id to delete.
    :type tx_id: str
    :returns: {'deleted': queryset}
    :rtype: dict
    """
    logger.debug(f"Deleting transaction: {tx_id}")

    # Update balances to reverse changes
    update.transaction_updated(uid=uid, tx_id=tx_id)

    # Delete transaction
    tx = Transaction.objects.for_user(uid).get_tx(tx_id)
    tx.delete()
    return {f'deleted': tx}


@validator.TransactionIDValidator
@validator.UserValidator
def get_transaction(uid, tx_id: str):
    """
    Retrieves a single transaction for a user.

    :param uid: The user id.
    :type uid: str
    :param tx_id: The transaction id to retrieve.
    :type tx_id: str
    :returns: {'transaction': queryset}
    :rtype: dict
    """
    logger.debug(f"Getting transaction: {tx_id} for {uid}")
    tx = Transaction.objects.for_user(uid).get_tx(tx_id)
    return {'transaction': tx}


# Private Functions

def _add_transaction(uid, data):
    logger.debug(f"Adding transaction: {data} for {uid}")
    # Pull out tags
    tags = data.pop("tags", None)

    # Fix amount to positive/negative based on tx_type
    data['amount'] = Decimal(Abs(data['amount']))
    if data['tx_type'] in ['EXPENSE', 'XFER_OUT']:
        data['amount'] = data['amount'] * -1

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
    return {'added': tx}
    
def _calc_total(uid, tx_queryset): 
    logger.debug(f"Calculating total for {tx_queryset} for user {uid}")
    return fc.calc_queryset(uid, tx_queryset)

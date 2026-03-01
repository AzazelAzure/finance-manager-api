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
from finance.logic.updaters import Updater
from finance.logic.fincalc import Calculator
from django.db import transaction
from loguru import logger
from finance.models import Transaction, UpcomingExpense, AppProfile

# TODO: Update Docstrings here too.  Again...

# Public Functions

@validator.UserValidator
def get_transactions(uid,**kwargs):
    """
    Retrieves a list of transactions for a user with dynamic filtering and ordering.\n
    If no tx_type is set, will return sum for rejected = serializersall tx_type.\n
    If month is set with no year, will return transactions for current month.\n
    If year is set with no month, will function the same as by_year.\n
    If start_date is set with no end_date, will return all transactions after start_date.\n
    If end_date is set with no start_date, will return all transactions before end_date.\n
    If no kwargs are sent, will return the most recent transaction.\n

    
    :param uid: The user id.
    :type uid: str
    :param kwargs: A dictionary of filters and ordering options.
    :type kwargs: dict
    :returns: {'transactions': queryset, 'amount': decimal amount}
    :rtype: dict
    """

    logger.debug(f"Getting transactions for {uid} with filters: {kwargs}")
    queryset = Transaction.objects.for_user(uid=uid)
    profile = kwargs.get('profile', AppProfile.objects.for_user(uid))
    fc = Calculator(profile)

    if not kwargs:
        queryset = queryset.get_latest()

    # Handle specific filters that require multiple arguments or no arguments
    if kwargs.get('current_month'):
        queryset = queryset.get_current_month()
    if kwargs.get('start_date') and kwargs.get('end_date'):
        queryset = queryset.get_by_period(kwargs['start_date'], kwargs['end_date'])
    if kwargs.get('month') and kwargs.get('year'):
        queryset = queryset.get_by_month(kwargs['month'], kwargs['year'])
    if kwargs.get('last_month'):
        queryset = queryset.get_last_month()
    if kwargs.get('previous_week'):
        queryset = queryset.get_previous_week()

    # Handle special case filters due to multiple use arguments
    if kwargs.get('start_date') and not kwargs.get('end_date'):
        queryset = queryset.get_all_after(kwargs['start_date'])
    if kwargs.get('end_date') and not kwargs.get('start_date'):
        queryset = queryset.get_all_before(kwargs['end_date'])
    if kwargs.get('month') and not kwargs.get('year'):
        queryset = queryset.get_current_month()
    if kwargs.get('year') and not kwargs.get('month'):
        queryset = queryset.get_by_year(kwargs['year'])
    

    # Dynamically apply other single-argument filters using getattr
    # Mapping of query parameter names to manager method names
    SINGLE_ARG_FILTER_MAP = {
        'tx_type': 'get_by_tx_type',
        'tag_name': 'get_by_tag_name',
        'category': 'get_by_category',
        'source': 'get_by_source',
        'currency_code': 'get_by_currency',
        'by_year': 'get_by_year',
        'by_date': 'get_by_date',
        'by_date': 'get_by_date',
        'gte': 'get_gte',
        'lte': 'get_lte',
    }
    for param_name, manager_method_name in SINGLE_ARG_FILTER_MAP.items():
        if kwargs.get(param_name):
            method = getattr(queryset, manager_method_name)
            queryset = method(kwargs[param_name])

    # Default ordering
    queryset = queryset.order_by('tx_id')
    return {'transactions': queryset, 
            'total_expenses': fc.calc_queryset(queryset.filter(tx_type='EXPENSE')),
            'total_income': fc.calc_queryset(queryset.filter(tx_type='INCOME')),
            'total_transfer_out': fc.calc_queryset(queryset.filter(tx_type='XFER_OUT')),
            'total_transfer_in': fc.calc_queryset(queryset.filter(tx_type='XFER_IN')),
            'total_leaks': fc.calc_queryset(queryset.filter(tx_type__in=['XFER_OUT', 'XFER_IN'])),
            }

@validator.UserValidator
@validator.TransactionValidator
@transaction.atomic
def add_transaction(uid, data, *args, **kwargs):
    """
    Adds a transaction to the user's account.
    
    :param uid: The user id.
    :type uid: str
    :param data: The data for the transaction.
    :type data: dict
    :returns: {'added': queryset}
    :rtype: dict
    """
    upcoming = kwargs.get('upcoming', UpcomingExpense.objects.for_user(uid))
    profile = kwargs.get('profile', AppProfile.objects.for_user(uid))
    if isinstance(data, list):
        logger.debug(f"Adding bulk transactions: {data}")
        rejected = kwargs.get('rejected', [])
        accepted = kwargs.get('accepted', [])
        to_update = Transaction.objects.bulk_create([Transaction(**item) for item in accepted])
        update = Updater(uid, profile=profile, transactions=to_update, upcoming=upcoming)
        update.new_transaction()
        if rejected:
            return {'accepted': to_update, 'rejected': rejected}
        else:
            return {'accepted': to_update}
    else:
        logger.debug(f"Adding transaction: {data}")
        tx = Transaction.objects.create(**data)
        update = Updater(profile=profile, transactions=tx, upcoming=upcoming) 
        update.new_transaction(uid, tx)
        return {'accepted': tx}

@validator.UserValidator
@validator.TransactionIDValidator
@validator.TransactionValidator
@transaction.atomic
def update_transaction(uid, tx_id: str, data: dict, *args, **kwargs):
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
    tx = kwargs.get('id_check') 
    profile = kwargs.get('profile', AppProfile.objects.for_user(uid))
    update = Updater(uid, profile=profile, transactions=tx)
    update.transaction_updated()
    tx.update(**data)
    update.new_transaction()
    return {f'updated': tx}

@validator.UserValidator
@validator.TransactionIDValidator
@transaction.atomic
def delete_transaction(uid, tx_id: str, *args, **kwargs):
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
    tx = kwargs.get('id_check')
    profile = kwargs.get('profile', AppProfile.objects.for_user(uid))
    update = Updater(uid, profile=profile, transactions=tx)
    # Update balances to reverse changes
    update.transaction_updated()

    # Delete transaction
    tx = list(tx)
    tx.delete()
    return {f'deleted': tx}

@validator.UserValidator
@validator.TransactionIDValidator
def get_transaction(uid, tx_id: str, *args, **kwargs):
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
    tx = kwargs.get('id_check', Transaction.objects.for_user(uid).get_tx(tx_id))
    return {'transaction': tx}

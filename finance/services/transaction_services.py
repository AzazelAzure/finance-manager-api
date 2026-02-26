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
from dateutil.relativedelta import relativedelta

# Private Functions
def _calc_total(uid, tx_queryset): 
    logger.debug(f"Calculating total for {tx_queryset} for user {uid}")
    return fc.calc_queryset(uid, tx_queryset)


def _handle_upcoming(queryset):
    if isinstance(queryset, list):
        for expense in queryset:
            expense = expense.get()
            expense.paid_flag = True
            if expense.end_date and timezone.now().date() >= expense.end_date:
                expense.is_recurring = False
            if expense.is_recurring:
                expense.due_date = expense.due_date + relativedelta(months=1)
        queryset.bulk_update(queryset, ['paid_flag', 'due_date', 'is_recurring'])
        return
    else:
        queryset = queryset.get()
        queryset.paid_flag = True
        if queryset.end_date and timezone.now().date() >= queryset.end_date:
            queryset.is_recurring = False
        if queryset.is_recurring:
            queryset.due_date = queryset.due_date + relativedelta(months=1)
        queryset.save()
        return

# Public Functions

@validator.UserValidator
def get_transactions(uid,**kwargs):
    """
    Retrieves a list of transactions for a user with dynamic filtering and ordering.\n
    If no tx_type is set, will return sum for rejected = serializersall tx_type.\n
    If month is set with no year, will return transactions for current month.\n
    If year is set with no month, will function the same as by_year.\n
    If start_date is set with no end_date, will return all transactions after start_date.\n
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
            'total_expenses': _calc_total(uid, queryset.filter(tx_type='EXPENSE')),
            'total_income': _calc_total(uid, queryset.filter(tx_type='INCOME')),
            'total_transfer_out': _calc_total(uid, queryset.filter(tx_type='XFER_OUT')),
            'total_transfer_in': _calc_total(uid, queryset.filter(tx_type='XFER_IN')),
            'total_leaks': _calc_total(uid, queryset.filter(tx_type__in=['XFER_OUT', 'XFER_IN'])),
            }

@transaction.atomic
@validator.TransactionValidator
@validator.UserValidator
def add_transaction(uid,data, rejected=None):
    """
    Adds a transaction to the user's account.
    
    :param uid: The user id.
    :type uid: str
    :param data: The data for the transaction.
    :type data: dict
    :returns: {'added': queryset}
    :rtype: dict
    """
    upcoming = UpcomingExpense.objects.for_user(uid)
    if isinstance(data, list):
        logger.debug(f"Adding bulk transactions: {data}")
        accepted = [item for item in data if item not in rejected]
        paid_bills = [item['bill'] for item in accepted if item.get('bill')]
        if paid_bills:
            _handle_upcoming(paid_bills)
        Transaction.objects.bulk_create([Transaction(**item) for item in accepted])
        to_update = Transaction.objects.filter(tx_id__in=[item['tx_id'] for item in accepted])
        for tx in to_update:
            update.new_transaction(uid, tx)
        if rejected:
            return {'accepted': accepted, 'rejected': rejected}
        else:
            return {'accepted': accepted}
    else:
        logger.debug(f"Adding transaction: {data}")
        tx = Transaction.objects.create(**data)
        tx = Transaction.objects.for_user(uid).get(tx_id=tx.tx_id)
        if tx.bill: # Access 'bill' attribute directly from the model instance
            _handle_upcoming(upcoming.filter(name=tx.bill)) # Pass a QuerySet
        update.new_transaction(uid, tx)
        return {'accepted': tx}

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
    if data.get('bill'): # TODO: This doesn't work, fix this.
        expense = UpcomingExpense.objects.for_user(uid).get_by_name(data['bill']).get()
        expense_month = expense.due_date
        expense_month.replace(day=1)
        if expense_month >= timezone.now().date():
            expense.paid_flag = True
            expense.save()
    update.new_transaction(uid, tx)
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

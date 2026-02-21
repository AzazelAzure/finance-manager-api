"""
This module handles all upcoming expense-related functionality for the finance manager application.

Attributes:
    add_expense: Adds a planned expense to the user's account.
    delete_expense: Deletes a planned expense from the user's account.
    update_expense: Updates a planned expense in the user's account.
    get_expenses: Retrieves a list of planned expenses for a user.
    get_expense: Retrieves a single planned expense for a user.
    get_all_expenses: Retrieves a list of all planned expenses for a user.
"""

import finance.logic.validators as validator
import finance.logic.updaters as update
import finance.logic.fincalc as fc
from django.db import transaction
from loguru import logger
from finance.models import UpcomingExpense, AppProfile


@transaction.atomic
@validator.UserValidator
@validator.UpcomingExpenseValidator
def add_expense(uid, data: dict):
    """
    Adds a planned expense to the user's account.

    :param uid: The user id.
    :type uid: str
    :param data: The data for the expense.
    :type data: dict
    :returns: {'added': queryset}
    :rtype: dict
    """
    logger.debug(f"Adding expense: {data}")
    uid = AppProfile.objects.for_user(uid).get()
    data['uid'] = uid
    UpcomingExpense.objects.create(**data)
    update.rebalance(uid)
    return {'added': UpcomingExpense.objects.for_user(uid).get_by_name(data['name'])}

@transaction.atomic    
@validator.UserValidator
def bulk_add_expenses(uid, data: list):
    """
    Adds a list of planned expenses to the user's account.

    :param uid: The user id.
    :type uid: str
    :param data: A list of dictionaries representing the expenses to add.
    :type data: list
    :returns: {'added': [queryset]}
    :rtype: dict
    """
    logger.debug(f"Adding bulk expenses: {data}")
    added = []
    for item in data:
        logger.debug(f"Adding expense: {item}")
        add_expense(uid, item)
        added.append(UpcomingExpense.objects.for_user(uid).get_by_name(item['name']))
    return {'added': added }


@transaction.atomic
@validator.UserValidator
@validator.UpcomingExpenseValidator
def delete_expense(uid, expense_name: str):
    """
    Deletes a planned expense from the user's account.

    :param uid: The user id.
    :type uid: str
    :param expense_name: The name of the expense to delete.
    :type expense_name: str
    :returns: {deleted: queryset}
    :rtype: dict
    """
    logger.debug(f"Deleting expense: {expense_name}")
    expense = UpcomingExpense.objects.for_user(uid).get_by_name(expense_name)
    expense.delete()
    update.rebalance(uid)
    return {'deleted': expense}

@transaction.atomic
@validator.UserValidator
@validator.UpcomingExpenseValidator
def update_expense(uid, expense_name: str, data: dict):
    """
    Updates a planned expense in the user's account.

    :param uid: The user id.
    :type uid: str
    :param expense_name: The name of the expense to update.
    :type expense_name: str
    :param data: The data to update the expense with.
    :type data: dict
    :returns: {'updated': queryset}
    :rtype: dict
    """
    logger.debug(f"Updating expense: {expense_name}")
    expense = UpcomingExpense.objects.for_user(uid).get_by_name(expense_name)
    expense.update(**data)
    update.rebalance(uid)
    return {'updated': expense}


@validator.UserValidator
@validator.UpcomingExpenseValidator
def get_expenses(uid, **kwargs):
    """
    Retrieves a list of planned expenses for a user with dynamic filtering and ordering.
    If start is set with no end, will return all expenses after start.
    If end is set with no start, will return all expenses before end.
    If month is set, will return all expenses for the current month.


    :param uid: The user id.
    :type uid: str
    :param kwargs: A dictionary of filters and ordering options.
    :type kwargs: dict
    :returns: {'expenses': queryset, 'amount': decimal amount}
    :rtype: dict
    """
    logger.debug(f"Getting expenses for {uid} with filters: {kwargs}")
    queryset = UpcomingExpense.objects.for_user(uid)

    # Handle specific filters that require multiple arguments or no arguments
    if kwargs.get('start') and kwargs.get('end'):
        queryset = queryset.get_by_period(kwargs['start'], kwargs['end'])
    if kwargs.get('start') and not kwargs.get('end'):
        queryset = queryset.get_expenses_by_period(kwargs['start'], None)
    if kwargs.get('end') and not kwargs.get('start'):
        queryset = queryset.get_expenses_by_period(None, kwargs['end'])
    if kwargs.get('for_month'):
        queryset = queryset.get_current_month()
    if kwargs.get('remaining'):
        queryset = queryset.get_by_remaining()
    if kwargs.get('upcoming'):
        queryset = queryset.get_all_upcoming()
    
    SINGLE_ARG_FILTER_MAP = {
        'due_date': 'get_by_due_date',
        'end_date': 'get_by_end_date',
        'recurring': 'get_by_recurring',
        'paid_flag': 'get_by_paid_flag',
        'start_date': 'get_by_start_date',
        'currency_code': 'get_by_currency'
    }
    for param_name, manager_method_name in SINGLE_ARG_FILTER_MAP.items():
        if kwargs.get(param_name):
            method = getattr(queryset, manager_method_name)
            queryset = method(kwargs[param_name])
    
    queryset = queryset.order_by('-due_date')
    return {'expenses': queryset, 'amount': fc.calc_queryset(uid, queryset)}


@validator.UserValidator
@validator.UpcomingExpenseValidator
def get_expense(uid, expense_name: str):
    """
    Retrieves a single planned expense for a user.
    
    :param uid: The user id.
    :type uid: str
    :param expense_name: The name of the expense to retrieve.
    :type expense_name: str
    :returns: {'expense': queryset}
    :rtype: dict
    """
    logger.debug(f"Getting expense: {expense_name} for {uid}")
    return {'expense': UpcomingExpense.objects.for_user(uid).get_by_name(expense_name)}

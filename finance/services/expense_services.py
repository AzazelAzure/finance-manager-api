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
from finance.logic.updaters import Updater
from finance.logic.fincalc import Calculator
from django.db import transaction
from loguru import logger
from finance.models import UpcomingExpense, AppProfile

@validator.UserValidator
@validator.UpcomingExpenseValidator
@transaction.atomic
def add_expense(uid, data, *args, **kwargs):
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
    profile = kwargs.get('profile')
    update = Updater(profile=profile)
    if isinstance(data,list):
        logger.debug(f"Adding multiple expenses: {data}")
        accepted = kwargs.get('accepted')
        rejected = kwargs.get('rejected')
        for item in accepted:
            item['uid'] = profile.user_id
        UpcomingExpense.objects.bulk_create([UpcomingExpense(**item) for item in accepted])
        update.rebalance(total_assets=False, leaks=False)
        return {'accepted': accepted, 'rejected': rejected}
    else:
        data['uid'] = profile.user_id
        UpcomingExpense.objects.create(**data)
        update.rebalance(total_assets=False, leaks=False)
        return {'accepted': UpcomingExpense.objects.for_user(uid).get_by_name(data['name'])}


@validator.UserValidator
@validator.UpcomingExpenseGetValidator
@transaction.atomic
def delete_expense(uid, expense_name: str, *args, **kwargs):
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
    update = Updater(profile=kwargs.get('profile'))
    expense = kwargs.get('existing')
    deleted = expense.get()
    expense.delete()
    update.rebalance(total_assets=False, leaks=False)
    return {'deleted': deleted}

@validator.UserValidator
@validator.UpcomingExpenseGetValidator
@validator.UpcomingExpenseValidator
@transaction.atomic
def update_expense(uid,  data: dict, expense_name: str, *args, **kwargs):
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
    expense = kwargs.get('existing')
    update = Updater(profile=kwargs.get('profile'))
    expense.update(**data)
    update.rebalance(total_assets=False, leaks=False)
    return {'updated': expense}


@validator.UserValidator
def get_expenses(uid, **kwargs):
    """
    Retrieves a list of planned expenses for a user with dynamic filtering and ordering.\n
    If start is set with no end, will return all expenses after start.\n
    If end is set with no start, will return all expenses before end.\n
    If month is set, will return all expenses for the current month.\n
    If no kwargs set, will return the current month.


    :param uid: The user id.
    :type uid: str
    :param kwargs: A dictionary of filters and ordering options.
    :type kwargs: dict
    :returns: {'expenses': queryset, 'amount': decimal amount}
    :rtype: dict
    """
    logger.debug(f"Getting expenses for {uid} with filters: {kwargs}")
    queryset = UpcomingExpense.objects.for_user(uid)

    if not kwargs:
        queryset = queryset.get_current_month()

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
    fc = Calculator(profile=kwargs.get('profile'))
    queryset = queryset.order_by('-due_date')
    return {'expenses': queryset, 'amount': fc.calc_queryset(uid, queryset)}


@validator.UserValidator
@validator.UpcomingExpenseGetValidator
def get_expense(uid, expense_name: str, *args, **kwargs):
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
    return {'expense': kwargs.get('existing')}

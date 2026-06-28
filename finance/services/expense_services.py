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
from finance.validators.expense_validators import (
    UpcomingExpenseGetValidator,
    UpcomingExpenseSetValidator,
)
from finance.logic.updaters import Updater
from finance.logic.fincalc import Calculator
from django.db import transaction
from loguru import logger
from finance.api_tools.redaction import payload_keys_preview
from finance.models import UpcomingExpense, AppProfile
from datetime import datetime, timedelta # Added for month filtering
import zoneinfo
from finance.logic.bill_recurrence import (
    MAX_CATCH_UP_PERIODS,
    advance_bill_due_date,
    periods_behind,
)

@validator.UserValidator
@UpcomingExpenseSetValidator
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
    logger.debug("Adding expense | keys={}", payload_keys_preview(data))
    profile = kwargs.get('profile')
    upcoming = kwargs.get('upcoming')
    if isinstance(data,list):
        logger.debug("Adding multiple expenses | len={}", len(data) if isinstance(data, list) else 0)
        accepted = kwargs.get('accepted', [])
        rejected = kwargs.get('rejected', [])
        created = UpcomingExpense.objects.bulk_create([UpcomingExpense(**item) for item in accepted])
        update = Updater(profile=profile, upcoming=upcoming)
        snapshot = update.expense_handler()
        return {'accepted': list(created), 'rejected': rejected, 'snapshot': snapshot}
    else:
        created = UpcomingExpense.objects.create(**data)
        update = Updater(profile=profile, upcoming=upcoming)
        snapshot = update.expense_handler()
        return {'accepted': [created], 'rejected': [], 'snapshot': snapshot}


@validator.UserValidator
@UpcomingExpenseGetValidator
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
    expense = kwargs.get('checked')
    upcoming = kwargs.get('upcoming')
    update = Updater(profile=kwargs.get('profile'), upcoming=upcoming)
    expense.delete()
    snapshot = update.expense_handler(old_name=expense.name)
    return {'deleted': [expense], 'snapshot': snapshot}

@validator.UserValidator
@UpcomingExpenseGetValidator
@UpcomingExpenseSetValidator
@transaction.atomic
def update_expense(uid, expense_name: str, data: dict, *args, **kwargs):
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
    expense = kwargs.get("checked")
    old_name = expense.name
    if not data.get("name"):
        data["name"] = old_name
    upcoming = kwargs.get('upcoming')
    update = Updater(profile=kwargs.get('profile'), upcoming=upcoming)
    for field, value in data.items():
        setattr(expense, field, value)
    expense.save(update_fields=list(data.keys()))
    if old_name != expense.name:
        snapshot = update.expense_handler(old_name=old_name, new_name=expense.name)
    else:
        snapshot = update.expense_handler()
    return {'updated': [expense], 'snapshot': snapshot}


@validator.UserValidator
def get_expenses(uid, **kwargs):
    """
    Retrieves a list of planned expenses for a user with dynamic filtering and ordering.\n
    If start is set with no end, will return all expenses after start.\n
    If end is set with no start, will return all expenses before end.\n
    If 'for_month' is set, will return all expenses for the specified month (YYYY-MM).\n
    If no date-related kwargs set, will return all expenses.


    :param uid: The user id.
    :type uid: str
    :param kwargs: A dictionary of filters and ordering options.
    :type kwargs: dict
    :returns: {'expenses': queryset, 'amount': decimal amount}
    :rtype: dict
    """
    logger.debug(f"Getting expenses for {uid} with filters: {kwargs}")
    queryset = UpcomingExpense.objects.for_user(uid)

    date_filter_applied = False

    # Handle specific date filters that require multiple arguments or no arguments
    if kwargs.get('start') and kwargs.get('end'):
        queryset = queryset.get_expenses_by_period(kwargs['start'], kwargs['end'])
        date_filter_applied = True
    elif kwargs.get('start') and not kwargs.get('end'):
        queryset = queryset.get_expenses_by_period(kwargs['start'], None)
        date_filter_applied = True
    elif kwargs.get('end') and not kwargs.get('start'):
        queryset = queryset.get_expenses_by_period(None, kwargs['end'])
        date_filter_applied = True
    
    # Fix for 'for_month' filter to parse YYYY-MM
    if kwargs.get('for_month'):
        month_str = kwargs['for_month'] # Expected format: "YYYY-MM"
        try:
            year, month = map(int, month_str.split('-'))
            start_date = datetime(year, month, 1).date()
            # Calculate the last day of the month
            if month == 12:
                end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
            else:
                end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
            
            queryset = queryset.get_expenses_by_period(start_date, end_date)
            date_filter_applied = True
        except ValueError:
            logger.warning(f"Invalid 'for_month' format: {month_str}. Expected YYYY-MM. Skipping month filter.")
            # If the format is invalid, do not apply a month filter.
            pass # Continue with other filters if any
            
    from finance.api_tools.query_utils import _query_param_bool
    if _query_param_bool(kwargs.get('remaining')) is True:
        queryset = queryset.get_by_remaining()
    if _query_param_bool(kwargs.get('upcoming')) is True:
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
        val = kwargs.get(param_name)
        if val is not None and val != "":
            # Interpret string booleans correctly for the manager
            if param_name in ("paid_flag", "recurring"):
                val = _query_param_bool(val)
            method = getattr(queryset, manager_method_name)
            queryset = method(val)
    fc = Calculator(profile=kwargs.get("profile"))
    queryset = queryset.order_by("-due_date")
    return {"expenses": queryset, "amount": fc.calc_queryset(queryset)}


@validator.UserValidator
@UpcomingExpenseGetValidator
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
    expense = kwargs.get("checked")
    return {"expense": expense, "amount": expense.amount}


@validator.UserValidator
@UpcomingExpenseGetValidator
@transaction.atomic
def catch_up_expense(uid, expense_name: str, periods: int | None = None, *args, **kwargs):
    """Mark an overdue bill caught up and advance ``due_date`` by bill interval."""
    expense = kwargs.get("checked")
    profile = kwargs.get("profile")
    upcoming = kwargs.get("upcoming")
    today = datetime.now(zoneinfo.ZoneInfo(profile.timezone)).date()

    if expense.paid_flag:
        return {"updated": [expense], "snapshot": None, "periods_advanced": 0}

    if not expense.due_date or expense.due_date >= today:
        return {"updated": [expense], "snapshot": None, "periods_advanced": 0}

    missed = periods_behind(expense, today, MAX_CATCH_UP_PERIODS)
    if missed <= 0:
        return {"updated": [expense], "snapshot": None, "periods_advanced": 0}

    if periods is None:
        advance_by = missed
    else:
        advance_by = min(max(int(periods), 1), MAX_CATCH_UP_PERIODS, missed)

    advance_bill_due_date(expense, periods=advance_by)
    if expense.is_recurring:
        expense.paid_flag = False
    else:
        expense.paid_flag = True

    expense.save(update_fields=["due_date", "paid_flag", "is_recurring"])
    update = Updater(profile=profile, upcoming=upcoming)
    snapshot = update.expense_handler()
    return {
        "updated": [expense],
        "snapshot": snapshot,
        "periods_advanced": advance_by,
        "periods_missed": missed,
    }
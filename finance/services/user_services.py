"""
This module handles all user-related functionality for the finance manager application.

Attributes:
    user_update_spend_accounts: Updates the spend accounts for a user.
    user_get_spend_accounts: Retrieves the spend accounts for a user.
    user_update_base_currency: Updates the base currency for a user.
    user_get_base_currency: Retrieves the base currency for a user.
    user_get_totals: Retrieves the totals for a user.
"""
# TODO: Update logging


import finance.logic.validators as validator
from finance.logic.updaters import Updater
from finance.logic.fincalc import Calculator
from django.db import transaction
from loguru import logger
from finance.models import (
    Transaction,
    AppProfile,
    FinancialSnapshot,
    PaymentSource,
)

@transaction.atomic
@validator.UserValidator
def user_update(uid: str, data: dict, *args, **kwargs):
    """
    Updates the spend accounts for a user.
    Raises a ValidationError if any of the sources do not exist.
    
    :param uid: The user id.
    :type uid: str
    :param data: The data for the spend accounts.
    :type data: list
    :returns: {'spend_accounts': [list], 'message': "Spend accounts updated successfully"}
    :rtype: dict
    """
    logger.debug(f'Updating {uid}')
    profile = kwargs.get('profile')
    sources = kwargs.get('sources') or [PaymentSource.objects.for_user(uid)]
    if data.get('spend_accounts'):
        if isinstance(data['spend_accounts'], list):
            data['spend_accounts'] = [item.lower() for item in data['spend_accounts']]
            profile.spend_accounts = data['spend_accounts']
        else:
            profile.spend_accounts = [data['spend_accounts']]
    if data.get('base_currency'):
        profile.base_currency = data['base_currency'].upper()
    if data.get('timezone'):
        profile.timezone = data['timezone'].upper()
    if data.get('start_week'):
        profile.start_of_week = data['start_week']
    profile.save()
    update = Updater(profile=profile, sources=sources)
    snapshot = update.user_handler()
    return {'message': "User updated successfully", 'snapshot': snapshot}

        
@validator.UserValidator
def user_get_info(uid: str, *args, **kwargs):
    """
    Retrieves the spend accounts and base currency for a user.
    
    :param uid: The user id.
    :type uid: str
    :returns: {'spend_accounts': list, 'base_currency': str}
    :rtype: dict
    """
    logger.debug(f"Getting spend accounts and base currency for {uid}")
    profile = kwargs.get('profile')
    spend_accounts = profile.spend_accounts
    base_currency = profile.base_currency
    timezone = profile.timezone
    start_week = profile.start_of_week
    return {
        'spend_accounts': spend_accounts, 
        'base_currency': base_currency,
        'timezone': timezone,
        'start_of_week': start_week
        }


# Data Getterss
@validator.UserValidator
def user_get_totals(uid, *args, **kwargs):
    """
    Retrieves the totals for a user.  Acts as a basic dashboard retrieval for relevant data.
    
    :param uid: The user id.
    :type uid: str
    :returns: {'Snapshot': queryset, 'transactions for month': queryset, 'total expenses for month': decimal, 'total income for month': decimal, 'total transfer out for month': decimal, 'total transfer in for month': decimal}
    :rtype: dict
    """
    logger.debug(f"Getting all totals for {uid}")
    queryset = Transaction.objects.for_user(uid).get_current_month()
    fc = Calculator(profile=kwargs.get('profile'))
    return {
        'snapshot': FinancialSnapshot.objects.for_user(uid), 
        'transactions_for_month': queryset,
        'total_expenses_for_month': fc.calc_queryset(uid, queryset.get_by_tx_type('EXPENSE')),
        'total_income_for_month': fc.calc_queryset(uid, queryset.get_by_tx_type('INCOME')),
        'total_transfer_out_for_month': fc.calc_queryset(uid, queryset.get_by_tx_type('XFER_OUT')),
        'total_transfer_in_for_month': fc.calc_queryset(uid, queryset.get_by_tx_type('XFER_IN')),
    }



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
import finance.logic.fincalc as fc
from django.db import transaction
from django.core.exceptions import ValidationError
from loguru import logger
from finance.models import (
    CurrentAsset,
    Transaction,
    AppProfile,
    FinancialSnapshot,
    PaymentSource,
    Currency
)

@transaction.atomic
@validator.UserValidator
def user_update_spend_accounts(uid: str, data: list):
    """
    Updates the spend accounts for a user.
    Raises a ValidationError if any of the sources do not exist.
    
    :param uid: The user id.
    :type uid: str
    :param data: The data for the spend accounts.
    :type data: list
    :returns: {'spend_accounts': queryset, 'message': "Spend accounts updated successfully"}
    :rtype: dict
    """
    logger.debug(f"Updating spend accounts for {uid}")
    user = AppProfile.objects.for_user(uid).get()
    # Set all params to uppercase
    data = {k.upper(): v for k, v in data.items()}
    # Check if sources exists
    for item in data:
        if not PaymentSource.objects.for_user(uid).filter(source=item).exists():
            logger.debug(f"Source does not exist: {item}")
            raise ValidationError("Source does not exist")
    # Update spend accounts    
    user.spend_accounts.set(data)    
    return {'spend_accounts': user.spend_accounts.all(), 'message': "Spend accounts updated successfully"}
        
@validator.UserValidator
def user_get_spend_accounts(uid: str):
    """ 
    Retrieves the spend accounts for a user.
    
    :param uid: The user id.
    :type uid: str
    :returns: {'spend_accounts': queryset}
    :rtype: dict
    """
    logger.debug(f"Getting spend accounts for {uid}")
    return {'spend_accounts': AppProfile.objects.for_user(uid).get_spend_accounts()}

@validator.UserValidator
def user_get_base_currency(uid: str):
    """
    Retrieves the base currency for a user.
    
    :param uid: The user id.
    :type uid: str
    :returns: {'base_currency': queryset}
    :rtype: dict
    """
    logger.debug(f"Getting base currency for {uid}")
    return {'base_currency': AppProfile.objects.for_user(uid).get_base_currency()}

@transaction.atomic
@validator.UserValidator
def user_update_base_currency(uid: str, data: dict):
    """
    Updates the base currency for a user.
    
    :param uid: The user id.
    :type uid: str
    :param data: The data for the base currency.
    :type data: dict
    :returns: {'base_currency': queryset, 'message': "Base currency updated successfully"}
    :rtype: dict
    """
    logger.debug(f"Updating base currency for {uid}")
    user = AppProfile.objects.for_user(uid).get()
    # Set all params to uppercase
    data = {k.upper(): v for k, v in data.items()}
    # Check if currency exists
    if not Currency.objects.filter(code=data['code']).exists():
        logger.debug(f"Currency does not exist: {data['code']}")
        raise ValidationError("Currency does not exist")
    # Update base currency
    user.base_currency = data['code']
    user.save()
    return {'base_currency': user.base_currency, 'message': "Base currency updated successfully"}


# Data Getterss
@validator.UserValidator
def user_get_totals(uid):
    """
    Retrieves the totals for a user.  Acts as a basic dashboard retrieval for relevant data.
    
    :param uid: The user id.
    :type uid: str
    :returns: {'Snapshot': queryset, 'assets': queryset, 'transactions for month': queryset, 'total expenses for month': decimal, 'total income for month': decimal, 'total transfer out for month': decimal, 'total transfer in for month': decimal}
    :rtype: dict
    """
    logger.debug(f"Getting all totals for {uid}")
    queryset = Transaction.objects.for_user(uid).get_current_month()
    return {
        'Snapshot': FinancialSnapshot.objects.for_user(uid).first(), 
        'assets': CurrentAsset.objects.for_user(uid).all(),
        'transactions for month': queryset,
        'total expenses for month': fc.calc_queryset(uid, queryset.get_by_tx_type('EXPENSE')),
        'total income for month': fc.calc_queryset(uid, queryset.get_by_tx_type('INCOME')),
        'total transfer out for month': fc.calc_queryset(uid, queryset.get_by_tx_type('XFER_OUT')),
        'total transfer in for month': fc.calc_queryset(uid, queryset.get_by_tx_type('XFER_IN')),
    }



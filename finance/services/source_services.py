"""
This module handles all payment source-related functionality for the finance manager application.

Attributes:
    add_source: Adds a payment source to the user's account.
    delete_source: Deletes a payment source from the user's account.
    update_source: Updates a payment source in the user's account.
    get_sources: Retrieves a list of payment sources for a user.
    get_source: Retrieves a single payment source for a user.
"""

import finance.logic.validators as validator
import finance.logic.updaters as update
from django.db import transaction
from loguru import logger
from finance.models import PaymentSource, AppProfile

# Payment Source Functions
@transaction.atomic
@validator.AssetValidator
@validator.UserValidator
def add_source(uid, data: dict):
    """
    Adds a payment source to the user's account.

    :param uid: The user id.
    :type uid: str
    :param data: The data for the payment source.
    :type data: dict
    :returns: {'message': "Payment source added successfully"}
    :rtype: dict
    """
    logger.debug(f"Adding asset: {data}")
    uid = AppProfile.objects.for_user(uid).get()
    asset = PaymentSource.objects.create(uid=uid,**data)
    update.rebalance(uid=uid, acc_type=asset.acc_type)
    return {'message': "Payment source added successfully"}

@transaction.atomic
@validator.UserValidator
@validator.SourceValidator
def delete_source(uid, source: str):
    """
    Deletes a payment source from the user's account.

    :param uid: The user id.
    :type uid: str
    :param source: The source of the payment source to delete.
    :type source: str
    :returns: {'message': "Payment source deleted successfully"}
    :rtype: dict
    """
    logger.debug(f"Deleting source: {source}")
    source_obj = PaymentSource.objects.for_user(uid).get_by_source(source=source)
    source_obj.delete()
    update.rebalance(uid=uid, acc_type=source_obj.acc_type)
    return {'message': "Payment source deleted successfully"}

@transaction.atomic
@validator.UserValidator
@validator.SourceValidator
def update_source(uid, source: str, data: dict):
    """
    Updates a payment source in the user's account.

    :param uid: The user id.
    :type uid: str
    :param source: The source of the payment source to update.
    :type source: str
    :param data: The data to update the payment source with.
    :type data: dict
    :returns: {'message': "Payment source updated successfully"}
    :rtype: dict
    """
    logger.debug(f"Updating source: {source}")
    source_obj = PaymentSource.objects.for_user(uid).get_by_source(source=source)
    source_obj.update(**data)
    update.rebalance(uid=uid, acc_type=source_obj.acc_type)
    return {'message': "Payment source updated successfully"}

@validator.UserValidator
@validator.SourceValidator
def get_sources(uid, acc_type=None):
    """
    Retrieves a list of payment sources for a user.

    :param uid: The user id.
    :type uid: str
    :param acc_type: The account type of the payment sources to retrieve. Defaults to none.
    :type acc_type: str
    :returns: {'sources': queryset}
    :rtype: dict
    """
    logger.debug(f"Getting all sources for {uid}")
    source_obj = PaymentSource.objects.for_user(uid).all()
    if acc_type:
        source_obj = source_obj.get_by_acc_type(acc_type)
    return {'sources': source_obj}

@validator.UserValidator
@validator.SourceValidator
def get_source(uid, source: str):
    """
    Retrieves a single payment source for a user.

    :param uid: The user id.
    :type uid: str
    :param source: The source of the payment source to retrieve.
    :type source: str
    :returns: {'source': queryset}
    :rtype: dict
    """
    logger.debug(f"Getting source: {source} for {uid}")
    return {'source': PaymentSource.objects.for_user(uid).get_by_source(source=source)}


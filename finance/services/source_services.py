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
@validator.SourceValidator
@validator.UserValidator
def add_source(uid, data: dict):
    """
    Adds a payment source to the user's account.

    :param uid: The user id.
    :type uid: str
    :param data: The data for the payment source.
    :type data: dict
    :returns: {'added': queryset}
    :rtype: dict
    """
    logger.debug(f"Adding asset: {data}")
    uid = AppProfile.objects.for_user(uid).get()
    data['source'] = data['source'].lower()
    asset = PaymentSource.objects.create(uid=uid,**data)
    update.rebalance(uid=uid, acc_type=asset.acc_type)
    return {'added': asset}

@transaction.atomic    
@validator.UserValidator
def bulk_add_sources(uid, data: list):
    """
    Adds a list of payment sources to the user's account.

    :param uid: The user id.
    :type uid: str
    :param data: A list of dictionaries representing the payment sources to add.
    :type data: list
    :returns: {'added': [queryset]}
    :rtype: dict
    """
    logger.debug(f"Adding bulk payment sources: {data}")
    added = []
    for item in data:
        logger.debug(f"Adding payment source: {item}")
        add_source(uid, item)
        added.append(PaymentSource.objects.for_user(uid).get_by_source(source=item['source']))
    return {'added': added }

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
    :returns: {'deleted': queryset}
    :rtype: dict
    """
    logger.debug(f"Deleting source: {source}")
    source_obj = PaymentSource.objects.for_user(uid).get_by_source(source=source)
    source_obj.delete()
    update.rebalance(uid=uid, acc_type=source_obj.acc_type)
    return {'deleted': source_obj}

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
    :returns: {'updated': queryset}
    :rtype: dict
    """
    logger.debug(f"Updating source: {source}")
    source_obj = PaymentSource.objects.for_user(uid).get_by_source(source=source)
    source_obj.update(**data)
    update.rebalance(uid=uid, acc_type=source_obj.acc_type)
    return {'updated': source_obj}

@validator.UserValidator
@validator.SourceValidator
def get_sources(uid, **kwargs):
    """
    Retrieves a list of payment sources for a user.  Accepts optional filters.

    :param uid: The user id.
    :type uid: str
    :param kwargs: A dictionary of filters.
    :type kwargs: dict
    :returns: {'sources': queryset}
    :rtype: dict
    """
    sources = PaymentSource.objects.for_user(uid)
    if kwargs.get('acc_type'):
        sources = sources.get_by_acc_type(kwargs['acc_type'])
    if kwargs.get('source'):
        sources = sources.get_by_source(kwargs['source'])
    return {'sources': sources}


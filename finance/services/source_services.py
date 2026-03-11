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
from finance.logic.updaters import Updater 
from django.db import transaction
from loguru import logger
from finance.models import PaymentSource

# TODO:  GUESS WHAT?!?!?!  Fix the docstrings, commments, and logger
# TODO: Refactor this for the rollin of assets to here


# Payment Source Functions
@validator.UserValidator
@validator.SourceSetValidator
@transaction.atomic
def add_source(uid, data, *args, **kwargs):
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
    sources = kwargs.get('sources')
    if isinstance(data, list):
        rejected = kwargs.get('rejected',[])
        accepted = kwargs.get('accepted',[])
        sources.bulk_create([PaymentSource(**item) for item in accepted])
        update = Updater(profile=kwargs.get('profile'), sources=[kwargs.get('sources')])
        snapshot = update.source_handler()
        return {'added': accepted, 'rejected': rejected, 'snapshot': snapshot}

    else:
        new_source = sources.create(**data)
        if new_source.amount != 0:
            update = Updater(profile=kwargs.get('profile'), sources=[kwargs.get('sources')])
            snapshot = update.source_handler()
    return {'added': new_source, 'snapshot': snapshot}



@validator.UserValidator
@validator.SourceGetValidator
@transaction.atomic
def delete_source(uid, source: str, *args, **kwargs):
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
    source = kwargs.get('source_check')
    source.delete()
    update = Updater(profile=kwargs.get('profile'), sources=[kwargs.get('sources')])
    snapshot = update.source_handler()
    return {'deleted': source, 'snapshot': snapshot}


@validator.UserValidator
@validator.SourceGetValidator
@validator.SourceValidator
@transaction.atomic
def update_source(uid, source: str, data: dict, *args, **kwargs):
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
    source_obj = kwargs.get('checked')
    for field, value in data.items():
        setattr(source_obj, field, value)
    source_obj.save()
    update = Updater(profile=kwargs.get('profile'), sources=[kwargs.get('sources')])
    snapshot = update.source_handler()
    return {'updated': source_obj, 'snapshot': snapshot}

@validator.UserValidator
@validator.SourceValidator
def get_sources(uid, data:dict, *args, **kwargs):
    """
    Retrieves a list of payment sources for a user.  Accepts optional filters.

    :param uid: The user id.
    :type uid: str
    :param kwargs: A dictionary of filters.
    :type kwargs: dict
    :returns: {'sources': queryset}
    :rtype: dict
    """
    sources = kwargs.get('sources')
    if data.get('acc_type'):
        sources = sources.filter(acc_type=data['acc_type'])
    if data.get('source'):
        sources = sources.filter(source__icontains=data['source'])
    return {'sources': sources}


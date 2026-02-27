"""
This module handles all asset-related functionality for the finance manager application.

Attributes:
    user_update_asset_source: Updates a source for an asset.
    user_bulk_update_assets: Updates a list of assets.
    user_get_asset: Retrieves a single asset.
    user_get_all_assets: Retrieves a list of all assets.
"""


import finance.logic.validators as validator
from finance.logic.updaters import Updater
from django.db import transaction
from django.core.exceptions import ValidationError
from loguru import logger
from finance.models import (
    PaymentSource, 
    CurrentAsset,
)

@transaction.atomic
@validator.AssetValidator
@validator.UserValidator
def update_asset_source(uid, data:dict, source: str):
    """
    Updates a source for an asset.
    
    :param uid: The user id.
    :type uid: str
    :param data: The data for the asset source.
    :type data: dict
    :returns: {'asset': model instance}
    :rtype: dict
    """
    # TODO: Fix this to work with the new Updater class
        # This will likely follow transaction logic. 
        # Just need to figure out how to pipe this back and forth to Updater
        # As written currently, this is bad. 

    # TODO: Potentially add bulk asset change as well
        # I'm still stuck on if this is actually necessary
        # I'll probably add it anyway.  
        # If I do:
            # TODO: Update Serializers to handle this
            # TODO: Update views to allow it
            # TODO: Make sure tests actually test bulk changes.
    logger.debug(f"Updating asset: {data}")
    data['source'] = data['source'].lower()
    assets = CurrentAsset.objects.for_user(uid)
    update = Updater(uid, assets=assets)
    asset_instance = assets.get_asset(source=data['source']).get()
    if PaymentSource.objects.filter(uid=uid, source=source).exists():
        source = PaymentSource.objects.filter(uid=uid, source=source).get()
        asset_instance.source = source
        asset_instance.save()
        update.rebalance(uid=uid, acc_type=asset_instance.source.acc_type)
        return {'updated': asset_instance}
    else:
        logger.error(f"Cannot update asset.  Source {source} does not exist.")
        raise ValidationError("Cannot update asset.  Source does not exist.")

@transaction.atomic
@validator.UserValidator
def get_asset(uid, source: str):
    """
    Retrieves a single asset.

    :param uid: The user id.
    :type uid: str
    :param source: The source of the asset to retrieve.
    :type source: str
    :returns: {'asset': model instance}
    :rtype: dict
    """
    logger.debug(f"Getting asset: {source} for {uid}")
    asset = CurrentAsset.objects.for_user(uid).get_asset(source)
    return {'asset': asset}

@transaction.atomic
@validator.UserValidator
def get_all_assets(uid):
    """
    Retrieves a list of all assets.

    :param uid: The user id.
    :type uid: str
    :returns: {'assets': queryset}
    :rtype: dict
    """
    logger.debug(f"Getting all assets for {uid}")
    return {'assets': CurrentAsset.objects.for_user(uid)}


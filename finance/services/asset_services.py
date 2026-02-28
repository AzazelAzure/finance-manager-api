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
    CurrentAsset,
)

@validator.UserValidator
@validator.AssetValidator
@transaction.atomic
def update_asset(uid, data:dict, source: str, **kwargs):
    """
    Updates a source for an asset.
    
    :param uid: The user id.
    :type uid: str
    :param data: The data for the asset source.
    :type data: dict
    :param source: The source of the asset to update.
    :type source: str
    :returns: {'asset': model instance}
    :rtype: dict
    """

    logger.debug(f"Updating asset: {data}")

    # First database hit to get values
    assets = CurrentAsset.objects.for_user(uid).get_asset(source)
    profile = kwargs.get('profile')

    # Set up Updater and asset to be changed
    update = Updater(uid, assets=assets, profile=profile)
    asset_instance = assets.get_asset(source=data['source'])

    # Get the previous type, in case it changes
    prev_type = asset_instance.get().source.acc_type

    # Update and return
    asset_instance.update(**data)
    update.asset_updated(prev_type)
    return {'updated': asset_instance}

@validator.UserValidator
@transaction.atomic
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

@validator.UserValidator
@transaction.atomic
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


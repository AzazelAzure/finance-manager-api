"""
This module handles all asset-related functionality for the finance manager application.

Attributes:
    user_update_asset_source: Updates a source for an asset.
    user_bulk_update_assets: Updates a list of assets.
    user_get_asset: Retrieves a single asset.
    user_get_all_assets: Retrieves a list of all assets.
"""


import finance.logic.validators as validator
import finance.logic.updaters as update
import finance.logic.fincalc as fc
from django.db import transaction
from loguru import logger
from finance.models import (
    PaymentSource, 
    CurrentAsset,
    Currency
)

@transaction.atomic
@validator.AssetValidator
@validator.UserValidator
def user_update_asset_source(uid, data:dict):
    """
    Updates a source for an asset.
    
    :param uid: The user id.
    :type uid: str
    :param data: The data for the asset.
    :type data: dict
    :returns: {'message': "Asset updated successfully"}
    :rtype: dict
    """
    return _user_update_asset(uid, data)

@transaction.atomic
@validator.BulkAssetValidator
@validator.UserValidator
def user_bulk_update_assets(uid, data: list):
    """
    Updates a list of assets.
    
    :param uid: The user id.
    :type uid: str
    :param data: A list of dictionaries representing the assets to update.
    :type data: list
    :returns: {'message': "Bulk assets updated successfully"}
    :rtype: dict
    """
    logger.debug(f"Adding bulk assets: {data}")
    for item in data:
        logger.debug(f"Adding asset: {item}")
        _user_update_asset(uid, item)
    return {'message': "Bulk assets updated successfully"}

@transaction.atomic
@validator.UserValidator
def user_get_asset(uid, source: str):
    """
    Retrieves a single asset.

    :param uid: The user id.
    :type uid: str
    :param source: The source of the asset to retrieve.
    :type source: str
    :returns: {'asset': queryset}
    :rtype: dict
    """
    logger.debug(f"Getting asset: {source} for {uid}")
    asset = CurrentAsset.objects.for_user(uid).get_asset(source)
    return {'asset': asset}

@transaction.atomic
@validator.UserValidator
def user_get_all_assets(uid):
    """
    Retrieves a list of all assets.

    :param uid: The user id.
    :type uid: str
    :returns: {'assets': queryset}
    :rtype: dict
    """
    logger.debug(f"Getting all assets for {uid}")
    return {'assets': CurrentAsset.objects.for_user(uid).all()}


def _user_update_asset(uid, data):
    logger.debug(f"Updating asset: {data}")
    source_obj = PaymentSource.objects.for_user(uid).get_by_source(source=data['source']).get()
    currency_obj = Currency.objects.filter(code=data['currency']).get()
    asset_instance = CurrentAsset.objects.for_user(uid).get_asset(source=data['source'])
    asset_instance.source = source_obj
    asset_instance.currency = currency_obj
    asset_instance.save()
    update.rebalance(uid=uid, acc_type=asset_instance.source.acc_type)
    return {'message': "Asset updated successfully"}
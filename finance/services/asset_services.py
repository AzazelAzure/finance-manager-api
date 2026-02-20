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
    return _user_update_asset(uid, data)

@transaction.atomic
@validator.BulkAssetValidator
@validator.UserValidator
def user_bulk_update_assets(uid, data: list):
    logger.debug(f"Adding bulk assets: {data}")
    for item in data:
        logger.debug(f"Adding asset: {item}")
        _user_update_asset(uid, item)
    return {'message': "Bulk assets updated successfully"}

@transaction.atomic
@validator.UserValidator
def user_get_asset(uid, source: str, currency: str):
    logger.debug(f"Getting asset: {source} for {uid}")
    asset = CurrentAsset.objects.for_user(uid).get_asset(source)
    return {'asset': asset}

@transaction.atomic
@validator.UserValidator
def user_get_all_assets(uid):
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
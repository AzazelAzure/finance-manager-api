import finance.logic.validators as validator
import finance.logic.updaters as update
from django.db import transaction
from loguru import logger
from finance.logging_config import logging_config
from finance.models import *
logging_config()


# Transaction Functions
@transaction.atomic
@validator.TransactionValidator
@validator.UserValidator
def user_add_transaction(uid,data:dict):
    return _user_add_transaction(uid, data)

@transaction.atomic
@validator.BulkTransactionValidator
@validator.UserValidator
def user_add_bulk_transactions(uid, data: list):
    logger.debug(f"Adding bulk transactions: {data}")
    for item in data:
        logger.debug(f"Adding transaction: {item}")
        _user_add_transaction(uid, item)
    return {'message': "Bulk transactions added successfully"}

@transaction.atomic
@validator.TransactionValidator
@validator.TransactionIDValidator
@validator.UserValidator
def user_update_transaction(uid, tx_id: str, data: dict):
    logger.debug(f"Updating transaction: {data}")
    transaction = Transaction.objects.filter(uid=uid, tx_id=tx_id).get()
    transaction.update(**data)
    update.transaction_updated(uid=uid, tx_id=tx_id)
    return {'message': "Transaction updated successfully"}

@transaction.atomic
@validator.TransactionIDValidator
@validator.UserValidator
def user_delete_transaction(uid, tx_id: str):
    logger.debug(f"Deleting transaction: {tx_id}")
    tx = Transaction.objects.filter(uid=uid, tx_id=tx_id).get()
    tx.delete()
    update.transaction_updated(uid=uid, tx_id=tx_id)
    return {'message': "Transaction deleted successfully"}

@transaction.atomic
@validator.TransactionIDValidator
@validator.UserValidator
def user_get_transaction(uid, tx_id: str):
    logger.debug(f"Getting transaction: {tx_id} for {uid}")
    tx = Transaction.objects.filter(uid=uid, tx_id=tx_id).get()
    return {'transaction': tx}

@transaction.atomic
@validator.UserValidator
def user_get_transactions(uid):
    logger.debug(f"Getting transactions for {uid}")
    transactions = Transaction.objects.filter(uid=uid).all()
    return {'transactions': transactions}

# Asset Functions
@transaction.atomic
@validator.UserValidator
def user_add_bulk_assets(uid, data: list):
    logger.debug(f"Adding bulk assets: {data}")
    for item in data:
        logger.debug(f"Adding asset: {item}")
        user_add_asset(uid, item)
    return


@transaction.atomic
@validator.AssetValidator
@validator.UserValidator
def user_update_asset_source(uid, data:dict):
    """
    Update the amount for an existing CurrentAsset.
    Since CurrentAsset is automatically created when PaymentSource is created,
    this function updates the existing asset rather than creating a new one.
    """
    logger.debug(f"Updating asset: {data}")
    # Convert string references to objects (similar to _fix_data for transactions)
    source_obj = PaymentSource.objects.for_user(uid).get_by_source(source=data['source']).get()
    currency_obj = Currency.objects.filter(code=data['currency'], uid=uid).get()
    
    # Update the asset
    CurrentAsset.objects.update(
        source=source_obj,
        uid=AppProfile.objects.for_user(uid).get(),
        currency=currency_obj
    )
    asset = CurrentAsset.objects.filter(source=source_obj, uid=uid).get()
    update.rebalance(uid=uid, acc_type=asset.source.acc_type)
    return {'message': "Asset updated successfully"}


@transaction.atomic
@validator.AssetValidator
@validator.UserValidator
def user_add_asset(uid, data: dict):
    logger.debug(f"Adding asset: {data}")
    asset = CurrentAsset.objects.create(**data)
    update.rebalance(uid=uid, acc_type=asset.source.acc_type)
    return {'message': "Asset added successfully"}


def _user_add_transaction(uid, data):
    logger.debug(f"Adding transaction: {data} for {uid}")
    tags = data.pop("tags", None)
    tx = Transaction.objects.create(**data) 
    if tags:
        logger.debug("Setting tags.  Tags: {tags}")
        tag_obj = Tag.objects.filter(name__in=tags)
        logger.debug(f"Tag objects: {tag_obj}.  Tag to be set: tags")
        tx.tags.set(tag_obj)
    update.transaction_updated(uid=uid, tx_id=tx.tx_id)
    return {'message': "Transaction added successfully"}

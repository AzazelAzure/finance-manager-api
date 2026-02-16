import finance.logic.validators as validator
import finance.logic.updaters as update
from django.db import transaction
from loguru import logger
from finance.logging_config import logging_config
from finance.models import *
logging_config()


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
    return [{'message':'Bulk transactions added successfully'},
            {"total savings": FinancialSnapshot.objects.for_user(uid).get_totals("SAVINGS")},
            {"total assets": FinancialSnapshot.objects.for_user(uid).get_totals("ASSETS")},
            {"total checking": FinancialSnapshot.objects.for_user(uid).get_totals("CHECKING")},
            ]


@transaction.atomic
def user_add_asset(data: dict):
    update.rebalance(uid=data["uid"], acc_type=data["source"])
    return


@transaction.atomic
def user_change_asset(data):
    return

def _user_add_transaction(uid, data):
    logger.debug(f"Adding transaction: {data} for {uid}")
    tags = data.pop("tags", None)
    tx = Transaction.objects.create(**data) 
    if tags:
        logger.debug("Setting tags.  Tags: {tags}")
        tag_obj = Tag.objects.filter(name__in=tags)
        logger.debug(f"Tag objects: {tag_obj}.  Tag to be set: tags")
        tx.tags.set(tag_obj)
    update.new_transaction(uid=uid)
    return {'message': "Transaction added successfully"}

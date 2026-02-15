import finance.logic.implementors as implement
import finance.logic.validators as validator
import finance.logic.updaters as update
from django.db import transaction
from loguru import logger
from finance.logging_config import logging_config
logging_config()


@transaction.atomic
@validator.TransactionValidator
def user_add_transaction(uid,data:dict):
    return _user_add_transaction(uid, data)

@transaction.atomic
@validator.BulkTransactionValidator
def user_add_bulk_transactions(uid, data: list):
    logger.debug(f"Adding bulk transactions: {data}")
    for item in data:
        logger.debug(f"Adding transaction: {item}")
        _user_add_transaction(uid, item)
    return {'message':'Bulk transactions added successfully'}


@transaction.atomic
def user_add_asset(data: dict):
    implement.add_asset(**data)
    update.rebalance(uid=data["uid"], acc_type=data["source"])
    return


@transaction.atomic
def user_change_asset(data):
    return

def _user_add_transaction(uid, data):
    logger.debug(f"Adding transaction: {data} for {uid}")
    implement.add_transaction(**data)
    update.new_transaction(uid=uid, is_income=data["is_income"])
    return {'message': "Transaction added successfully"}

# TODO: Update docstrings
# TODO: Update logging


import finance.logic.validators as validator
import finance.logic.updaters as update
import finance.logic.fincalc as fc
from django.db import transaction
from django.utils import timezone
from loguru import logger
from finance.models import (
    PaymentSource, 
    CurrentAsset,
    Transaction,
    AppProfile,
    FinancialSnapshot,
)

# Payment Source Functions
@transaction.atomic
@validator.AssetValidator
@validator.UserValidator
def user_add_source(uid, data: dict):
    logger.debug(f"Adding asset: {data}")
    uid = AppProfile.objects.for_user(uid).get()
    asset = PaymentSource.objects.create(uid=uid,**data)
    update.rebalance(uid=uid, acc_type=asset.acc_type)
    return {'message': "Payment source added successfully"}

@transaction.atomic
@validator.UserValidator
@validator.PaymentSourceValidator
def user_delete_source(uid, source: str):
    logger.debug(f"Deleting source: {source}")
    source_obj = PaymentSource.objects.for_user(uid).get_by_source(source=source)
    source_obj.delete()
    update.rebalance(uid=uid, acc_type=source_obj.acc_type)
    return {'message': "Payment source deleted successfully"}

@transaction.atomic
@validator.UserValidator
@validator.PaymentSourceValidator
def user_update_source(uid, source: str, data: dict):
    logger.debug(f"Updating source: {source}")
    source_obj = PaymentSource.objects.for_user(uid).get_by_source(source=source)
    source_obj.update(**data)
    update.rebalance(uid=uid, acc_type=source_obj.acc_type)
    return {'message': "Payment source updated successfully"}

@validator.UserValidator
def user_get_sources(uid):
    logger.debug(f"Getting all sources for {uid}")
    return {'sources': PaymentSource.objects.for_user(uid).all()}   

# Data Getterss
@validator.UserValidator
def user_get_totals(uid):
    logger.debug(f"Getting all totals for {uid}")
    queryset = Transaction.objects.for_user(uid).get_current_month()
    return {
        'Snapshot': FinancialSnapshot.objects.for_user(uid).first(), 
        'assets': CurrentAsset.objects.for_user(uid).all(),
        'transactions for month': queryset,
        'total expenses for month': fc.calc_queryset(uid, queryset.get_by_tx_type('EXPENSE')),
        'total income for month': fc.calc_queryset(uid, queryset.get_by_tx_type('INCOME')),
        'total transfer out for month': fc.calc_queryset(uid, queryset.get_by_tx_type('XFER_OUT')),
        'total transfer in for month': fc.calc_queryset(uid, queryset.get_by_tx_type('XFER_IN')),
    }



import finance.logic.fincalc as fc
from finance.models import (
    Transaction, 
    CurrentAsset, 
    UpcomingExpense, 
    AppProfile,
    FinancialSnapshot
)
from loguru import logger


def new_transaction(uid, tx_id: str):
    tx = Transaction.objects.for_user(uid).get_tx(tx_id)
    tx_amount = tx.amount
    multiplier = -1 if tx.tx_type in ["INCOME", "XFER_IN"] else 1
    _recalc_asset_amount(uid, tx.source, tx_amount, multiplier)
    rebalance(uid, tx.source.acc_type)
    return

def transaction_updated(uid, tx_id: str):
    tx = Transaction.objects.for_user(uid).get_tx(tx_id)
    multiplier = -1 if tx.tx_type in ["EXPENSE", "XFER_OUT"] else 1
    tx_amount = tx.amount * multiplier
    _recalc_asset_amount(uid, tx.source, tx_amount, 1)
    rebalance(uid, tx.source.acc_type)
    return

def rebalance(uid, acc_type=None):
    logger.debug(f"Rebalancing {uid} with acc_type {acc_type}")
    if acc_type:
        _recalc_asset_type(uid, acc_type)
    _recalc_total_assets(uid)
    _recalc_leaks(uid)
    _recalc_sts(uid)
    return


def _recalc_sts(uid):
    logger.debug(f"Recalculating safe to spend for {uid}")
    spend_accounts = AppProfile.objects.for_user(uid).get_spend_accounts(uid)
    logger.debug(f"Spend accounts: {spend_accounts.uidaccounts} Base currency: {base_currency}")
    spend_accounts = tuple(spend_accounts)
    sts = fc.calc_sts(uid, spend_accounts)
    logger.warning(f"Changed safe to spend to: {sts}")
    FinancialSnapshot.objects.for_user(uid).update(safe_to_spend=sts)
    return


def _recalc_total_assets(uid):
    logger.debug(f"Recalculating total assets for {uid} with base currency {base_currency}")
    total_assets = fc.calc_total_assets(uid)
    FinancialSnapshot.objects.for_user(uid).update(total_assets=total_assets)
    logger.warning(f"Changed total assets to: {total_assets}")
    return


def _recalc_asset_type(uid, acc_type):
    acc_type = acc_type.acc_type
    logger.debug(f"Recalculating asset type {acc_type} for {uid} with base currency {base_currency}")
    asset = fc.calc_asset_type(uid, acc_type)
    FinancialSnapshot.objects.for_user(uid).set_totals(acc_type, asset)
    return


def _recalc_leaks(uid):
    logger.debug(f"Recalculating leaks for {uid}")
    leaks = fc.calc_leaks(uid)
    FinancialSnapshot.objects.for_user(uid).update(total_leaks=leaks)
    return

def _recalc_asset_amount(uid, source, amount, multiplier):
    logger.debug(f"Recalculating asset amount for {uid} with source {source} and amount {amount}")
    asset = CurrentAsset.objects.for_user(uid).get_asset(source)
    new_amount = amount * multiplier
    new_balance = fc.calc_new_balance(uid, source, new_amount)
    asset.amount = new_balance
    asset.save()
    return


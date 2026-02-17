import finance.logic.fincalc as fc
from finance.models import *
from loguru import logger


def transaction_updated(uid, tx_id: str):
    tx = Transaction.objects.filter(uid=uid, tx_id=tx_id).get()
    tx_amount = tx.amount
    tx_source = tx.source.source
    multiplier = -1 if tx.tx_type in ["INCOME", "XFER_IN"] else 1
    _recalc_asset_amount(uid, tx.source, tx_amount, multiplier)
    rebalance(uid, tx.source)
    return

def rebalance(uid, acc_type=None):
    logger.debug(f"Rebalancing {uid} with acc_type {acc_type}")
    base_currency = AppProfile.objects.for_user(uid).get_base_currency().code
    if acc_type:
        _recalc_asset_type(uid, acc_type, base_currency)
    _recalc_total_assets(uid, base_currency)
    _recalc_leaks(uid, base_currency)
    _recalc_sts(uid, base_currency)
    return


def _recalc_sts(uid, base_currency):
    logger.debug(f"Recalculating safe to spend for {uid}")
    spend_accounts = AppProfile.objects.for_user(uid).get_spend_accounts(uid)
    logger.debug(f"Spend accounts: {spend_asset.uidaccounts} Base currency: {base_currency}")
    spend_accounts = tuple(spend_accounts)
    sts = fc.calc_sts(uid, base_currency, spend_accounts)
    logger.warning(f"Changed safe to spend to: {sts}")
    FinancialSnapshot.objects.filter(uid=uid).update(safe_to_spend=sts)
    return


def _recalc_total_assets(uid, base_currency):
    logger.debug(f"Recalculating total assets for {uid} with base currency {base_currency}")
    total_assets = fc.calc_total_assets(uid, base_currency)
    FinancialSnapshot.objects.filter(uid=uid).update(total_assets=total_assets)
    logger.warning(f"Changed total assets to: {total_assets}")
    return


def _recalc_asset_type(uid, acc_type, base_currency):
    acc_type = acc_type.acc_type
    logger.debug(f"Recalculating asset type {acc_type} for {uid} with base currency {base_currency}")
    asset = fc.calc_asset_type(uid, base_currency, acc_type)
    FinancialSnapshot.objects.for_user(uid).set_totals(acc_type, asset)
    return


def _recalc_leaks(uid, base_currency):
    logger.debug(f"Recalculating leaks for {uid}")
    leaks = fc.calc_leaks(uid, base_currency)
    FinancialSnapshot.objects.filter(uid=uid).update(total_leaks=leaks)
    return

def _recalc_asset_amount(uid, source, amount, multiplier):
    logger.debug(f"Recalculating asset amount for {uid} with source {source} and amount {amount}")
    asset = CurrentAsset.objects.filter(uid=uid, source=source).get()
    new_amount = amount * multiplier
    new_balance = fc.calc_new_balance(uid, source, new_amount)
    asset.amount = new_balance
    asset.save()
    return


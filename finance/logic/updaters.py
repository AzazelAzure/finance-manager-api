import finance.logic.fincalc as fc
from finance.models import *
from loguru import logger


def new_transaction(uid):
    tx = Transaction.objects.for_user(uid).get_latest(uid)
    logger.debug(f"Transaction: {tx}")
    tx_amount = tx.amount
    tx_source = tx.source.source
    logger.debug(f'tx_source: {tx_source}.  tx_amount: {tx_amount}. tx currency: {tx.currency}')
    multiplier = -1 if tx.tx_type in ["INCOME", "XFER_IN"] else 1
    adjusted_amount = tx_amount * multiplier
    balance = fc.calc_new_balance(uid, tx_source, adjusted_amount)
    logger.warning(f'Changed balance to: {balance} from: {CurrentAsset.objects.filter(uid=uid, source=tx.source).get().amount} for: {tx.source.source}')
    CurrentAsset.objects.filter(uid=uid, source=tx.source).update(amount=balance)
    logger.warning(f'Amount after balance change: {CurrentAsset.objects.filter(uid=uid, source=tx.source).get().amount}')
    rebalance(uid, tx.source)
    logger.warning(f'Rebalanced {tx.source.source}.  Total assets: {FinancialSnapshot.objects.for_user(uid).get_totals("ASSETS")}, total checking: {FinancialSnapshot.objects.for_user(uid).get_totals("CHECKING")}, total savings: {FinancialSnapshot.objects.for_user(uid).get_totals("SAVINGS")}')
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
    logger.debug(f"Spend accounts: {spend_accounts} Base currency: {base_currency}")
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

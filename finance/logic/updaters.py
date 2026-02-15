import finance.logic.grabbers as select
import finance.logic.implementors as implement
import finance.logic.fincalc as fc
from loguru import logger


def new_transaction(uid, is_income=False):
    tx = select.get_last_transaction(uid)
    logger.debug(f"Transaction: {tx}")
    tx_amount = tx.amount
    tx_source = tx.source.source
    logger.debug(f'tx_source: {tx_source}.  tx_amount: {tx_amount}. tx currency: {tx.currency}')
    multiplier = -1 if is_income else 1
    adjusted_amount = tx_amount * multiplier
    balance = fc.calc_new_balance(uid, tx_source, adjusted_amount)
    implement.update_asset(uid, tx.source, amount=balance)
    rebalance(uid, tx.source)
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
    base_currency = select.get_base_currency(uid).code
    spend_accounts = select.get_spend_accounts(uid)
    logger.debug(f"Spend accounts: {spend_accounts} Base currency: {base_currency}")
    spend_accounts = tuple(spend_accounts)
    sts = fc.calc_sts(uid, base_currency, spend_accounts)
    implement.set_total(uid, "safe_to_spend", sts)
    return


def _recalc_total_assets(uid):
    logger.debug(f"Recalculating total assets for {uid}")
    base_currency = select.get_base_currency(uid).code
    logger.debug(f"Base currency: {base_currency}")
    total_assets = fc.calc_total_assets(uid, base_currency)
    implement.set_total(uid, "total_assets", total_assets)
    return


def _recalc_asset_type(uid, acc_type):
    acc_type = acc_type.acc_type
    base_currency = select.get_base_currency(uid).code
    logger.debug(f"Recalculating asset type {acc_type} for {uid} with base currency {base_currency}")
    asset = fc.calc_asset_type(uid, base_currency, acc_type)
    implement.set_total(uid, f"total_{acc_type.lower()}", asset)
    return


def _recalc_leaks(uid):
    logger.debug(f"Recalculating leaks for {uid}")
    base_currency = select.get_base_currency(uid).code
    logger.debug(f"Base currency: {base_currency}")
    leaks = fc.calc_leaks(uid, base_currency)
    implement.set_total(uid, "total_leaks", leaks)
    return

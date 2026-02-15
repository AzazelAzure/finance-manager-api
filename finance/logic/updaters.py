import grabbers as select
import implementors as implement
import fincalc as fc


def new_transaction(uid, is_income=False):
    tx = select.get_last_transaction(uid)
    tx_amount = tx.amount
    tx_source = tx.source
    multiplier = -1 if is_income else 1
    adjusted_amount = tx_amount * multiplier
    balance = fc.calc_new_balance(uid, tx_source, adjusted_amount)
    implement.update_expense(uid, tx.source, amount=balance)
    rebalance(uid, tx.source)
    return


def rebalance(uid, acc_type=None):
    if acc_type:
        _recalc_asset_type(uid, acc_type)
    _recalc_total_assets(uid)
    _recalc_leaks(uid)
    _recalc_sts(uid)
    return


def _recalc_sts(uid):
    base_currency = select.get_base_currency(uid)
    spend_accounts = select.get_spend_accounts(uid)
    spend_accounts = tuple(spend_accounts)
    sts = fc.calc_sts(uid, base_currency, spend_accounts)
    implement.set_total(uid, "safe_to_spend", sts)
    return


def _recalc_total_assets(uid):
    base_currency = select.get_base_currency(uid)
    total_assets = fc.calc_total_assets(uid, base_currency)
    implement.set_total(uid, "total_assets", total_assets)
    return


def _recalc_asset_type(uid, acc_type):
    base_currency = select.get_base_currency(uid)
    asset = fc.calc_asset_type(uid, base_currency, acc_type)
    implement.set_total(uid, f"total_{acc_type}", asset)
    return


def _recalc_leaks(uid):
    base_currency = select.get_base_currency(uid)
    leaks = fc.calc_leaks(uid, base_currency)
    implement.set_total(uid, "total_leaks", leaks)
    return

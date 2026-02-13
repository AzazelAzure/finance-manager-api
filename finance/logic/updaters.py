import selectors as select
import implementors as implement
import fincalc as fc


def new_transaction(uid):
    tx = select.get_last_transaction(uid)
    base_currency = select.get_base_currency(uid)
    spend_accounts = select.get_spend_accounts(uid)
    spend_accounts = tuple(spend_accounts)
    sts = fc.calc_sts(uid, base_currency, spend_accounts)

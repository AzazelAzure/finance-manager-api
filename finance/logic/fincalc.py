"""
This module handles all financial calculations for the finance manager application.
"""

# TODO: Update docstrings
# TODO: Import and add logging
# TODO: Add functions to calculate expenses and income.

import grabbers as select
from django.db.models import Sum
from currency_converter import CurrencyConverter
from decimal import Decimal


def calc_sts(uid, base_currency, types_to_include: tuple):
    """
    Calculates 'safe to spend' totals by aggregating specific source types.

    Args:
        uid: Required to linking accounts to user profile.
        base_currency: Base currency code to normalize totals to.
        types_to_include (tuple): String identifiers for source types to include.
    Returns:
        Decimal difference between spendable total and debt total.
    """
    spendable = select.get_asset(uid=uid, *types_to_include)
    debts = select.get_total_remaining(uid)
    spend_by_currency = spendable.values("currency").annotate(total=Sum("amount"))
    debt_by_currency = debts.values("currency").annotate(total=Sum("amount"))
    spend = 0
    debt = 0
    for item in spend_by_currency:
        if item["currency"] != base_currency:
            spend += _convert_currency(item["currency"], base_currency, item["total"])
        else:
            spend += item["total"] or Decimal("0")
    for item in debt_by_currency:
        if item["currency"] != base_currency:
            debt += _convert_currency(item["currency"], base_currency, item["total"])
        else:
            debt += item["total"] or Decimal("0")
    return (spend - debt).quantize(Decimal("0.01"))


def calc_leaks(uid, base_currency):
    """
    Calculates leaks for transfers to monitor fees.
    Returns aggregate sum on xfers or 0
    """
    xfers = select.get_transactions(uid=uid, tx_type="XFER")
    xfers_by_currency = xfers.values("currency").annotate(total=Sum("amount"))
    xfer_total = 0
    for item in xfers_by_currency:
        if item["currency"] != base_currency:
            xfer_total += _convert_currency(
                item["currency"], base_currency, item["total"]
            )
        else:
            xfer_total += item["total"] or Decimal("0")

    return xfer_total.quantize(Decimal("0.01"))


def calc_spending_total(transactions_queryset, base_currency):
    """
    Calculates spending totals from Transactions.

    Args:
        transaction_queryset: Requires a transaction query set pulled from selectors.py

    Returns:
        Decimal aggregate total of transactions or 0.
    """
    tx = transactions_queryset.values("currency").annotate(total=Sum("amount"))
    total = 0
    for item in tx:
        if item["currency"] != base_currency:
            total += _convert_currency(item["currency"], base_currency, item["total"])
        else:
            total += item["total"] or Decimal("0")
    return total.quantize(Decimal("0.01"))


def _convert_currency(from_code, to_code, amount):
    if amount is None:
        return 0
    c = CurrencyConverter(decimal=True)
    converted = c.convert(amount, from_code, to_code)
    return converted

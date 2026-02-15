"""
This module handles all financial calculations for the finance manager application.
"""

# TODO: Update docstrings
# TODO: Update logging
# TODO: Refactor calculators to remove redundant code

import finance.logic.grabbers as select
from django.db.models import Sum
from currency_converter import CurrencyConverter
from decimal import Decimal
from loguru import logger


def calc_sts(uid, base_currency, types_to_include: tuple = ('CASH')):
    """
    Calculates 'safe to spend' totals by aggregating specific source types.

    Args:
        uid: Required to linking accounts to user profile.
        base_currency: Base currency code to normalize totals to.
        types_to_include (tuple): String identifiers for source types to include.
    Returns:
        Decimal difference between spendable total and debt total.
    """
    logger.debug(f"Calculating sts for {uid} with base currency {base_currency} for types {types_to_include}")
    spendable = select.get_asset(uid, *types_to_include)
    debts = select.get_total_remaining(uid)
    spend_by_currency = spendable.values("currency__code").annotate(total=Sum("amount"))
    debt_by_currency = debts.values("currency__code").annotate(total=Sum("estimated_cost"))
    spend = 0
    debt = 0
    for item in spend_by_currency:
        if item["currency__code"] != base_currency:
            spend += _convert_currency(item["currency__code"], base_currency, item["total"])
        else:
            spend += item["total"] or Decimal("0")
    for item in debt_by_currency:
        if item["currency__code"] != base_currency:
            debt += _convert_currency(item["currency__code"], base_currency, item["total"])
        else:
            debt += item["total"] or Decimal("0")
    return Decimal((spend - debt)).quantize(Decimal("0.01"))


def calc_leaks(uid, base_currency):
    """
    Calculates leaks for transfers to monitor fees.
    Returns aggregate sum on xfers or 0
    """
    xfers = select.get_transactions(uid=uid, tx_type="XFER")
    xfers_by_currency = xfers.values("currency__code").annotate(total=Sum("amount"))
    xfer_total = 0
    for item in xfers_by_currency:
        if item["currency__code"] != base_currency:
            xfer_total += _convert_currency(
                item["currency__code"], base_currency, item["total"]
            )
        else:
            xfer_total += item["total"] or Decimal("0")

    return Decimal(xfer_total).quantize(Decimal("0.01"))


def calc_spending_total(transactions_queryset, base_currency):
    """
    Calculates spending totals from Transactions.

    Args:
        transaction_queryset: Requires a transaction query set pulled from selectors.py

    Returns:
        Decimal aggregate total of transactions or 0.
    """
    tx = transactions_queryset.values("currency__code").annotate(total=Sum("amount"))
    total = 0
    for item in tx:
        if item["currency__code"] != base_currency:
            total += _convert_currency(item["currency__code"], base_currency, item["total"])
        else:
            total += item["total"] or Decimal("0")
    return Decimal(total).quantize(Decimal("0.01"))


def calc_new_balance(uid, source, amount):
    logger.debug(f"Calculating new balance for {source} with amount {amount}")
    old_balance = select.get_asset(uid, source).values_list("amount", flat=True).first()
    logger.debug(f"Old balance: {old_balance}")
    new_balance = old_balance - amount
    logger.debug(f"New balance: {new_balance}")
    return Decimal(new_balance).quantize(Decimal("0.01"))


def calc_total_assets(uid, base_currency):
    logger.debug(f"Calculating total assets for {uid} with base currency {base_currency}")
    assets = select.get_all_assets(uid)
    asset_by_currency = assets.values("currency__code").annotate(total=Sum("amount"))
    asset_total = 0
    for item in asset_by_currency:
        if item["currency__code"] != base_currency:
            asset_total += _convert_currency(
                item["currency_code"], base_currency, item["total"]
            )
        else:
            asset_total += item["total"] or Decimal("0")
    return Decimal(asset_total).quantize(Decimal("0.01"))


def calc_asset_type(uid, base_currency, acc_type):
    logger.debug(f"Calculating asset type {acc_type} for {uid} with base currency {base_currency}")
    asset = select.get_type(uid, acc_type)
    asset_by_currency = asset.values("currency__code").annotate(total=Sum("amount"))
    asset_total = 0
    for item in asset_by_currency:
        if item["currency__code"] != base_currency:
            logger.debug(f"Converting {item['currency']} to {base_currency}")
            asset_total += _convert_currency(
                item["currency__code"], base_currency, item["total"]
            )
        else:
            asset_total += item["total"] or Decimal("0")
    return Decimal(asset_total).quantize(Decimal("0.01"))


def _convert_currency(from_code, to_code, amount):
    if amount is None:
        return 0
    c = CurrencyConverter(decimal=True)
    converted = c.convert(amount, from_code, to_code)
    return converted

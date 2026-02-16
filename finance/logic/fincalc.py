"""
This module handles all financial calculations for the finance manager application.
"""

# TODO: Update docstrings
# TODO: Update logging
# TODO: Refactor calculators to remove redundant code
from finance.models import *
import finance.logic.grabbers as select
from django.db.models import Sum
from django.utils import timezone
from currency_converter import CurrencyConverter
from decimal import Decimal
from loguru import logger



def calc_sts(uid, base_currency, types_to_include: tuple = ('CASH,')):
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
    spendable = CurrentAsset.objects.filter(uid=uid, source__source__in=types_to_include)
    debts = UpcomingExpense.objects.filter(
        uid=uid,
        paid_flag=False, 
        status="ACTIVE",
        due_date__lte=timezone.now().date()
        )
    spend_by_currency = spendable.values("currency__code").annotate(total=Sum("amount"))
    debt_by_currency = debts.values("currency__code").annotate(total=Sum("estimated_cost"))
    spend = sum(map(lambda x: _calc_totals(x["currency__code"], base_currency, x["total"]), spend_by_currency))
    debt = sum(map(lambda x: _calc_totals(x["currency__code"], base_currency, x["total"]), debt_by_currency))
    logger.debug(f"Spend: {spend}, Debt: {debt}, Total: {(spend - debt)}")
    return Decimal((spend - debt)).quantize(Decimal("0.01"))


def calc_leaks(uid, base_currency):
    """
    Calculates leaks for transfers to monitor fees.
    Returns aggregate sum on xfers or 0
    """
    xfers_in = Transaction.objects.filter(uid=uid, tx_type="XFER_IN")
    xfers_in_by_currency = xfers_in.values("currency__code").annotate(total=Sum("amount"))
    xfers_out = Transaction.objects.filter(uid=uid, tx_type="XFER_OUT")
    xfers_out_by_currency = xfers_out.values("currency__code").annotate(total=Sum("amount"))
    xfer_in_total = sum(map(lambda x: _calc_totals(x["currency__code"], base_currency, x["total"]), xfers_in_by_currency))
    xfer_out_total = sum(map(lambda x: _calc_totals(x["currency__code"], base_currency, x["total"]), xfers_out_by_currency))
    xfer_total = xfer_in_total - xfer_out_total
    return Decimal(xfer_total).quantize(Decimal("0.01"))

def calc_spending_total(uid, base_currency):
    tx = Transaction.objects.filter(uid=uid, date__range=[timezone.now().date(), None])
    total = sum(map(lambda x: _calc_totals(x["currency__code"], base_currency, x["total"]), tx))
    return Decimal(total).quantize(Decimal("0.01"))


def calc_new_balance(uid, source, amount):
    logger.debug(f"Calculating new balance for {source} with amount {amount}")
    old_balance = CurrentAsset.objects.filter(uid=uid, source__source=source).values_list("amount", flat=True).first()
    logger.debug(f"Old balance: {old_balance}")
    new_balance = old_balance - amount
    logger.debug(f"New balance: {new_balance}")
    return Decimal(new_balance).quantize(Decimal("0.01"))


def calc_total_assets(uid, base_currency):
    logger.debug(f"Calculating total assets for {uid} with base currency {base_currency}")
    assets = CurrentAsset.objects.filter(uid=uid)
    asset_by_currency = assets.values("currency__code").annotate(total=Sum("amount"))
    logger.debug(f"Asset by currency: {asset_by_currency}")
    asset_total = sum(map(lambda x: _calc_totals(x["currency__code"], base_currency, x["total"]), asset_by_currency))
    logger.debug(f"Total asset total: {asset_total}")
    return Decimal(asset_total).quantize(Decimal("0.01"))


def calc_asset_type(uid, base_currency, acc_type):
    logger.debug(f"Calculating asset type {acc_type} for {uid} with base currency {base_currency}")
    asset = CurrentAsset.objects.filter(uid=uid, source__acc_type=acc_type)
    asset_by_currency = asset.values("currency__code").annotate(total=Sum("amount"))
    logger.debug(f"Asset by currency: {asset_by_currency}")
    asset_total = sum(map(lambda x: _calc_totals(x["currency__code"], base_currency, x["total"]), asset_by_currency))
    return Decimal(asset_total).quantize(Decimal("0.01"))

def _convert_currency(from_code, to_code, amount):
    logger.debug(f"Converting {amount} from {from_code} to {to_code}")
    if amount is None:
        return 0
    c = CurrencyConverter(decimal=True)
    converted = c.convert(amount, from_code, to_code)
    logger.debug(f"Converted: {converted}")
    return converted

def _calc_totals(item_currency, base_currency, amount):
    logger.debug(f"Calculating totals for {item_currency} with base currency {base_currency} from {amount}")
    total = 0
    if item_currency != base_currency:
        total += _convert_currency(item_currency, base_currency, amount)
    else:
        total += amount or Decimal("0")
    logger.debug(f"Totals: {total}")
    return total
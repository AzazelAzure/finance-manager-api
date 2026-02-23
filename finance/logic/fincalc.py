"""
This module handles all financial calculations for the finance manager application.

Attributes:
    calc_sts: Calculates 'safe to spend' totals by aggregating specific source types.
    calc_leaks: Calculates leaks for transfers to monitor fees.
    calc_queryset: Calculates the total amount for a queryset.
    calc_new_balance: Calculates the new balance for a source.
    calc_total_assets: Calculates the total assets for a user.
    calc_asset_type: Calculates the total assets for a specific account type.
"""

# TODO: Update logging

from finance.models import (
    CurrentAsset, 
    UpcomingExpense, 
    Transaction,
    AppProfile,
    Currency
)
from django.db.models import Sum
from finance.logic.convert_currency import convert_currency
from decimal import Decimal
from loguru import logger




def calc_sts(uid, types_to_include: tuple = ('CASH,')):
    """
    Calculates 'safe to spend' totals by aggregating specific source types.

    :param uid: Required to linking accounts to user profile.
    :type uid: str
    :param types_to_include: String identifiers for source types to include.
    :type types_to_include: tuple
    :returns: Decimal difference between spendable total and debt total.
    :rtype: Decimal
    """
    base_currency = AppProfile.objects.for_user(uid).get_base_currency().code
    logger.debug(f"Calculating sts for {uid} with base currency {base_currency} for types {types_to_include}")
    spendable = CurrentAsset.objects.for_user(uid).get_by_type(*types_to_include)
    debts = UpcomingExpense.objects.for_user(uid).get_current_month()
    spend_by_currency = spendable.values("currency__code").annotate(total=Sum("amount"))
    debt_by_currency = debts.values("currency__code").annotate(total=Sum("estimated_cost"))
    spend = sum(map(lambda x: _calc_totals(x["currency__code"], base_currency, x["total"]), spend_by_currency))
    debt = sum(map(lambda x: _calc_totals(x["currency__code"], base_currency, x["total"]), debt_by_currency))
    logger.debug(f"Spend: {spend}, Debt: {debt}, Total: {(spend - debt)}")
    return Decimal((spend - debt)).quantize(Decimal("0.01"))


def calc_leaks(uid):
    """
    Calculates leaks for transfers to monitor fees.
    
    :param uid: Required to linking accounts to user profile.
    :type uid: str
    :returns: Aggregate sum on xfers or 0 if none.
    :rtype: Decimal
    """
    base_currency = AppProfile.objects.for_user(uid).get_base_currency().code
    xfers_in = Transaction.objects.for_user(uid).get_by_tx_type("XFER_IN")
    xfers_in_by_currency = xfers_in.values("currency__code").annotate(total=Sum("amount"))
    xfers_out = Transaction.objects.for_user(uid).get_by_tx_type("XFER_OUT")
    xfers_out_by_currency = xfers_out.values("currency__code").annotate(total=Sum("amount"))
    xfer_in_total = sum(map(lambda x: _calc_totals(x["currency__code"], base_currency, x["total"]), xfers_in_by_currency))
    xfer_out_total = sum(map(lambda x: _calc_totals(x["currency__code"], base_currency, x["total"]), xfers_out_by_currency))
    xfer_total = xfer_in_total - xfer_out_total
    return Decimal(xfer_total).quantize(Decimal("0.01"))

def calc_queryset(uid, queryset):
    """
    Calculates the total amount for a queryset.

    :param uid: Required to linking accounts to user profile.
    :type uid: str
    :param queryset: The queryset to calculate the total for.
    :type queryset: QuerySet
    :returns: The total amount for the queryset.
    :rtype: Decimal
    """
    logger.debug(f"Calculating total for {queryset}")
    base_currency = AppProfile.objects.for_user(uid).get_base_currency().code
    total_by_currency = queryset.values("currency__code").annotate(total=Sum("amount"))
    total = sum(map(lambda x: _calc_totals(x["currency__code"], base_currency, x["total"]), total_by_currency))
    return Decimal(total).quantize(Decimal("0.01"))

def calc_new_balance(uid, source, amount, currency):
    """
    Calculates the new balance for a source.

    :param uid: Required to linking accounts to user profile.
    :type uid: str
    :param source: The source to calculate the balance for.
    :type source: str
    :param amount: The amount to subtract from the balance.
    :type amount: Decimal
    :param multiplier: The multiplier to apply to the amount.
    :type multiplier: int
    :param currency: The currency of the amount.
    :type currency: str
    :returns: The new balance for the source.
    :rtype: Decimal
    """
    logger.debug(f"Calculating new balance for {source} with amount {amount}")
    old_balance = CurrentAsset.objects.filter(uid=uid, source__source=source).values_list("amount", flat=True).first()
    logger.debug(f"Old balance: {old_balance}")
    asset_currency = Currency.objects.for_user(uid).get_by_code(code=currency).get()
    if currency != asset_currency.code:
        amount = convert_currency(amount, currency, asset_currency.code)
    new_balance = old_balance + amount
    logger.debug(f"New balance: {new_balance}")
    return Decimal(new_balance).quantize(Decimal("0.01"))


def calc_total_assets(uid):
    """
    Calculates the total assets for a user.

    :param uid: Required to linking accounts to user profile.
    :type uid: str
    :returns: The total assets for the user.
    :rtype: Decimal
    """
    base_currency = AppProfile.objects.for_user(uid).get_base_currency().code
    logger.debug(f"Calculating total assets for {uid} with base currency {base_currency}")
    assets = CurrentAsset.objects.filter(uid=uid).exclude(source__acc_type="UNKNOWN")
    asset_by_currency = assets.values("currency__code").annotate(total=Sum("amount"))
    logger.debug(f"Asset by currency: {asset_by_currency}")
    asset_total = sum(map(lambda x: _calc_totals(x["currency__code"], base_currency, x["total"]), asset_by_currency))
    logger.debug(f"Total asset total: {asset_total}")
    return Decimal(asset_total).quantize(Decimal("0.01"))


def calc_asset_type(uid, acc_type):
    """
    Calculates the total assets for a specific account type.

    :param uid: Required to linking accounts to user profile.
    :type uid: str
    :param acc_type: The account type to calculate the total for.
    :type acc_type: str
    :returns: The total assets for the account type.
    :rtype: Decimal
    """
    base_currency = AppProfile.objects.for_user(uid).get_base_currency().code
    logger.debug(f"Calculating asset type {acc_type} for {uid} with base currency {base_currency}")
    asset = CurrentAsset.objects.filter(uid=uid, source__acc_type=acc_type)
    asset_by_currency = asset.values("currency__code").annotate(total=Sum("amount"))
    logger.debug(f"Asset by currency: {asset_by_currency}")
    asset_total = sum(map(lambda x: _calc_totals(x["currency__code"], base_currency, x["total"]), asset_by_currency))
    return Decimal(asset_total).quantize(Decimal("0.01"))

def _calc_totals(item_currency, base_currency, amount):
    logger.debug(f"Calculating totals for {item_currency} with base currency {base_currency} from {amount}")
    total = 0
    if item_currency != base_currency:
        total += convert_currency(amount, item_currency, base_currency)
    else:
        total += amount or Decimal("0")
    logger.debug(f"Totals: {total}")
    return total
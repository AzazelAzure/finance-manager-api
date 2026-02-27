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
# TODO:  Guess what?  It's docstrings again!

from finance.models import (
    CurrentAsset, 
    UpcomingExpense,
    FinancialSnapshot, 
    PaymentSource,
    Transaction,
    AppProfile,
    Currency
)
from django.db.models import Sum
from finance.logic.convert_currency import convert_currency
from decimal import Decimal
from loguru import logger


class Calculator:

    def __init__(self, profile, **kwargs):
        self.profile = profile
        self.uid = self.profile.user_id
        self.base_currency = self.profile.base_currency.code
        self.spend_accounts = self.profile.get_spend_accounts()

        # These should almost never be passed on initialization.
        # The ability to pass in are for potential future features
        # In current workflow, never pass in a kwarg to set these
        self.assets = kwargs.get("assets") or CurrentAsset.objects.for_user(self.uid)
        self.transactions = kwargs.get('transactions') or Transaction.objects.for_user(self.uid).get_current_month()
        self.sources = kwargs.get('sources') or PaymentSource.objects.for_user(self.uid)
        self.snapshots = kwargs.get('snapshots') or FinancialSnapshot.objects.for_user(self.uid)
        self.currencies = kwargs.get('currencies') or Currency.objects.for_user(self.uid)
        self.upcoming = kwargs.get('upcoming') or UpcomingExpense.objects.for_user(self.uid)
        return

    def calc_sts(self):
        """
        Calculates 'safe to spend' totals by aggregating specific source types.

        :param uid: Required to linking accounts to user profile.
        :type uid: str
        :param types_to_include: String identifiers for source types to include.
        :type types_to_include: tuple
        :returns: Decimal difference between spendable total and debt total.
        :rtype: Decimal
        """
        logger.debug(f"Calculating sts for {self.uid}")
        # Set spendable and get current month debts
        spendable = self.assets.get_by_type(*self.spend_accounts)
        debts = self.upcoming.get_current_month()

        # Organize spendable accounts/debts by currency and get sums
        spend_by_currency = spendable.values("currency__code").annotate(total=Sum("amount"))
        debt_by_currency = debts.values("currency__code").annotate(total=Sum("estimated_cost"))

        # Convert spendable accounts/debts into base currency if necessary
        spend = sum(map(lambda x: self._calc_totals(x["currency__code"], self.base_currency, x["total"]), spend_by_currency))
        debt = sum(map(lambda x: self._calc_totals(x["currency__code"], self.base_currency, x["total"]), debt_by_currency))
        logger.debug(f"Spend: {spend}, Debt: {debt}, Total: {(spend - debt)}")

        # Return decimal converted spendable accounts minus converted debts
        return Decimal((spend - debt)).quantize(Decimal("0.01"))

    def calc_leaks(self):
        """
        Calculates leaks for transfers to monitor fees.
        
        :param uid: Required to linking accounts to user profile.
        :type uid: str
        :returns: Aggregate sum on xfers or 0 if none.
        :rtype: Decimal
        """
        # Get all transactions marked as XFER_IN, Sort by currency type, get sums for each currency
        xfers_in = self.transactions.get_by_tx_type("XFER_IN")
        xfers_in_by_currency = xfers_in.values("currency__code").annotate(total=Sum("amount"))

        # Repeat for XFER_OUT
        xfers_out = self.transactions.get_by_tx_type("XFER_OUT")
        xfers_out_by_currency = xfers_out.values("currency__code").annotate(total=Sum("amount"))

        # Convert both XFER_IN and XFER_OUT totals into base currency
        xfer_in_total = sum(map(lambda x: self._calc_totals(x["currency__code"], self.base_currency, x["total"]), xfers_in_by_currency))
        xfer_out_total = sum(map(lambda x: self._calc_totals(x["currency__code"], self.base_currency, x["total"]), xfers_out_by_currency))
        xfer_total = xfer_in_total - xfer_out_total

        # Return total of XFER_IN - XFER_OUT
        # Set up this way as any fees/losses should be caught in XFER_IN
        return Decimal(xfer_total).quantize(Decimal("0.01"))

    def calc_queryset(self, queryset):
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
        base_currency = self.profile.base_currency.code
        total_by_currency = queryset.values("currency__code").annotate(total=Sum("amount"))
        total = sum(map(lambda x: self._calc_totals(x["currency__code"], base_currency, x["total"]), total_by_currency))
        return Decimal(total).quantize(Decimal("0.01"))

    def calc_new_balance(self, asset_queryset, amount):
        """
        Calculates the new balance for a source.\n
        Amount should always be in one currency.  If not, this will cause problems.\n
        If you're unsure, run the asset_queryset through calc_queryset first.\n
        It's better to convert it all to the base currency then back than to have a mix of currencies.\n

        :param uid: Required to linking accounts to user profile.
        :type uid: str
        :param asset_queryset: The source to calculate the balance for.
        :type source: queryset
        :param amount: The amount to subtract from the balance.
        :type amount: Decimal
        :returns: The new balance for the source.
        :rtype: Decimal
        """
    
        logger.debug(f"Calculating new balance for {asset_queryset} with amount {amount}")

        # Get the current balance
        old_balance = asset_queryset.values_list("amount", flat=True).first()
        logger.debug(f"Old balance: {old_balance}")

        # Check the actual currency vs the base currency
        asset_currency = asset_queryset.currency
        currency = self.profile.base_currency.code

        # This checks if the currency is in the base currency
        # If not, converts the amount passed in to the asset currency
        if currency != asset_currency.code:
            amount = convert_currency(amount, currency, asset_currency.code)

        # Calculate the new balance and return it in Decimal
        new_balance = old_balance + amount
        logger.debug(f"New balance: {new_balance}")
        return Decimal(new_balance).quantize(Decimal("0.01"))

    def calc_total_assets(self):
        """
        Calculates the total assets for a user.

        :param uid: Required to linking accounts to user profile.
        :type uid: str
        :returns: The total assets for the user.
        :rtype: Decimal
        """

        logger.debug(f"Calculating total assets for {self.uid} with base currency {self.base_currency}")

        # Remove 'unknown' from assets so they aren't included in calculations
        assets = self.assets.exclude(source__acc_type="UNKNOWN")

        # Get all assets, and sort them by currency, and sum them by that currency
        asset_by_currency = assets.values("currency__code").annotate(total=Sum("amount"))
        logger.debug(f"Asset by currency: {asset_by_currency}")

        # Convert all assets not already in base_currency to the base_currency
        # Then sum them, and return the total in Decimal
        asset_total = sum(map(lambda x: self._calc_totals(x["currency__code"], self.base_currency, x["total"]), asset_by_currency))
        logger.debug(f"Total asset total: {asset_total}")
        return Decimal(asset_total).quantize(Decimal("0.01"))

    def calc_asset_type(self, acc_type):
        """
        Calculates the total assets for a specific account type.

        :param uid: Required to linking accounts to user profile.
        :type uid: str
        :param acc_type: The account type to calculate the total for.
        :type acc_type: str
        :returns: The total assets for the account type.
        :rtype: Decimal
        """
        logger.debug(f"Calculating asset type {acc_type} for {self.uid}")

        # Get the assets for the incoming acc_type. 
        asset = self.assets.filter(source__acc_type=acc_type)

        # Sums the assets for all sources with the acc_type in acc_type
        asset_by_currency = asset.values("currency__code").annotate(total=Sum("amount"))
        logger.debug(f"Asset by currency: {asset_by_currency}")

        # Converts the assets by currency to base_currency then returns Decimal total
        asset_total = sum(map(lambda x: self._calc_totals(x["currency__code"], self.base_currency, x["total"]), asset_by_currency))
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

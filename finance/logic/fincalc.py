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

from django.db.models import Sum
from finance.logic.convert_currency import convert_currency
from decimal import Decimal
from loguru import logger


class Calculator:

    def __init__(self, profile, **kwargs):
        self.profile = profile
        self.uid = self.profile.user_id
        self.base_currency = self.profile.base_currency
        self.spend_accounts = self.profile.spend_accounts
        return

    def calc_sts(self, source_list, debt_list):
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
        spendable = source_list
        debts = debt_list

        # Organize spendable accounts/debts by currency and get sums
        spend_by_currency = {}
        for item in spendable:
            if item.currency not in spend_by_currency:
                spend_by_currency[item.currency] = item.amount
            else:
                spend_by_currency[item.currency] += item.amount
        logger.debug(f"Spend by currency: {spend_by_currency}")

        debt_by_currency = {}
        for item in debts:
            if item.currency not in debt_by_currency:
                debt_by_currency[item.currency] = item.amount
            else:
                debt_by_currency[item.currency] += item.amount
        logger.debug(f"Debt by currency: {debt_by_currency}")

        # Convert spendable accounts/debts into base currency if necessary
        spend = sum(self._calc_totals(currency, self.base_currency, amount) for currency, amount in spend_by_currency.items())
        debt = sum(self._calc_totals(currency, self.base_currency, amount) for currency, amount in debt_by_currency.items())
        logger.debug(f"Spend: {spend}, Debt: {debt}, Total: {(spend - debt)}")

        # Return decimal converted spendable accounts minus converted debts
        return Decimal((spend - debt)).quantize(Decimal("0.01"))

    def calc_leaks(self, tx_list):
        """
        Calculates leaks for transfers to monitor fees.
        
        :param uid: Required to linking accounts to user profile.
        :type uid: str
        :returns: Aggregate sum on xfers or 0 if none.
        :rtype: Decimal
        """
        # Get all transactions marked as XFER_IN, Sort by currency type, get sums for each currency
        xfers_in = [tx for tx in tx_list if tx.tx_type == "XFER_IN"]
        xfers_in_by_currency = {}
        for item in xfers_in:
            if item.currency not in xfers_in_by_currency:
                xfers_in_by_currency[item.currency] = item.amount
            else:
                xfers_in_by_currency[item.currency] += item.amount
        logger.debug(f"Xfers in by currency: {xfers_in_by_currency}")

        # Repeat for XFER_OUT
        xfers_out = [tx for tx in tx_list if tx.tx_type == "XFER_OUT"]
        xfers_out_by_currency = {}
        for item in xfers_out:
            if item.currency not in xfers_out_by_currency:
                xfers_out_by_currency[item.currency] = item.amount
            else:
                xfers_out_by_currency[item.currency] += item.amount
        logger.debug(f"Xfers out by currency: {xfers_out_by_currency}")

        # Convert both XFER_IN and XFER_OUT totals into base currency
        xfer_in_total = sum(self._calc_totals(currency, self.base_currency, amount) for currency, amount in xfers_in_by_currency.items())
        xfer_out_total = sum(self._calc_totals(currency, self.base_currency, amount) for currency, amount in xfers_out_by_currency.items())
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

    def calc_new_balance(self, source_queryset, amount):
        """
        Calculates the new balance for a source.\n
        Amount should always be in one currency.  If not, this will cause problems.\n
        Realistically, you should make sure the amount is in the base currency first.

        :param uid: Required to linking accounts to user profile.
        :type uid: str
        :param asset_queryset: The source to calculate the balance for.
        :type source: queryset
        :param amount: The amount to subtract from the balance.
        :type amount: Decimal
        :returns: The new balance for the source.
        :rtype: Decimal
        """
    
        logger.debug(f"Calculating new balance for {source_queryset} with amount {amount}")

        # Get the current balance
        old_balance = source_queryset.values_list("amount", flat=True).first()
        logger.debug(f"Old balance: {old_balance}")

        # Check the actual currency vs the base currency
        asset_currency = source_queryset.currency
        currency = self.base_currency

        # This checks if the currency is in the base currency
        # If not, converts the amount passed in to the asset currency
        if currency != asset_currency.code:
            amount = convert_currency(amount, currency, asset_currency)

        # Calculate the new balance and return it in Decimal
        new_balance = old_balance + amount
        logger.debug(f"New balance: {new_balance}")
        return Decimal(new_balance).quantize(Decimal("0.01"))

    def calc_total_assets(self, source_list):
        """
        Calculates the total assets for a user.

        :param uid: Required to linking accounts to user profile.
        :type uid: str
        :returns: The total assets for the user.
        :rtype: Decimal
        """
        # TODO: Fix this for sources

        logger.debug(f"Calculating total assets for {self.uid} with base currency {self.base_currency}")

        # Remove 'unknown' from assets so they aren't included in calculations
        assets = [source for source in source_list if source.acc_type != "UNKNOWN"]

        # Get all assets, and sort them by currency, and sum them by that currency
        asset_by_currency = {}
        for item in assets:
            if item.currency not in asset_by_currency:
                asset_by_currency[item.currency] = item.amount
            else:
                asset_by_currency[item.currency] += item.amount
        logger.debug(f"Asset by currency: {asset_by_currency}")

        # Convert all assets not already in base_currency to the base_currency
        # Then sum them, and return the total in Decimal
        asset_total = sum(self._calc_totals(currency, self.base_currency, amount) 
                          for currency, amount in asset_by_currency.items())
        
        logger.debug(f"Total asset total: {asset_total}")
        return Decimal(asset_total).quantize(Decimal("0.01"))

    def calc_acc_types(self, source_list):
        acctype_totals ={}
        for source in source_list:
            if source.acc_type == "UNKNOWN":
                continue
            if source.currency != self.base_currency:
                source.amount = convert_currency(source.amount, source.currency, self.base_currency)
            if f'total_{source.acc_type.lower()}' in acctype_totals:
                acctype_totals[f'total_{source.acc_type.lower()}'] += Decimal(source.amount).quantize(Decimal("0.01"))
            else:
                acctype_totals[f'total_{source.acc_type.lower()}'] = Decimal(source.amount).quantize(Decimal("0.01"))
        logger.debug(f"Acc type totals: {acctype_totals}")
        return acctype_totals

    def calc_tx_sources(self, tx_list, source_list):
        source_aggregate ={}
        source_map = {source.source: source for source in source_list}
        logger.debug(f"Source map: {source_map}")
        for source in source_list: 
            source_aggregate[source.source] = Decimal(source.amount).quantize(Decimal("0.01"))
        logger.debug(f"Initialized source aggregate: {source_aggregate}")
        for tx in tx_list:
            amount_to_add = tx.amount
            if tx.currency != source_map[tx.source].currency:
                amount_to_add = convert_currency(tx.amount, tx.currency, source_map[tx.source].currency)
            source_aggregate[tx.source] += Decimal(amount_to_add).quantize(Decimal("0.01"))
        logger.debug(f"Source aggregate: {source_aggregate}")
        return source_aggregate

    
    @staticmethod
    def _calc_totals(item_currency, base_currency, amount):
        logger.debug(f"Calculating totals for {item_currency} with base currency {base_currency} from {amount}")
        total = 0
        if item_currency != base_currency:
            total += convert_currency(amount, item_currency, base_currency)
        else:
            total += amount or Decimal("0")
        logger.debug(f"Totals: {total}")
        return total

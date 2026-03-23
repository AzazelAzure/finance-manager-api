"""Financial calculation helpers used by services and updater flows."""

from django.db.models import Sum
from finance.logic.convert_currency import convert_currency
from decimal import Decimal
from loguru import logger


class Calculator:
    """Compute aggregate balances/summaries in the user's base currency."""

    def __init__(self, profile, **kwargs):
        self.profile = profile
        self.uid = self.profile.user_id
        self.base_currency = self.profile.base_currency
        self.spend_accounts = self.profile.spend_accounts
        return

    def calc_sts(self, source_list, debt_list):
        """Return safe-to-spend as spendable sources minus unpaid debts."""
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

        debt_by_currency = {}
        for item in debts:
            if item.currency not in debt_by_currency:
                debt_by_currency[item.currency] = item.amount
            else:
                debt_by_currency[item.currency] += item.amount

        # Convert spendable accounts/debts into base currency if necessary
        spend = sum(self._calc_totals(currency, self.base_currency, amount) for currency, amount in spend_by_currency.items())
        debt = sum(self._calc_totals(currency, self.base_currency, amount) for currency, amount in debt_by_currency.items())

        # Return decimal converted spendable accounts minus converted debts
        return Decimal((spend - debt)).quantize(Decimal("0.01"))

    def calc_leaks(self, tx_list):
        """Return net transfer delta to surface transfer leakage/fees."""
        # Get all transactions marked as XFER_IN, Sort by currency type, get sums for each currency
        xfers_in = [tx for tx in tx_list if tx.tx_type == "XFER_IN"]
        xfers_in_by_currency = {}
        for item in xfers_in:
            if item.currency not in xfers_in_by_currency:
                xfers_in_by_currency[item.currency] = item.amount
            else:
                xfers_in_by_currency[item.currency] += item.amount

        # Repeat for XFER_OUT
        xfers_out = [tx for tx in tx_list if tx.tx_type == "XFER_OUT"]
        xfers_out_by_currency = {}
        for item in xfers_out:
            if item.currency not in xfers_out_by_currency:
                xfers_out_by_currency[item.currency] = item.amount
            else:
                xfers_out_by_currency[item.currency] += item.amount

        # Convert both XFER_IN and XFER_OUT totals into base currency
        xfer_in_total = sum(self._calc_totals(currency, self.base_currency, amount) for currency, amount in xfers_in_by_currency.items())
        xfer_out_total = sum(self._calc_totals(currency, self.base_currency, amount) for currency, amount in xfers_out_by_currency.items())
        xfer_total = xfer_in_total - xfer_out_total

        # Return total of XFER_IN - XFER_OUT
        # Set up this way as any fees/losses should be caught in XFER_IN
        return Decimal(xfer_total).quantize(Decimal("0.01"))

    def calc_queryset(self, queryset):
        """Return summed queryset total converted into base currency."""
        base_currency = self.profile.base_currency
        if hasattr(base_currency, "code"):
            base_currency = base_currency.code
        # Transaction.currency is a CharField (code), not a FK
        total_by_currency = queryset.values("currency").annotate(total=Sum("amount"))
        total = sum(
            self._calc_totals(x["currency"], base_currency, x["total"])
            for x in total_by_currency
        )
        return Decimal(total).quantize(Decimal("0.01")) 

    def calc_new_balance(self, source_queryset, amount):
        """Return updated source balance, converting amount when needed."""

        # Get the current balance
        old_balance = source_queryset.values_list("amount", flat=True).first()

        # Check the actual currency vs the base currency
        asset_currency = source_queryset.currency
        currency = self.base_currency

        # This checks if the currency is in the base currency
        # If not, converts the amount passed in to the asset currency
        if currency != asset_currency.code:
            amount = convert_currency(amount, currency, asset_currency)

        # Calculate the new balance and return it in Decimal
        new_balance = old_balance + amount
        return Decimal(new_balance).quantize(Decimal("0.01"))

    def calc_total_assets(self, source_list):
        """Return total assets across non-UNKNOWN sources in base currency."""

        # Remove 'unknown' from assets so they aren't included in calculations
        assets = [source for source in source_list if source.acc_type != "UNKNOWN"]

        # Get all assets, and sort them by currency, and sum them by that currency
        asset_by_currency = {}
        for item in assets:
            if item.currency not in asset_by_currency:
                asset_by_currency[item.currency] = item.amount
            else:
                asset_by_currency[item.currency] += item.amount

        # Convert all assets not already in base_currency to the base_currency
        # Then sum them, and return the total in Decimal
        asset_total = sum(self._calc_totals(currency, self.base_currency, amount) 
                          for currency, amount in asset_by_currency.items())
        
        return Decimal(asset_total).quantize(Decimal("0.01"))

    def calc_acc_types(self, source_list):
        """Return per-account-type totals keyed as ``total_<type>``."""
        acctype_totals ={}
        for source in source_list:
            if source.acc_type == "UNKNOWN":
                continue
            # Normalize all source balances before grouping by account type.
            if source.currency != self.base_currency:
                source.amount = convert_currency(source.amount, source.currency, self.base_currency)
            if f'total_{source.acc_type.lower()}' in acctype_totals:
                acctype_totals[f'total_{source.acc_type.lower()}'] += Decimal(source.amount).quantize(Decimal("0.01"))
            else:
                acctype_totals[f'total_{source.acc_type.lower()}'] = Decimal(source.amount).quantize(Decimal("0.01"))
        return acctype_totals

    def calc_tx_sources(self, tx_list, source_list):
        """Apply transactions to source balances and return per-source totals."""
        source_aggregate ={}
        source_map = {source.source: source for source in source_list}
        for source in source_list: 
            source_aggregate[source.source] = Decimal(source.amount).quantize(Decimal("0.01"))
        for tx in tx_list:
            amount_to_add = tx.amount
            # Convert each transaction into the target source currency before applying.
            if tx.currency != source_map[tx.source].currency:
                amount_to_add = convert_currency(tx.amount, tx.currency, source_map[tx.source].currency)
            source_aggregate[tx.source] += Decimal(amount_to_add).quantize(Decimal("0.01"))
        return source_aggregate

    
    @staticmethod
    def _calc_totals(item_currency, base_currency, amount):
        """Convert amount into base currency and return numeric total."""
        total = 0
        if item_currency != base_currency:
            total += convert_currency(amount, item_currency, base_currency)
        else:
            total += amount or Decimal("0")
        return total

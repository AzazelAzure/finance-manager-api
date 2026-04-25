"""Financial calculation helpers used by services and updater flows."""

import zoneinfo
from datetime import datetime
from decimal import Decimal

from django.db.models import Sum
from finance.logic.convert_currency import convert_currency
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
        """Absolute transfer imbalance in base currency (fees, rounding, drift).

        Rows follow ``fix_tx_data`` / DB storage: XFER_IN positive, XFER_OUT negative.
        We report leak magnitude as a positive value for UX consistency.
        """
        net = Decimal("0")
        for tx in tx_list:
            if tx.tx_type not in ("XFER_IN", "XFER_OUT"):
                continue
            net += Decimal(self._calc_totals(tx.currency, self.base_currency, tx.amount))
        return abs(net).quantize(Decimal("0.01"))

    def calc_current_month_expense_spending(self):
        """Positive total of EXPENSE rows in the user's current calendar month, base currency.

        Expense amounts are stored negative after ``fix_tx_data``; this returns the
        magnitude of outflow for snapshot ``total_monthly_spending``.
        """
        from finance.models import Transaction

        tz = zoneinfo.ZoneInfo(self.profile.timezone)
        today = datetime.now(tz).date()
        first = today.replace(day=1)
        qs = Transaction.objects.for_user(self.uid).filter(
            tx_type="EXPENSE",
            date__gte=first,
            date__lte=today,
        )
        signed_total = self.calc_queryset(qs)
        return abs(signed_total).quantize(Decimal("0.01"))

    def calc_upcoming_bills_base_total(self, bills):
        """Sum ``UpcomingExpense`` (or similar) amounts into base currency.

        Callers pass only the rows that should count (e.g. unpaid bills due this month).
        """
        total = Decimal("0")
        for bill in bills:
            amt = getattr(bill, "amount", None)
            if amt is None:
                continue
            cur = getattr(bill, "currency", None) or self.base_currency
            if hasattr(cur, "code"):
                cur = cur.code
            cur = str(cur).upper()
            total += Decimal(self._calc_totals(cur, self.base_currency, amt))
        return total.quantize(Decimal("0.01"))

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

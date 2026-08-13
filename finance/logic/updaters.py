"""State mutation helpers for transactions, sources, expenses, and snapshots."""

from datetime import datetime
from django.utils.dateparse import parse_date

from finance.logic.fincalc import Calculator
from finance.logic.pay_cycle import current_pay_cycle_window
from finance.logic.source_linkage import (
    build_source_maps,
    generate_source_id,
    load_source_maps,
)
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from finance.models import (
    Transaction, 
    PaymentSource,
    FinancialSnapshot,
    UpcomingExpense
)
from loguru import logger
import uuid
import zoneinfo

class Updater:
    """Apply data-side effects after CRUD operations across finance domains."""
    def __init__(self, profile, **kwargs):
        
        # Required arguments
        self.profile = profile
        

        # Ease for profile to set applicable info
        self.uid = self.profile.user_id
        self.base_currency = self.profile.base_currency
        self.spend_accounts = self.profile.spend_accounts
        self.timezone = zoneinfo.ZoneInfo(self.profile.timezone)
        
        
        # Situational settings
        if "transactions" in kwargs:
            self.transactions = kwargs.get("transactions") or []
            upcoming_obj = kwargs.get('upcoming')
            self.upcoming = upcoming_obj or UpcomingExpense.objects.for_user(self.uid)

            # `TransactionValidator` may pass preloaded `sources` and `upcoming` as lists.
            # When lists are provided, avoid re-querying to reduce DB executions.
            sources_obj = kwargs.get('sources') or PaymentSource.objects.for_user(self.uid)
            if isinstance(sources_obj, list):
                self.sources = sources_obj
            else:
                self.sources = list(sources_obj)

            self.paid_bills = set(tx.bill for tx in self.transactions if tx.bill)
            if isinstance(upcoming_obj, list):
                # Keep a queryset around for `.bulk_update(...)` calls,
                # but compute unpaid in-memory from the preloaded list.
                self.upcoming = UpcomingExpense.objects.for_user(self.uid)
                self.unpaid = [b for b in upcoming_obj if not b.paid_flag]
            elif isinstance(self.upcoming, list):
                # Defensive fallback; should not normally happen.
                self.unpaid = [b for b in self.upcoming if not b.paid_flag]
            else:
                self.unpaid = list(self.upcoming.filter(paid_flag=False))
            self.spend_accounts = list(
                source for source in self.sources if source.source_id in self.spend_accounts
            )
            
        if kwargs.get('sources'):
            self.sources = kwargs.get('sources')

        if kwargs.get('upcoming'):
            self.sources = kwargs.get('sources') or list(PaymentSource.objects.for_user(self.uid))
            upcoming_obj = kwargs.get('upcoming')
            # If upcoming was preloaded as a list (TransactionValidator optimization),
            # we still need a queryset on `self.upcoming` for `.bulk_update(...)`.
            if isinstance(upcoming_obj, list):
                self.upcoming = UpcomingExpense.objects.for_user(self.uid)
            else:
                self.upcoming = upcoming_obj

        # Snapshot is only required by handlers that mutate or rebuild totals.
        # Validators sometimes instantiate Updater just to call pure fixers (e.g., fix_tx_data),
        # and in those cases we should avoid an unnecessary DB hit.
        self.snapshots = None
        if "transactions" in kwargs or kwargs.get('sources') or kwargs.get('upcoming'):
            self.snapshots = FinancialSnapshot.objects.for_user(self.uid).first()
        
        # Create the calculator instance
        self.fc = Calculator(self.profile)
        return

    def _bills_unpaid_due_in_profile_current_month(self):
        """Unpaid upcoming bills with due_date in the profile's active STS window.

        Must match the intended KPI semantics: *remaining* bills due in the STS window (unpaid)
        in base-currency form, and the same set must back *safe to spend* (spendable minus
        those bills). Use profile timezone for calendar-month windows (not server UTC day).
        """
        now = datetime.now(self.timezone).date()
        if self.profile.sts_window_mode == "pay_cycle":
            window_start, window_end = current_pay_cycle_window(self.profile, today=now)
        else:
            window_start = now.replace(day=1)
            window_end = window_start + relativedelta(months=1)
        if hasattr(self, "unpaid"):
            return [
                b
                for b in self.unpaid
                if b.due_date and window_start <= b.due_date < window_end
            ]
        upcoming_qs = getattr(self, "upcoming", None) or UpcomingExpense.objects.for_user(self.uid)
        return list(
            upcoming_qs.filter(
                paid_flag=False,
                due_date__gte=window_start,
                due_date__lt=window_end,
            )
        )

    # Data fixers
    def fix_tx_data(self, data):
        """Normalize incoming transaction payload fields in-place."""
        maps = build_source_maps(self.sources) if hasattr(self, "sources") and self.sources else load_source_maps(self.uid)
        name_to_id, id_to_name = maps
        for item in data:
            item['uid'] = self.profile.user_id
            item['amount'] = abs(Decimal(item['amount']))
            item['currency'] = item['currency'].upper()
            raw_source = str(item['source'])
            if raw_source in id_to_name:
                item['source'] = raw_source
            else:
                lower = raw_source.lower()
                item['source'] = name_to_id.get(lower, lower)
            if item['tx_type'] in ['EXPENSE', 'XFER_OUT']:
                item['amount'] = item['amount'] * -1
            if not item.get('date'):
                item['date'] = datetime.now(self.timezone).date()
            if not item.get('created_on'):
                item['created_on'] = datetime.now(self.timezone).date()
            if not item.get('tx_id'):
                date_suffix = datetime.now(self.timezone).date()
                unique_id = str(uuid.uuid4())[:8].upper()
                item['tx_id'] = f"{date_suffix}-{unique_id}"
            if not item.get('category'):
                if item['tx_type'] in ['XFER_IN', 'XFER_OUT']:
                    item['category'] = 'transfer'
                else:
                    item['category'] = item['tx_type'].lower()
        return data

    def fix_source_data(self, data):
        """Normalize incoming source payload fields in-place."""
        today = datetime.now(self.timezone).date()
        for item in data:
            item['uid'] = self.profile.user_id
            item['source'] = item['source'].lower()
            item['acc_type'] = item['acc_type'].upper()
            if not item.get('source_id'):
                item['source_id'] = generate_source_id(today)
            if item.get('currency'):
                item['currency'] = item['currency'].upper()
            if item.get('amount') is not None and item.get('amount') != "":
                item['amount'] = Decimal(item['amount'])
            else:
                item['amount'] = Decimal("0.00")
            if item.get("opening_amount") is None or item.get("opening_amount") == "":
                item["opening_amount"] = item["amount"]
            else:
                item["opening_amount"] = Decimal(item["opening_amount"])
        return data
    
    def fix_expense_data(self, data):
        """Normalize incoming expense payload fields in-place."""
        maps = build_source_maps(self.sources) if hasattr(self, "sources") and self.sources else load_source_maps(self.uid)
        name_to_id, id_to_name = maps
        for item in data:
            item['uid'] = self.profile.user_id
            if item.get('name'):
                item['name'] = str(item["name"]).strip()
            if item.get('currency'):
                item['currency'] = item['currency'].upper()
            if "source" in item:
                raw = item["source"]
                if raw is None or raw == "":
                    item["source"] = None
                else:
                    raw_source = str(raw)
                    if raw_source in id_to_name:
                        item["source"] = raw_source
                    else:
                        item["source"] = name_to_id.get(raw_source.lower(), raw_source)


    # Transaction Handler
    def recompute_locked_source_amounts(self, source_ids=None):
        """Lock PaymentSource rows and set amount = opening_amount + ledger_sum."""
        qs = PaymentSource.objects.for_user(self.uid)
        if source_ids is not None:
            qs = qs.filter(source_id__in=list(source_ids))
        locked = list(qs.select_for_update())
        for source in locked:
            self.fc.apply_opening_plus_ledger(source)
        if locked:
            PaymentSource.objects.bulk_update(locked, ["amount"])
        self.sources = list(PaymentSource.objects.for_user(self.uid))
        return locked

    def _lock_bills_by_name(self, names):
        if not names:
            return []
        return list(
            UpcomingExpense.objects.for_user(self.uid).filter(name__in=list(names)).select_for_update()
        )

    def apply_bill_effects(self, update=None):
        """Roll bill due dates / paid flags; does not touch PaymentSource.amount."""
        updated_bill = False
        if update:
            updated_bill = self._handle_tx_update(update)

        bills_to_settle = getattr(self, "paid_bills", set()) or set()
        if update and getattr(update, "bill", None):
            bills_to_settle = bills_to_settle - {update.bill}

        if bills_to_settle:
            locked_bills = self._lock_bills_by_name(bills_to_settle)
            locked_by_name = {bill.name: bill for bill in locked_bills}
            self.unpaid = [locked_by_name[name] for name in bills_to_settle if name in locked_by_name]
            self._handle_upcoming(updated_bill)
        elif updated_bill:
            updated_bill.save()
        return updated_bill

    def transaction_handler(self, update=None):
        """Apply transaction effects to sources, upcoming bills, and snapshots."""
        self.apply_bill_effects(update=update)
        source_ids = {tx.source for tx in self.transactions if getattr(tx, "source", None)}
        if update and getattr(update, "source", None):
            source_ids.add(update.source)
        self.recompute_locked_source_amounts(source_ids or None)
        return self._tx_snapshot_handler()


    # Expense Handlers
    def expense_handler(self, old_name=None, new_name=None):
        """Sync transactions/snapshot fields after expense changes."""
        if old_name:
            txs = Transaction.objects.for_user(self.uid).filter(bill=old_name)
            if new_name:
                txs.update(bill=new_name)
            else:
                txs.update(bill='unknown')
        accounts = [source for source in self.sources if source.source_id in self.spend_accounts]
        debts = self._bills_unpaid_due_in_profile_current_month()
        self.snapshots.safe_to_spend = self.fc.calc_sts(accounts, debts)
        self.snapshots.total_remaining_expenses = self.fc.calc_upcoming_bills_base_total(debts)
        self.snapshots.save()
        return self.snapshots


    # Category Handlers
    def category_changed(self, cat_name, new_name):
        """Rename transaction category references after category rename."""
        affected = Transaction.objects.for_user(self.uid).filter(category=cat_name)
        affected.update(category=new_name)
        return

    def category_deleted(self, cat_name):
        """Map removed category references back to each transaction type default."""
        affected = list(Transaction.objects.for_user(self.uid).filter(category=cat_name))
        for item in affected:
            item.category = item.tx_type.lower()
        if affected:
            Transaction.objects.for_user(self.uid).bulk_update(affected, ["category"])
        return


    # Source Handlers
    def source_handler(self):
        """Recalculate snapshot totals after source create/update/delete."""
        logger.debug(f"Recalculating snapshot totals after source change for {self.uid}")
        acc_totals = self.fc.calc_acc_types(self.sources)
        for total, value in acc_totals.items():
            if hasattr(self.snapshots, total):
                setattr(self.snapshots, total, value)

        # calc_acc_types mutates balances in memory; use DB-fresh rows for STS / assets.
        fresh_sources = list(PaymentSource.objects.for_user(self.uid))
        accounts = [s for s in fresh_sources if s.source_id in self.spend_accounts]
        debts = self._bills_unpaid_due_in_profile_current_month()
        self.snapshots.safe_to_spend = self.fc.calc_sts(accounts, debts)
        self.snapshots.total_assets = self.fc.calc_total_assets(fresh_sources)
        self.snapshots.total_remaining_expenses = self.fc.calc_upcoming_bills_base_total(debts)
        self.snapshots.save()
        return self.snapshots

    
    # User Handler
    def user_handler(self):
        """Recompute snapshot fields after profile-level updates."""
        logger.debug(f"Recalculating snapshot totals after profile update for {self.uid}")
        # Per-account-type totals (total_cash, total_ewallet, …) must be recomputed in the
        # new base currency — same as source_handler. calc_acc_types mutates source.amount
        # in memory; reload sources before safe_to_spend / total_assets.
        acc_totals = self.fc.calc_acc_types(self.sources)
        for total, value in acc_totals.items():
            if hasattr(self.snapshots, total):
                setattr(self.snapshots, total, value)

        fresh_sources = list(PaymentSource.objects.for_user(self.uid))
        debts = self._bills_unpaid_due_in_profile_current_month()
        spend_accounts = [
            s for s in fresh_sources if s.source_id in self.spend_accounts
        ]
        self.snapshots.safe_to_spend = self.fc.calc_sts(spend_accounts, debts)
        self.snapshots.total_assets = self.fc.calc_total_assets(fresh_sources)
        self.snapshots.total_monthly_spending = self.fc.calc_current_month_expense_spending()
        self.snapshots.total_remaining_expenses = self.fc.calc_upcoming_bills_base_total(debts)
        self.snapshots.save()
        return self.snapshots


    # Helper functions
    def _handle_upcoming(self,updated_bill=False):
        """Mark paid bills and roll recurring due dates when transactions settle them."""
        to_update = []
        if updated_bill:
            to_update.append(updated_bill)

        for bill in self.unpaid:
            if bill.name not in self.paid_bills:
                continue
            covering_dates = []
            for tx in getattr(self, "transactions", []):
                if getattr(tx, "bill", None) != bill.name:
                    continue
                raw = getattr(tx, "date", None)
                if isinstance(raw, str):
                    raw = parse_date(raw)
                if raw:
                    covering_dates.append(raw)
            if covering_dates and bill.due_date and bill.due_date > max(covering_dates):
                # Another concurrent settler already rolled this due date forward.
                continue
            to_update.append(bill)

            # Flip the 'is recurring' if the end date has passed
            if bill.end_date and datetime.now(self.timezone).date() >= bill.end_date:
                bill.is_recurring = False
                bill.paid_flag = True
            elif bill.is_recurring:
                from finance.logic.bill_recurrence import advance_bill_due_date

                advance_bill_due_date(bill, periods=1)
                bill.paid_flag = False
            else:
                bill.paid_flag = True

        # Update whatever was changed
        self.upcoming.bulk_update(to_update, ['paid_flag', 'due_date', 'is_recurring'])
        return
    
    def _handle_tx_update(self, tx):
        """Reverse old bill settlement so the replacement payload can be applied cleanly."""
        if not getattr(tx, "bill", None):
            return False
        append_change = False
        locked = self._lock_bills_by_name({tx.bill})
        affected_bill = next((bill for bill in locked if bill.name == tx.bill), None)
        if not affected_bill:
            return False
        from finance.logic.bill_recurrence import subtract_interval_from_date

        prior_due = subtract_interval_from_date(affected_bill.due_date, affected_bill, periods=1)
        if prior_due <= tx.date:
            affected_bill.paid_flag = False
            affected_bill.due_date = prior_due
        if affected_bill.end_date and affected_bill.due_date <= affected_bill.end_date:
            affected_bill.is_recurring = True
        if not self.paid_bills:
            affected_bill.save()
        else:
            append_change = affected_bill
        return append_change
    
    def _tx_snapshot_handler(self):
        """Rebuild snapshot totals from current source/transaction state."""
        # Same bill list for STS debt and total_remaining_expenses (unpaid, due this month).
        bills = self._bills_unpaid_due_in_profile_current_month()
        # Leak metric must reflect full persisted transfer history, not only the
        # in-flight mutation batch.
        transfers = list(
            Transaction.objects.for_user(self.uid).filter(tx_type__in=["XFER_IN", "XFER_OUT"])
        )
        type_totals = self.fc.calc_acc_types(self.sources)
        # calc_acc_types mutates source.amount in memory to base currency while
        # leaving source.currency unchanged — same pattern as source_handler /
        # user_handler: reload DB rows before total_assets and safe_to_spend.
        fresh_sources = list(PaymentSource.objects.for_user(self.uid))
        spend_names = self.profile.spend_accounts
        spend_accounts = [s for s in fresh_sources if s.source_id in spend_names]
        self.snapshots.total_assets = self.fc.calc_total_assets(fresh_sources)
        self.snapshots.safe_to_spend = self.fc.calc_sts(spend_accounts, bills)
        self.snapshots.total_leaks = self.fc.calc_leaks(transfers) if transfers else Decimal("0.00")
        self.snapshots.total_monthly_spending = self.fc.calc_current_month_expense_spending()
        self.snapshots.total_remaining_expenses = self.fc.calc_upcoming_bills_base_total(bills)
        for total in type_totals:
            setattr(self.snapshots, total, type_totals[total])
        self.snapshots.save()
        return self.snapshots

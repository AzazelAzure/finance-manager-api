"""
This module functions as the data manipulation layer for the financial manager application.

Attributes:
    new_transaction: Handles new transactions.
    transaction_updated: Handles transaction updates.
    rebalance: Rebalances the user's accounts.
"""

from datetime import datetime

from finance.logic.fincalc import Calculator
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

# TODO:  Docstrings... again

class Updater:
    """
    Class to handle data manipulation for the finance manager application.

    Required Params:
        - profile: The user AppProfile queryset
        - sources: The PaymentSource queryset
        - currencies: The Currency queryset


    Optional Params:
        - transactions: The Transaction queryset
        - assets: The CurrentAsset queryset


    Conditional Params:
        If Transactions:
            - tags: Tags queryset
            - upcoming: UpcomingExpense queryset

    """
    def __init__(self, profile, **kwargs):
        
        # Required arguments
        self.profile = profile
        

        # Ease for profile to set applicable info
        self.uid = self.profile.user_id
        self.base_currency = self.profile.base_currency
        self.spend_accounts = self.profile.spend_accounts
        self.timezone = zoneinfo.ZoneInfo(self.profile.timezone)
        
        
        # Situational settings
        if kwargs.get('transactions'):
            self.transactions = kwargs.get('transactions')
            self.upcoming = kwargs.get('upcoming') or UpcomingExpense.objects.for_user(self.uid)
            self.sources = list(PaymentSource.objects.for_user(self.uid))
            self.paid_bills = set(tx.bill for tx in self.transactions if tx.bill)
            self.unpaid = list(self.upcoming.filter(paid_flag=False))
            self.spend_accounts = list(source for source in self.sources if source.source in self.spend_accounts)
            
        if kwargs.get('sources'):
            self.sources = kwargs.get('sources')

        if kwargs.get('upcoming'):
            self.sources = kwargs.get('sources') or [PaymentSource.objects.for_user(self.uid)]
            self.upcoming = kwargs.get('upcoming')

        # Single hit for any user, always used
        self.snapshots = FinancialSnapshot.objects.for_user(self.uid).first()
        
        # Create the calculator instance
        self.fc = Calculator(self.profile)
        return


    # Data fixers
    def fix_tx_data(self, data):
        for item in data:
            item['uid'] = self.profile.user_id
            item['amount'] = abs(Decimal(item['amount']))
            item['currency'] = item['currency'].upper()
            item['source'] = item['source'].lower()
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
        for item in data:
            item['uid'] = self.profile.user_id
            item['source'] = item['source'].lower()
            item['acc_type'] = item['acc_type'].upper()
            if item.get('currency'):
                item['currency'] = data['currency'].upper()
            if item.get('amount'):
                item['amount'] = Decimal(item['amount'])
        return data
    
    def fix_expense_data(self, data):
        for item in data:
            item['uid'] = self.profile.user_id
            item['name'] = item['name'].lower()
            item['currency'] = item['currency'].upper()
            


    # Transaction Handler
    def transaction_handler(self, update=None):
     
        updated_bill = False
        if update:
            updated_bill = self._handle_tx_update(update)
        if self.paid_bills:
            self._handle_upcoming(updated_bill)
        src_amounts = self.fc.calc_tx_sources(self.transactions, self.sources)
        for source in self.sources:
            if source.source in src_amounts:
                source.amount = src_amounts[source.source]
        PaymentSource.objects.for_user(self.uid).bulk_update(self.sources, ['amount'])
        snapshot = self._tx_snapshot_handler()
        return snapshot


    # Expense Handlers
    def expense_handler(self, old_name=None, new_name=None):
        if old_name:
            txs = Transaction.objects.for_user(self.uid).filter(bill=old_name)
            if new_name:
                txs.update(bill=new_name)
            else:
                txs.update(bill='unknown')
        accounts = [source for source in self.sources if source.source in self.spend_accounts]
        debts = list(self.upcoming.get_current_month().filter(paid_flag=False))
        self.snapshots.safe_to_spend = self.fc.calc_sts(accounts, debts)
        self.snapshots.save()
        return self.snapshots


    # Category Handlers
    def category_changed(self, cat_name, new_name):
        affected = Transaction.for_user(self.uid).filter(category=cat_name)
        affected.update(category=new_name)
        return

    def category_deleted(self, cat_name):
        affected = list(Transaction.for_user(self.uid).filter(category=cat_name))
        for item in affected:
            item.category = item.tx_type.lower()
        affected.bulk_update(affected, ['category'])
        return


    # Source Handlers
    def source_handler(self):
        logger.debug(f"Source added for {self.uid}")
        acc_totals = self.fc.calc_acc_types(self.sources)
        for total in self.snapshots:
            logger.debug(f'Source added updating snapshot for total: {total}')
            if total in acc_totals:
                logger.debug(f'Succesfully updated snapshot for total: {total}')
                self.snapshots[total] = acc_totals[total]

        accounts = list(source for source in self.sources if source.source in self.spend_accounts)
        debts = [UpcomingExpense.objects.for_user(self.uid).get_current_month().filter(paid_flag=False)]
        self.snapshots.safe_to_spend = self.fc.calc_sts(accounts, debts)
        self.snapshots.total_assets = self.fc.calc_total_assets(self.sources)
        self.snapshots.save()
        return self.snapshots

    
    # User Handler
    def user_handler(self):
        logger.debug(f'User updated for {self.uid}')
        debts = list(UpcomingExpense.objects.for_user(self.uid).get_current_month().filter(paid_flag=False))
        self.snapshots.safe_to_spend = self.fc.calc_sts(self.sources, debts)
        self.total_assets = self.fc.calc_total_assets(self.sources)
        self.snapshots.save()
        return self.snapshots


    # Helper functions
    def _handle_upcoming(self,updated_bill=False):
        

        to_update = []
        if updated_bill:
            to_update.append(updated_bill)

        for bill in self.unpaid:
            if bill.name in self.paid_bills:
                to_update.append(bill)

                # Flip the 'is recurring' if the end date has passed
                if bill.end_date and datetime.now(self.timezone).date() >= bill.end_date:
                    bill.is_recurring = False
                    bill.paid_flag = True
                
                # If this is recurring, move the due date up one month
                if bill.is_recurring:
                    bill.due_date = bill.due_date + relativedelta(months=1)

        # Update whatever was changed
        self.upcoming.bulk_update(to_update, ['paid_flag', 'due_date', 'is_recurring'])
        return
    
    def _in_current_month(self, date):
        now = datetime.now(self.timezone).date()
        return date.month == now.month and date.year == now.year
    
    def _handle_tx_update(self, tx):
        append_change = False
        affected_bill = next((bill for bill in self.unpaid if bill.name == tx.bill), None)
        if affected_bill:
            if affected_bill.due_date - relativedelta(months=1) <= tx.date:
                affected_bill.paid_flag = False
                affected_bill.due_date = affected_bill.due_date - relativedelta(months=1)
            if affected_bill.end_date and affected_bill.due_date <= affected_bill.end_date:
                affected_bill.is_recurring = True
            if not self.paid_bills:
                affected_bill.save()
            else:
                append_change = affected_bill
        affected_source = next((source for source in self.sources if source.source == tx.source), None)
        if affected_source:
            tx.amount = tx.amount * -1
            affected_source.amount += tx.amount
        return append_change
    
    def _tx_snapshot_handler(self):
        debt_list = {
            bill.name: bill 
            for bill in self.unpaid 
            if bill.is_recurring==True and self._in_current_month(bill.due_date)
            }
        transfers = [item for item in self.transactions if item.tx_type in ['XFER_IN', 'XFER_OUT']]
        type_totals = self.fc.calc_acc_types(self.sources)
        self.snapshots.total_assets = self.fc.calc_total_assets(self.sources)
        self.snapshots.safe_to_spend = self.fc.calc_sts(self.spend_accounts, debt_list)
        if transfers:
            self.snapshots.leaks = self.fc.calc_leaks(transfers)
        for total in type_totals:
            setattr(self.snapshots, total, type_totals[total])
        self.snapshots.save()
        return self.snapshots

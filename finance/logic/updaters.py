"""
This module functions as the data manipulation layer for the financial manager application.

Attributes:
    new_transaction: Handles new transactions.
    transaction_updated: Handles transaction updates.
    rebalance: Rebalances the user's accounts.
"""

from finance.logic.fincalc import Calculator
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from django.db.models.functions import Abs
from django.utils import timezone
from finance.models import (
    Tag,
    Transaction, 
    PaymentSource,
    FinancialSnapshot,
    UpcomingExpense
)
from loguru import logger
import uuid

# TODO: In order:
    # Fix Transaction Handling
    # Fix Source handling
    # Fix Snapshot handling
    # Docstrings absolutely last



# TODO:  Docstrings... again

# TODO: Finish fixing changes for new linking system and other refactors

# TODO: Fix transaction updates to account for affecting sources
    # TODO: This will require some changes in fincalc

# TODO: Refactor snapshot calculations to reduce separate calls to one

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
        self.base_currency = self.profile.base_currency.code
        self.spend_accounts = self.profile.spend_accounts
        
        
        # Situational settings
        if kwargs.get('transactions'):
            self.transactions = kwargs.get('transactions')
            self.upcoming = kwargs.get('upcoming') or UpcomingExpense.objects.for_user(self.uid)
            self.sources = list(PaymentSource.objects.for_user(self.uid))
            self.paid_bills = set(tx.bill for tx in self.transactions if tx.bill)
            self.unpaid = list(self.upcoming.filter(paid_flag=False))
            self.spend_accounts = set(source for source in self.sources if source.source in self.spend_accounts)
            
        if kwargs.get('sources'):
            self.sources = kwargs.get('sources')

        if kwargs.get('source_type'):
            self.source_type = kwargs.get('source_type')

        if kwargs.get('souce_check'):
            self.source_check = kwargs.get('source_check')
        
        if kwargs.get('upcoming_check'):
            self.upcoming_check = kwargs.get('upcoming_check')

        # Single hit for any user, always used
        # TODO: Move this to a conditional grab
        self.snapshots = FinancialSnapshot.objects.for_user(self.uid).first()
        
        # Create the calculator instance
        self.fc = Calculator(self.profile)
        return

    # Data fixers
    def fix_tx_data(self, data):
        for item in data:
            item['uid'] = self.profile.user_id
            item['amount'] = Decimal(Abs(item['amount']))
            item['currency'] = item['currency'].upper()
            item['source'] = item['source'].lower()
            if item['tx_type'] in ['EXPENSE', 'XFER_OUT']:
                item['amount'] = item['amount'] * -1
            if not item['date']:
                item['date'] = timezone.now(self.profile.timezone).date()
            if not item['created_on']:
                item['created_on'] = timezone.now(self.profile.timezone).date()
            if not item['tx_id']:
                date_suffix = timezone.now(self.profile.timezone).date()
                unique_id = str(uuid.uuid4())[:8].upper()
                item['tx_id'] = f"{date_suffix}-{unique_id}"
            if not item['category']:
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

    # Transaction Handlers
    def new_transaction(self):
        """
        Function to handle new transactions.
        
        :param uid: The user id.
        :type uid: str
        :param transaction_queryset: A queryset of a transaction
        :type transaction_queryset: queryset
        :returns: None
        """
        self._recalc_source_amount()
        self._handle_upcoming()
        self.rebalance(acc_type=True)
        return

    def transaction_updated(self):
        """
        Function to handle transaction updates.
        Reverses the transaction effect to user account.
        If bill was changed, checks if the transaction is past due and updates the bill.
        
        :param uid: The user id.
        :type uid: str
        :param tx_id: The transaction id.
        :type tx_id: str
        :returns: None
        """

        tx = self.transactions.get()
        # If bill was changed, check if transaction is past the adjusted due date
        if tx.bill: 
            # This decides if anything SHOULD be changed.
            # Since on payment, it pushes the duedate up one month automatically
            # We check if we undid that change would this tx have paid it.
            # This makes sure if this tx is older than the current billing cycle
            # Nothing is changed
            self._updated_affected_upcomings(tx)

        # Invert transaction amount and recalculate
        tx.amount = tx.amount * -1
        tx.save()
        self._recalc_asset_amount()
        self.rebalance(acc_type=True)
        return


    def transaction_handler(self, update=None):
        # 1.  Check if transfer was passed in
            # If passed handle undoing the transaction
            # Since this no longer hits two models, should just be checking bill status
            # And reversing the amount in that account
        # 2. Check if self.transactions has bill
            # If it does, handle that
        # 3. Handle affected sources and recalc them
        # 4 Update snapshot
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
        snapshot = self.snapshot_handler()
        return snapshot

    def snapshot_handler(self):
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
        for total in self.snapshots:
            if total in type_totals:
                self.snapshots[total] = type_totals[total]
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
    def source_added(self):
        # This will take the sources passed in when initialized
        # Iterate over the sources, and update calculation based on acc type
        # I may make a special calculator for this, or just the queryset calc
        # It really depends on how my calculator refactor goes
        # I need to make calculations and updates more efficient
        return

    def source_deleted(self):
        # This is turbo fucked, fix this
        # Will need separate for if it's updated.
            # Will require thoughts on how to handle this
            # If user wants all transactions to follow it
            # Or for them to remain there.
            # New function, with a passed "transfer" bool
                # If not passed, assume to move to "unknown"
        return
    
    def source_updated(self, transfer=False):
        # This will require a top down refactor for this particular bool
        # Basically a if transfer isn't false, set to transfer
        # else, move them all to "unknown"
        return


    # Slated for deletion
    # Rebalance Handler
    def rebalance(self,acc_type=False, total_assets=True, leaks=True, sts=True):
        """
        Rebalances the user's accounts.
        
        :param uid: The user id.
        :type uid: str
        :param acc_type: The account type to rebalance.
        :type acc_type: str
        :returns: None
        """
        logger.debug(f"Rebalancing.  Acc_type is {acc_type}")

        # Recalculate asset type if provided
        # Ordered this way due to how calculations are done
        # TODO: This is getting gutted to handle specific cases
            # Case 1: Transaction cases
                # Added new transactions
                # Updated transaction
            # Case 2: Source cases
                # Added new sources
                # Deleted sources
                # Updated sources
            # Has to be handled this way to reduce/remove N+1 calculations
            # Also fix snapshot calculations to handle all necessary updates in ONE update
            # Reduced hits from 4+ to 2 maximum.
                # Once to get the snapshot, the second to save the new values
        if acc_type:
            self._recalc_asset_type()
        if total_assets:
            self._recalc_total_assets()
        if leaks:
            self._recalc_leaks()
        if sts:
            self._recalc_sts()
        return

        

    # Private Functions

    # Functions slated for deletion
    def _recalc_sts(self):
        """
        Recalculates the safe to spend for a user and sets to Financial Snapshot.
        """
        logger.debug(f"Recalculating safe to spend for {self.uid}")
        # Calc the new safe to spend total
        sts = self.fc.calc_sts() 

        # Update FinancialSnapshot
        self.snapshots.update(safe_to_spend=sts)
        logger.warning(f"Changed safe to spend to: {sts}")
        return

    def _recalc_total_assets(self):
        """
        Recalculates the total assets for a user and sets to Financial Snapshot.
        """
        logger.debug(f"Recalculating total assets for {self.uid}")
        total_assets = self.fc.calc_total_assets() 
        self.snapshots.update(total_assets=total_assets)
        logger.warning(f"Changed total assets to: {total_assets}")
        return

    def _recalc_source_amount(self):
        """
        Recalculates the asset amount for a source.
        """
        logger.debug(f"Recalculating asset amount with source {source} ")
        
        affected_sources = self.transactions.values_list('source', flat=True).distinct()
        logger.debug(f"Affected sources: {affected_sources}")

        for source in affected_sources: 
            # TODO: Monitor for validity
            aggregate = self.fc.calc_queryset(self.transactions.filter(source=source))                
            source.amount = self.fc.calc_new_balance(self.sources.filter(source=source), aggregate)
        self.sources.bulk_update(affected_sources, ['amount'])
        return

    def _updated_affected_upcomings(self, tx):

            # Check if paid flag should be changed
            if tx.date >= tx.bill.due_date - relativedelta(months=1):
                tx.bill.paid_flag = False
                tx.bill.due_date = tx.bill.due_date - relativedelta(months=1)
            
            # Check if current due date is before the end date
            # If it is, fix the is recurring
            if tx.bill.end_date and tx.bill.due_date <= tx.bill.end_date:
                tx.bill.is_recurring = True
            
            tx.bill.save()
            return

    # Used functions
    def _handle_upcoming(self,updated_bill=False):
        

        to_update = []
        if updated_bill:
            to_update.append(updated_bill)

        for bill in self.unpaid:
            if bill.name in self.paid_bills:
                to_update.append(bill)

                # Flip the 'is recurring' if the end date has passed
                if bill.end_date and timezone.now(self.profile.timezone).date() >= bill.end_date:
                    bill.is_recurring = False
                    bill.paid_flag = True
                
                # If this is recurring, move the due date up one month
                if bill.is_recurring:
                    bill.due_date = bill.due_date + relativedelta(months=1)

        # Update whatever was changed
        self.upcoming.bulk_update(to_update, ['paid_flag', 'due_date', 'is_recurring'])
        return
    
    def _in_current_month(self, date):
        return date.month == timezone.now(self.profile.timezone).date().month and date.year == timezone.now(self.profile.timezone).date().year
    
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
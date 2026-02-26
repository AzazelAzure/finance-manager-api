"""
This module functions as the data manipulation layer for the financial manager application.

Attributes:
    new_transaction: Handles new transactions.
    transaction_updated: Handles transaction updates.
    rebalance: Rebalances the user's accounts.
"""

import finance.logic.fincalc as fc
from dateutil.relativedelta import relativedelta
from finance.models import (
    Transaction, 
    CurrentAsset, 
    AppProfile,
    PaymentSource,
    FinancialSnapshot,
    Currency,
    UpcomingExpense
)
from loguru import logger

class Updaters:
    """
    Class to handle data manipulation for the finance manager application.
    """
    def __init__(self, uid, **kwargs):
        self.profile = AppProfile.objects.for_user(uid)
        self.uid = uid
        self.assets = kwargs.get("assets") or CurrentAsset.objects.for_user(uid)
        self.transactions = kwargs.get('transactions') or Transaction.objects.for_user(uid)
        self.sources = kwargs.get('sources') or PaymentSource.objects.for_user(uid)
        self.snapshots = kwargs.get('snapshots') or FinancialSnapshot.objects.for_user(uid)
        self.currencies = kwargs.get('currencies') or Currency.objects.for_user(uid)
        self.upcoming = kwargs.get('upcoming') or UpcomingExpense.objects.for_user(uid)


    def new_transaction(self):
        """
        Function to handle new transactions.
        
        :param uid: The user id.
        :type uid: str
        :param transaction_queryset: A queryset of a transaction
        :type transaction_queryset: queryset
        :returns: None
        """
        if isinstance(self.transactions, list):
            for tx in self.transactions:
                self._recalc_asset_amount(tx.source, tx.amount, tx.currency.code)
                self.rebalance(tx.source.acc_type)
            return
        else:
            self._recalc_asset_amount(self.transactions.source, self.transactions.amount, self.transactions.currency.code)
            self.rebalance(self.transactions.source.acc_type)
            return


    def transaction_updated(uid, tx_id: str):
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
        tx = Transaction.objects.for_user(uid).get_tx(tx_id)

        # If bill was changed, check if transaction is past due
        if tx.bill: # TODO: This is likely fine, but verify
            if tx.date >= (tx.bill.due_date - relativedelta(months=1)):
                tx.bill.paid_flag = False
                tx.bill.due_date = tx.bill.due_date - relativedelta(months=1)
                tx.bill.save()

        # Invert transaction amount and recalculate
        multiplier = -1 if tx.tx_type in ["EXPENSE", "XFER_OUT"] else 1
        tx_amount = tx.amount * multiplier
        _recalc_asset_amount(uid, tx.source, tx_amount, tx.currency.code)
        rebalance(uid, tx.source.acc_type)
        return

    def rebalance(uid, acc_type=None):
        """
        Rebalances the user's accounts.
        
        :param uid: The user id.
        :type uid: str
        :param acc_type: The account type to rebalance.
        :type acc_type: str
        :returns: None
        """
        logger.debug(f"Rebalancing {uid} with acc_type {acc_type}")

        # Recalculate asset type if provided
        # Ordered this way due to how calculations are done
        if acc_type:
            _recalc_asset_type(uid, acc_type)
        _recalc_total_assets(uid)
        _recalc_leaks(uid)
        _recalc_sts(uid)
        return


    def _recalc_sts(uid):
        """
        Recalculates the safe to spend for a user and sets to Financial Snapshot.
        """
        logger.debug(f"Recalculating safe to spend for {uid}")
        # Get spend accounts
        spend_accounts = AppProfile.objects.for_user(uid).get_spend_accounts(uid)
        logger.debug(f"Spend accounts: {spend_accounts.uidaccounts}")
        # Convert to tuple
        spend_accounts = tuple(spend_accounts)
        sts = fc.calc_sts(uid, spend_accounts)
        logger.warning(f"Changed safe to spend to: {sts}")
        # Update FinancialSnapshot
        FinancialSnapshot.objects.for_user(uid).update(safe_to_spend=sts)
        return


    def _recalc_total_assets(uid):
        """
        Recalculates the total assets for a user and sets to Financial Snapshot.
        """
        logger.debug(f"Recalculating total assets for {uid}")
        total_assets = fc.calc_total_assets(uid)
        FinancialSnapshot.objects.for_user(uid).update(total_assets=total_assets)
        logger.warning(f"Changed total assets to: {total_assets}")
        return


    def _recalc_asset_type(uid, acc_type):
        """
        Recalculates the total assets for a specific account type and sets to Financial Snapshot.
        """
        acc_type = acc_type.acc_type
        logger.debug(f"Recalculating asset type {acc_type} for {uid}")
        asset = fc.calc_asset_type(uid, acc_type)
        FinancialSnapshot.objects.for_user(uid).set_totals(acc_type, asset)
        return


    def _recalc_leaks(uid):
        """
        Recalculates the leaks for a user and sets to Financial Snapshot.
        """
        logger.debug(f"Recalculating leaks for {uid}")
        leaks = fc.calc_leaks(uid)
        FinancialSnapshot.objects.for_user(uid).update(total_leaks=leaks)
        return

    def _recalc_asset_amount(uid, source, amount, currency):
        """
        Recalculates the asset amount for a source and sets to CurrentAsset.
        """
        logger.debug(f"Recalculating asset amount for {uid} with source {source} and amount {amount}")
        asset = CurrentAsset.objects.for_user(uid).get_asset(source)
        new_balance = fc.calc_new_balance(uid, source, amount, currency)
        asset.amount = new_balance
        asset.save()
        return


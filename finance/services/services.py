# TODO: Update docstrings
# TODO: Update logging


import finance.logic.validators as validator
import finance.logic.updaters as update
import finance.logic.fincalc as fc
from django.db import transaction
from loguru import logger
from finance.models import (
    Transaction, 
    PaymentSource, 
    CurrentAsset,
    UpcomingExpense, 
    Tag, 
    AppProfile,
    FinancialSnapshot,
    Currency
)

# Transaction Functions
@transaction.atomic
@validator.TransactionValidator
@validator.UserValidator
def user_add_transaction(uid,data:dict):
    return _user_add_transaction(uid, data)

@transaction.atomic
@validator.BulkTransactionValidator
@validator.UserValidator
def user_add_bulk_transactions(uid, data: list):
    logger.debug(f"Adding bulk transactions: {data}")
    for item in data:
        logger.debug(f"Adding transaction: {item}")
        _user_add_transaction(uid, item)
    return {'message': "Bulk transactions added successfully"}

@transaction.atomic
@validator.TransactionValidator
@validator.TransactionIDValidator
@validator.UserValidator
def user_update_transaction(uid, tx_id: str, data: dict):
    logger.debug(f"Updating transaction: {data}")
    update.transaction_updated(uid=uid, tx_id=tx_id)
    tx = Transaction.objects.for_user(uid).get_tx(tx_id)
    tx.update(**data)
    update.new_transaction(uid=uid, tx_id=tx.tx_id)
    return {f'message': "{tx_id} updated successfully"}

@transaction.atomic
@validator.TransactionIDValidator
@validator.UserValidator
def user_delete_transaction(uid, tx_id: str):
    logger.debug(f"Deleting transaction: {tx_id}")
    update.transaction_updated(uid=uid, tx_id=tx_id)
    tx = Transaction.objects.for_user(uid).get_tx(tx_id)
    tx.delete()
    return {f'message': "Deleted {tx_id} successfully"}

@transaction.atomic
@validator.TransactionIDValidator
@validator.UserValidator
def user_get_transaction(uid, tx_id: str):
    logger.debug(f"Getting transaction: {tx_id} for {uid}")
    tx = Transaction.objects.for_user(uid).get_tx(tx_id)
    return {'transaction': tx}

@transaction.atomic
@validator.TransactionIDValidator
@validator.UserValidator
def user_get_all_transactions(uid):
    logger.debug(f"Getting transactions for {uid}")
    txs = Transaction.objects.for_user(uid).all()
    return {'transactions': txs, 'amount': _user_get_total_all_transactions(uid)}

@transaction.atomic
@validator.UserValidator
def user_get_transactions_month(uid):
    logger.debug(f"Getting current month transactions for {uid}")
    txs = Transaction.objects.for_user(uid=uid).get_current_month()
    return {'transactions': txs, 'amount': _user_get_total_monthly_spending(uid)}

@transaction.atomic
@validator.UserValidator
def user_get_transactions_by_type(uid, tx_type: str):
    logger.debug(f"Getting transactions by type: {tx_type} for {uid}")
    txs = Transaction.objects.for_user(uid=uid).get_by_tx_type(tx_type)
    return {'transactions': txs, 'amount': _user_get_total_by_type(uid, tx_type)}

@transaction.atomic
@validator.UserValidator
def user_get_tranactions_by_period(uid, start_date, end_date):
    logger.debug(f"Getting transactions by period: {start_date} to {end_date} for {uid}")
    txs = Transaction.objects.for_user(uid=uid).get_by_period(start_date, end_date)
    return {'transactions': txs, 'amount': _user_get_total_by_period(uid, start_date, end_date)}


# Asset Functions
@transaction.atomic
@validator.BulkAssetValidator
@validator.UserValidator
def user_bulk_update_assets(uid, data: list):
    logger.debug(f"Adding bulk assets: {data}")
    for item in data:
        logger.debug(f"Adding asset: {item}")
        _user_update_asset(uid, item)
    return {'message': "Bulk assets updated successfully"}

@transaction.atomic
@validator.AssetValidator
@validator.UserValidator
def user_update_asset_source(uid, data:dict):
    return _user_update_asset(uid, data)

@transaction.atomic
@validator.UserValidator
def user_get_asset(uid, source: str, currency: str):
    logger.debug(f"Getting asset: {source} for {uid}")
    asset = CurrentAsset.objects.for_user(uid).get_asset(source)
    return {'asset': asset}

@transaction.atomic
@validator.UserValidator
def user_get_all_assets(uid):
    logger.debug(f"Getting all assets for {uid}")
    assets_queryset = CurrentAsset.objects.for_user(uid).all()
    # Transform the QuerySet into a list of dictionaries with source and amount
    formatted_assets = [{'source': asset.source.source, 'amount': asset.amount} for asset in assets_queryset]
    return {'assets': formatted_assets}

# Payment Source Functions
@transaction.atomic
@validator.AssetValidator
@validator.UserValidator
def user_add_source(uid, data: dict):
    logger.debug(f"Adding asset: {data}")
    uid = AppProfile.objects.for_user(uid).get()
    asset = PaymentSource.objects.create(uid=uid,**data)
    update.rebalance(uid=uid, acc_type=asset.acc_type)
    return {'message': "Payment source added successfully"}


# Upcoming Expense Functions
@transaction.atomic
@validator.UserValidator
def user_add_expense(uid, data: dict):
    logger.debug(f"Adding expense: {data}")
    uid = AppProfile.objects.for_user(uid).get()
    data['uid'] = uid
    UpcomingExpense.objects.create(**data)
    update.rebalance(uid)
    return {'message': "Expense added successfully"}

@transaction.atomic
@validator.UserValidator
@validator.UpcomingExpenseValidator
def user_delete_expense(uid, expense_name: str):
    logger.debug(f"Deleting expense: {expense_name}")
    expense = UpcomingExpense.objects.for_user(uid).get_by_name(expense_name)
    expense.delete()
    update.rebalance(uid)
    return {'message': "Expense deleted successfully"}

@transaction.atomic
@validator.UserValidator
@validator.UpcomingExpenseValidator
def user_update_expense(uid, expense_name: str, data: dict):
    logger.debug(f"Updating expense: {expense_name}")
    expense = UpcomingExpense.objects.for_user(uid).get_by_name(expense_name)
    expense.update(**data)
    update.rebalance(uid)
    return {'message': "Expense updated successfully"}

@transaction.atomic
@validator.UserValidator
@validator.UpcomingExpenseValidator
def user_get_expense(uid, expense_name: str):
    logger.debug(f"Getting expense: {expense_name} for {uid}")
    expense = UpcomingExpense.objects.for_user(uid).get_by_name(expense_name).get()
    return {
        'name': expense.name,
        'estimated_cost': expense.estimated_cost,
        'due_date': expense.due_date,
        'start_date': expense.start_date,
        'end_date': expense.end_date,
        'paid_flag': expense.paid_flag,
        'expense_id': expense.expense_id,
        'status': expense.status,
        'currency': expense.currency.code, # Access the code of the related Currency object
        'is_recurring': expense.is_recurring,
    }

@transaction.atomic
@validator.UserValidator
def user_get_all_expenses(uid):
    logger.debug(f"Getting all expenses for {uid}")
    expenses = UpcomingExpense.objects.for_user(uid).all()
    # Transform the QuerySet into a list of dictionaries with relevant expense fields
    formatted_expenses = []
    for expense in expenses:
        formatted_expenses.append({
            'name': expense.name,
            'estimated_cost': expense.estimated_cost,
            'due_date': expense.due_date,
            'start_date': expense.start_date,
            'end_date': expense.end_date,
            'paid_flag': expense.paid_flag,
            'expense_id': expense.expense_id,
            'status': expense.status,
            'currency': expense.currency.code, # Access the code of the related Currency object
            'is_recurring': expense.is_recurring,
        })
    return formatted_expenses


# Data Getters
@transaction.atomic
@validator.UserValidator
def user_get_totals(uid):
    logger.debug(f"Getting all totals for {uid}")
    assets_queryset = CurrentAsset.objects.for_user(uid).all()
    formatted_assets = [{'source': asset.source.source, 'amount': asset.amount} for asset in assets_queryset]
    return {
        'Snapshot': FinancialSnapshot.objects.for_user(uid).first(), 
        'assets': formatted_assets,
        'total transactions': _user_get_total_all_transactions(uid),
        'total transactions for month': _user_get_total_monthly_spending(uid)
        }


# Private Functions
def _user_add_transaction(uid, data):
    logger.debug(f"Adding transaction: {data} for {uid}")
    tags = data.pop("tags", None)
    tx = Transaction.objects.create(**data) 
    if tags:
        logger.debug("Setting tags.  Tags: {tags}")
        tag_obj = Tag.objects.filter(name__in=tags)
        logger.debug(f"Tag objects: {tag_obj}.  Tag to be set: {tags}")
        tx.tags.set(tag_obj)
    update.new_transaction(uid=uid, tx_id=tx.tx_id)
    return {'message': "Transaction added successfully"}

def _user_update_asset(uid, data):
    logger.debug(f"Updating asset: {data}")
    # Convert string references to objects
    source_obj = PaymentSource.objects.for_user(uid).get_by_source(source=data['source']).get()
    currency_obj = Currency.objects.filter(code=data['currency']).get()
    
    # Update the asset
    asset_instance = CurrentAsset.objects.for_user(uid).get_asset(source=data['source'])
    asset_instance.source = source_obj
    asset_instance.currency = currency_obj
    asset_instance.save()
    update.rebalance(uid=uid, acc_type=asset_instance.source.acc_type)
    return {'message': "Asset updated successfully"}

def _user_get_total_all_transactions(uid):
    logger.debug(f"Getting total for all transactions for {uid}")
    return fc.calc_all_spending_total(uid)

def _user_get_total_monthly_spending(uid):
    logger.debug(f"Getting total for monthly transactions for {uid}")
    return fc.calc_monthly_spending_total(uid)

def _user_get_total_by_type(uid, tx_type):
    logger.debug(f"Getting total for {tx_type} transactions for {uid}")
    return fc.calc_total_by_type(uid, tx_type)

def _user_get_total_by_period(uid, start_date, end_date):
    logger.debug(f"Getting total for transactions between {start_date} and {end_date} for {uid}")
    return fc.calc_total_by_period(uid, start_date, end_date)
"""
This module handles all validation logic for the finance manager application.
Verifies that the data provided is valid, and cleans strings to proper formats.

Attributes:
    TransactionValidator: Decorator to validate a transaction.
    BulkTransactionValidator: Decorator to validate a list of transactions.
    TransactionIDValidator: Decorator to validate a transaction id.
    TransactionTypeValidator: Decorator to validate a transaction type.
    UserValidator: Decorator to validate a user.
    AssetValidator: Decorator to validate an asset.
    BulkAssetValidator: Decorator to validate a list of assets.
    UpcomingExpenseValidator: Decorator to validate an upcoming expense.s
"""

from functools import wraps
from django.core.exceptions import ValidationError
from django.utils import timezone
from finance.models import (
    AppProfile,
    Transaction,
    UpcomingExpense, 
    PaymentSource, 
    Currency, 
    Tag
)
from finance.logic.updaters import Updater
from loguru import logger



# Transaction Validators
def TransactionValidator(func):
    """
    Decorator to validate a transaction.
    Checks if all required fields are valid, and fixes any data that needs to be fixed.
    Raises a ValidationError if any validation fails.
    """
    @wraps(func)
    def _wrapped(uid, data):
        sources = PaymentSource.objects.for_user(uid)
        currencies = Currency.objects.all()
        tags = Tag.objects.for_user(uid)
        upcoming = UpcomingExpense.objects.for_user(uid)
        profile = AppProfile.objects.for_user(uid)
        update = Updater(uid, sources=sources, currencies=currencies, tags=tags, upcoming=upcoming, profile=profile)
        if isinstance(data, list):
            rejected = []
            for item in data:
                logger.debug(f"Validating transaction: {item} with uid: {uid}")
                try:
                    _validate_transaction(uid, item, sources, currencies, tags, upcoming)
                    update.fix_tx_data(data)
                except ValidationError as e:
                    logger.error(f"Transaction validation failed: {e}")
                    rejected.append(item)
            return func(uid, data, rejected)
        logger.debug(f"Validating transaction: {data} with uid: {uid}")
        _validate_transaction(uid, data, sources, currencies, tags, upcoming)
        update.fix_data(data)
        return func(uid, data)
    return _wrapped


def TransactionIDValidator(func):
    """
    Decorator to validate a transaction id.
    Checks if the transaction exists.nsaction.objects.bulk_create([Transaction(**item) for item in data])
    Raises a ValidationError if the transaction does not exist.
    """
    @wraps(func)
    def _wrapped(uid, tx_id: str):
        logger.debug(f"Validating transaction id: {tx_id} with uid: {uid}")
        if not Transaction.objects.for_user(uid).filter(tx_id=tx_id).exists():
            logger.error(f"Transaction does not exist: {tx_id}")
            raise ValidationError("Transaction does not exist")
        return func(uid, tx_id)
    return _wrapped

def TransactionTypeValidator(func):
    """
    Decorator to validate a transaction type.
    Checks if the transaction type exists.
    Raises a ValidationError if the transaction type does not exist.
    """
    @wraps(func)
    def _wrapped(uid, tx_type: str):
        logger.debug(f"Validating transaction type: {tx_type} with uid: {uid}")
        if not Transaction.objects.for_user(uid).filter(tx_type=tx_type).exists():
            logger.error(f"Transaction type does not exist: {tx_type}")
            raise ValidationError("Transaction type does not exist")
        return func(uid, tx_type)
    return _wrapped

# User Validator
def UserValidator(func):
    """
    Decorator to validate a user.
    Checks if the user exists.
    Raises a ValidationError if the user does not exist.
    """
    @wraps(func)
    def _wrapped(uid, data:dict):
        logger.debug(f"Validating user with uid: {uid}")
        if not AppProfile.objects.for_user(uid).exists():
            logger.error(f"User does not exist: {uid}")
            raise ValidationError("User does not exist")
        return func(uid, data)
    return _wrapped

# Asset Validators
def AssetValidator(func):
    """
    Decorator to validate an asset.
    Checks if all required fields are valid.
    Fixes any data that needs to be fixed.
    Raises a ValidationError if any validation fails.
    """
    @wraps(func)
    def _wrapped(uid, data):
        # Currently set up to allow for updating multiple assets
        # Bulk updates are currently not implemented, but framework exists
        sources = PaymentSource.objects.for_user(uid)
        currencies = Currency.objects.all()
        profile = AppProfile.objects.for_user(uid)
        update = Updater(uid, sources=sources, currencies=currencies, profile=profile)
        if isinstance(data, list):
            rejected = []
            for item in data:
                logger.debug(f"Validating asset: {item} with uid: {uid}")
                try:
                    _validate_asset(uid, item, sources, currencies, profile)
                    update.fix_asset_data(data)
                except ValidationError:
                    rejected.append(item)
            return func(uid, data, rejected)
        logger.debug(f"Validating asset: {data} with uid: {uid}")
        _validate_asset(uid, data, sources, currencies, profile)
        update.fix_asset_data(data)
        return func(uid, data)
    return _wrapped

# Upcoming Expense Validators
def UpcomingExpenseValidator(func):
    """
    Decorator to validate an upcoming expense.
    Checks if the expense exists.
    Raises a ValidationError if the expense does not exist.
    """
    @wraps(func)
    def _wrapped(uid, data:dict):
        logger.debug(f"Validating expense: {data} with uid: {uid}")
        if not UpcomingExpense.objects.for_user(uid).filter(name=data['name']).exists():
            logger.error(f"Expense does not exist: {data['name']}")
            raise ValidationError("Expense does not exist")
        return func(uid, data)
    return _wrapped

# Tag Validators
def TagValidator(func):
    """
    Decorator to validate a tag.
    Checks if the tag exists.
    Raises a ValidationError if the tag already exists.
    """
    @wraps(func)
    def _wrapped(uid, data:dict):
        logger.debug(f"Validating tag: {data} with uid: {uid}")
        if Tag.objects.for_user(uid).filter(name=data['name'].lower()).exists():
            logger.error(f"Tag already exists: {data['name']}")
            raise ValidationError("Tag already exists.  Cannot add duplicates")
        return func(uid, data)
    return _wrapped

def SourceValidator(func):
    """
    Decorator to validate a payment source.
    Checks if the source exists.
    Raises a ValidationError if the source does not exist.
    """
    @wraps(func)
    def _wrapped(uid, data:dict):
        logger.debug(f"Validating source: {data} with uid: {uid}")
        if not PaymentSource.objects.for_user(uid).filter(source=data['source']).exists():
            logger.error(f"Source does not exist: {data['source']}")
            raise ValidationError("Source does not exist")
        if data['acc_type'] not in PaymentSource.AccType.choices:
            logger.error(f"Account type does not exist: {data['acc_type']}")
            raise ValidationError("Account type does not exist")
        return func(uid, data)
    return _wrapped

# Private Functions
def _validate_transaction(uid, data:dict, sources, currencies, tags, upcoming):
    logger.debug(f"Validating transaction: {data} with uid: {uid}")
    if not sources.filter(source=data['source']).exists():
        logger.error(f"Source does not exist: {data['source']}")
        raise ValidationError("Source does not exist")
    if not currencies.filter(code=data['currency']).exists():
        logger.error(f"Currency does not exist: {data['currency']}")
        raise ValidationError("Currency does not exist")
    if data.get('tags'):
        for tag in data['tags']:
            if not tags.filter(name=tag).exists():
                logger.warning(f"Tag does not exist: {tag}.  Creating...")
                uid_instance = AppProfile.objects.for_user(uid).get()
                Tag.objects.create(name=tag.lower(), uid=uid_instance)
    if not data.get('date'):
        data['date'] = timezone.now().date()
    if data['date'] > timezone.now().date():
       raise ValidationError("Date cannot be in the future")
    if data.get('bill'):
        if not upcoming.filter(name=data['bill']).exists():
            logger.error(f"Expense does not exist: {data['bill']}")
            raise ValidationError("Expense does not exist")
        if data['tx_type'] != 'EXPENSE':
            logger.error(f"Expense must be an expense: {data['tx_type']}")
            raise ValidationError("Expense must be an expense")
    return data

def _validate_asset(uid, data:dict, sources, currencies, profile):
    logger.debug(f"Validating asset: {data} with uid: {uid}")
    if not sources.filter(source=data['source']).exists():
        logger.error(f"Source does not exist: {data['source']}")
        raise ValidationError("Source does not exist")
    if not currencies.filter(code=data['currency']).exists():
        logger.error(f"Currency does not exist: {data['currency']}")
        raise ValidationError("Currency does not exist")
    return data



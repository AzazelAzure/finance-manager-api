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

from loguru import logger

# Transaction Validators
def TransactionValidator(func):
    """
    Decorator to validate a transaction.
    Checks if all required fields are valid, and fixes any data that needs to be fixed.
    Raises a ValidationError if any validation fails.
    """
    @wraps(func)
    def _wrapped(uid, data:dict):
        logger.debug(f"Validating transaction: {data} with uid: {uid}")
        _validate_transaction(uid, data)
        _fix_data(uid, data)
        return func(uid, data)
    return _wrapped

def BulkTransactionValidator(func):
    """
    Decorator to validate a list of transactions.
    Checks if all required fields are valid, and fixes any dataoes not that needs to be fixed.
    Raises a ValidationError if any validation fails.
    """
    @wraps(func)
    def _wrapped(uid, data:list):
        logger.debug(f"Validating bulk transaction: {data} with uid: {uid}")
        for item in data:
            logger.debug(f"Validating transaction: {item}")
            _validate_transaction(uid, item)
            _fix_data(uid, item)
        return func(uid, data)
    return _wrapped

def TransactionIDValidator(func):
    """
    Decorator to validate a transaction id.
    Checks if the transaction exists.
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
    def _wrapped(uid, data:dict):
        logger.debug(f"Validating asset: {data} with uid: {uid}")
        _validate_asset(uid, data)
        return func(uid, data)
    return _wrapped

def BulkAssetValidator(func):
    """
    Decorator to validate a list of assets.
    Checks if all required fields are valid.
    Fixes any data that needs to be fixed.
    Raises a ValidationError if any validation fails.
    """
    @wraps(func)
    def _wrapped(uid, data:list):
        logger.debug(f"Validating bulk asset: {data} with uid: {uid}")
        for item in data:
            logger.debug(f"Validating asset: {item}")
            _validate_asset(uid, item)
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
def _validate_transaction(uid, data:dict):
    logger.debug(f"Validating transaction: {data} with uid: {uid}")
    if not PaymentSource.objects.for_user(uid).filter(source=data['source']).exists():
        logger.error(f"Source does not exist: {data['source']}")
        raise ValidationError("Source does not exist")
    if not Currency.objects.filter(code=data['currency']).exists():
        logger.error(f"Currency does not exist: {data['currency']}")
        raise ValidationError("Currency does not exist")
    if data.get('tags'):
        for tag in data['tags']:
            if not Tag.objects.for_user(uid).filter(name=tag).exists():
                logger.warning(f"Tag does not exist: {tag}.  Creating...")
                uid_instance = AppProfile.objects.for_user(uid).get()
                Tag.objects.create(name=tag.lower(), uid=uid_instance)
    if not data.get('date'):
        data['date'] = timezone.now().date()
    if data.get('bill'):
        if not UpcomingExpense.objects.for_user(uid).filter(name=data['bill']).exists():
            logger.error(f"Expense does not exist: {data['bill']}")
            raise ValidationError("Expense does not exist")
        # Fix this value here since it's not a required field, to avoid key errors in _fix_data()
        data['bill'] = UpcomingExpense.objects.for_user(uid).get_by_name(data['bill'])
    return data

def _validate_asset(uid, data:dict):
    logger.debug(f"Validating asset: {data} with uid: {uid}")
    if not PaymentSource.objects.for_user(uid).filter(source=data['source']).exists():
        logger.error(f"Source does not exist: {data['source']}")
        raise ValidationError("Source does not exist")
    if not Currency.objects.filter(code=data['currency']).exists():
        logger.error(f"Currency does not exist: {data['currency']}")
        raise ValidationError("Currency does not exist")
    data['uid'] = AppProfile.objects.for_user(uid).get()
    data['currency'] = AppProfile.objects.for_user(uid).get_base_currency()
    data['source'] = PaymentSource.objects.for_user(uid).get_by_source(source=data['source']).get()
    return data

def _fix_data(uid, data:dict):
    logger.debug(f"Fixing data for {uid}")
    data['source'] = PaymentSource.objects.for_user(uid).get_by_source(source=data['source']).get()
    data['currency'] = Currency.objects.for_user(uid).get_by_code(code=data['currency']).get()
    data['uid'] = AppProfile.objects.for_user(uid).get()
    return data


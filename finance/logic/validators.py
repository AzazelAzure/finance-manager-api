from functools import wraps
from django.core.exceptions import ValidationError
from django.utils import timezone
from finance.models import (
    AppProfile,
    Transaction,
    UpcomingExpense, 
    Category, 
    PaymentSource, 
    Currency, 
    Tag
)

from loguru import logger

# TODO: Add Docstrings
# TODO: Add tag validation
# TODO: Fix _fix_data to pull from models directly

# Transaction Validators
def TransactionValidator(func):
    @wraps(func)
    def _wrapped(uid, data:dict):
        logger.debug(f"Validating transaction: {data} with uid: {uid}")
        _validate_transaction(uid, data)
        _fix_data(uid, data)
        return func(uid, data)
    return _wrapped

def BulkTransactionValidator(func):
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
    @wraps(func)
    def _wrapped(uid, tx_id: str):
        logger.debug(f"Validating transaction id: {tx_id} with uid: {uid}")
        if not Transaction.objects.for_user(uid).filter(tx_id=tx_id).exists():
            raise ValidationError("Transaction does not exist")
        return func(uid, tx_id)
    return _wrapped

def TransactionTypeValidator(func):
    @wraps(func)
    def _wrapped(uid, tx_type: str):
        logger.debug(f"Validating transaction type: {tx_type} with uid: {uid}")
        if not Transaction.objects.for_user(uid).filter(tx_type=tx_type).exists():
            raise ValidationError("Transaction type does not exist")
        return func(uid, tx_type)
    return _wrapped

# User Validator
def UserValidator(func):
    @wraps(func)
    def _wrapped(uid, data:dict):
        logger.debug(f"Validating user with uid: {uid}")
        if not AppProfile.objects.for_user(uid).exists():
            raise ValidationError("User does not exist")
        return func(uid, data)
    return _wrapped

# Asset Validators
def AssetValidator(func):
    @wraps(func)
    def _wrapped(uid, data:dict):
        logger.debug(f"Validating asset: {data} with uid: {uid}")
        _validate_asset(uid, data)
        return func(uid, data)
    return _wrapped

def BulkAssetValidator(func):
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
    @wraps(func)
    def _wrapped(uid, data:dict):
        logger.debug(f"Validating expense: {data} with uid: {uid}")
        if not UpcomingExpense.objects.for_user(uid).filter(name=data['name']).exists():
            logger.debug(f"Expense does not exist: {data['name']}")
            raise ValidationError("Expense does not exist")
        return func(uid, data)
    return _wrapped

# Private Functions
def _validate_transaction(uid, data:dict):
    logger.debug(f"Validating transaction: {data} with uid: {uid}")
    if not Category.objects.for_user(uid).filter(name=data['category']).exists():
        logger.debug(f"Category does not exist: {data['category']}")
        raise ValidationError("Category does not exist")
    if not PaymentSource.objects.for_user(uid).filter(source=data['source']).exists():
        logger.debug(f"Source does not exist: {data['source']}")
        raise ValidationError("Source does not exist")
    if not Currency.objects.filter(code=data['currency']).exists():
        logger.debug(f"Currency does not exist: {data['currency']}")
        raise ValidationError("Currency does not exist")
    for tag in data['tags']:
        if not Tag.objects.for_user(uid).filter(name=tag).exists():
            logger.debug(f"Tag does not exist: {tag}.  Creating...")
            uid_instance = AppProfile.objects.for_user(uid).get()
            Tag.objects.create(name=tag, uid=uid_instance)
    if not data.get('date'):
        data['date'] = timezone.now().date()
    return

def _validate_asset(uid, data:dict):
    logger.debug(f"Validating asset: {data} with uid: {uid}")
    if not PaymentSource.objects.for_user(uid).filter(source=data['source']).exists():
        logger.debug(f"Source does not exist: {data['source']}")
        raise ValidationError("Source does not exist")
    if not Currency.objects.filter(code=data['currency']).exists():
        logger.debug(f"Currency does not exist: {data['currency']}")
        raise ValidationError("Currency does not exist")
    return

def _fix_data(uid, data:dict):
    logger.debug(f"Fixing data for {uid}")
    data['category'] = Category.objects.for_user(uid).get_by_name(name=data['category']).get()
    data['source'] = PaymentSource.objects.for_user(uid).get_by_source(source=data['source']).get()
    data['currency'] = AppProfile.objects.for_user(uid).get_base_currency()
    data['uid'] = AppProfile.objects.for_user(uid).get()
    return data


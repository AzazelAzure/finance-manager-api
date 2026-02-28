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
    Tag
)
from finance.logic.updaters import Updater
from loguru import logger
import pycountry
import zoneinfo



# Transaction Validators
def TransactionValidator(func):
    """
    Decorator to validate a transaction.
    Checks if all required fields are valid, and fixes any data that needs to be fixed.
    Raises a ValidationError if any validation fails.
    """
    @wraps(func)
    def _wrapped(uid, data, *args, **kwargs):
        sources = PaymentSource.objects.for_user(uid)
        tags = Tag.objects.for_user(uid)
        upcoming = UpcomingExpense.objects.for_user(uid)
        profile = kwargs.get('profile')
        kwargs['sources'] = sources
        kwargs['tags'] = tags
        kwargs['upcoming'] = upcoming
        update = Updater(transactions=data, sources=sources, tags=tags, upcoming=upcoming, profile=profile)
        if isinstance(data, list):
            rejected = []
            for item in data:
                logger.debug(f"Validating transaction: {item} with uid: {uid}")
                try:
                    _validate_transaction(uid, item, sources, tags, upcoming)
                except ValidationError as e:
                    logger.error(f"Transaction validation failed: {e}")
                    rejected.append(item)
            accepted = [item for item in data if item not in rejected]
            kwargs['rejected'] = rejected
            kwargs['accepted'] = accepted
            update.fix_tx_data(accepted)
            return func(uid, data,  *args, **kwargs)
        logger.debug(f"Validating transaction: {data} with uid: {uid}")
        _validate_transaction(uid, data, sources, tags, upcoming)
        update.fix_data(data)
        return func(uid, data, *args, **kwargs)
    return _wrapped

def TransactionIDValidator(func):
    """
    Decorator to validate a transaction id.
    Checks if the transaction exists.nsaction.objects.bulk_create([Transaction(**item) for item in data])
    Raises a ValidationError if the transaction does not exist.
    """
    @wraps(func)
    def _wrapped(uid, tx_id: str, *args, **kwargs):
        logger.debug(f"Validating transaction id: {tx_id} with uid: {uid}")
        # Check if transaction exists
        profile = kwargs.get('profile')
        to_check = Transaction.objects.for_user(profile.user_id).get_tx(tx_id=tx_id)
        if not to_check:
            logger.error(f"Transaction does not exist: {tx_id}")
            raise ValidationError("Transaction does not exist")
        kwargs['id_check'] = to_check
        return func(uid, tx_id,  profile=profile, *args, **kwargs)
    return _wrapped


# User Validator
def UserValidator(func):
    """
    Decorator to validate a user.
    Checks if the user exists.
    Raises a ValidationError if the user does not exist.
    """
    @wraps(func)
    def _wrapped(uid, data:dict, *args, **kwargs):
        logger.debug(f"Validating user with uid: {uid}")
        profile = AppProfile.objects.for_user(uid)
        if not profile.exists():
            logger.error(f"User does not exist: {uid}")
            raise ValidationError("User does not exist")
        kwargs['profile'] = profile
        if data.get('timezone'):
            _validate_timezone(data['timezone'])
        if data.get('base_currency'):
            _validate_currency(data['base_currency'])
        return func(uid, data, *args, **kwargs)
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
    def _wrapped(uid, data, src, *args, **kwargs):
        sources = PaymentSource.objects.for_user(uid)
        profile = kwargs.get('profile')
        logger.debug(f"Validating asset: {data} with uid: {uid}")
        _validate_asset(uid, data, sources, src)
        update = Updater(sources=sources, profile=profile)
        update.fix_asset_data(data, src)
        kwargs['sources'] = sources
        return func(uid, data, *args, **kwargs)
    return _wrapped


# Upcoming Expense Validators
def UpcomingExpenseValidator(func):
    """
    Decorator to validate an upcoming expense.
    Checks if the expense exists.
    Raises a ValidationError if the expense does not exist.
    """
    @wraps(func)
    def _wrapped(uid, data, *args, **kwargs):
        logger.debug(f"Validating expense: {data} with uid: {uid}")
        profile = kwargs.get('profile')
        upcoming = UpcomingExpense.objects.for_user(profile.user_id)
        kwargs['upcoming'] = upcoming
        # Check if it's a list, and treat it as a bulk addition
        if isinstance(data, list):
            rejected = []
            accepted = []
            for item in data:
                try:
                    _validate_expense(uid, item)
                    accepted.append(item)
                except ValidationError as e:
                    logger.error(f"Expense validation failed: {e}")
                    rejected.append(item)
            kwargs['rejected'] = rejected
            kwargs['accepted'] = accepted
            return func(uid, data, *args, **kwargs)
        else: 
            _validate_expense(uid, data)
            kwargs['upcoming'] = upcoming.filter(name=data['name'])
        return func(uid, data, **args, **kwargs)
    return _wrapped

def UpcomingExpenseGetValidator(func):
    @wraps(func)
    def _wrapped(uid, data, expense_name: str, *args, **kwargs):
        logger.debug(f"Validating expense: {data} with uid: {uid}")
        profile = kwargs.get('profile')
        upcoming = UpcomingExpense.for_user(profile.user_id).get_by_name(expense_name)
        if not upcoming:
            logger.error(f"Expense does not exist: {expense_name}")
            raise ValidationError("Expense does not exist")
        kwargs['existing'] = upcoming
        return func(uid, expense_name, *args, **kwargs)
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


# Source Validators
def SourceValidator(func):
    """
    Decorator to validate a payment source.
    Checks if the source exists.
    Raises a ValidationError if the source does not exist.
    """
    @wraps(func)
    def _wrapped(uid, data, *args, **kwargs):
        profile = kwargs.get('profile')
        sources = PaymentSource.objects.for_user(profile.user_id)
        update = Updater(sources=sources, profile=profile)
        kwargs['sources'] = sources
        logger.debug(f"Validating source: {data} with uid: {uid}")
        if isinstance(data, list):
            rejected = []
            accept = []
            for item in data:
                try:
                    _validate_source(uid, item)
                    update.fix_source_data(item)
                    accept.append(item)
                except ValidationError as e:
                    logger.error(f"Source validation failed: {e}")
                    rejected.append(item)
            kwargs['rejected'] = rejected
            kwargs['accepted'] = accept
            return func(uid, data, *args, **kwargs)
        else:
            _validate_source(uid, data)
            update.fix_source_data(data)
            return func(uid, data, *args, **kwargs)
    return _wrapped

def SourceGetValidator(func):
    @wraps(func)
    def _wrapped(uid, source: str, *args, **kwargs):
        logger.debug(f"Validating source: {source} with uid: {uid}")
        if not PaymentSource.objects.for_user(uid).filter(source=source).exists():
            logger.error(f"Source does not exist: {source}")
            raise ValidationError("Source does not exist")
        checked = PaymentSource.objects.for_user(uid).get_by_source(source=source)
        kwargs['checked'] = checked
        return func(uid, source, *args, **kwargs)
    return _wrapped


# Private Functions
def _validate_transaction(uid, data:dict, sources, tags, upcoming):
    logger.debug(f"Validating transaction: {data} with uid: {uid}")
    if not sources.filter(source=data['source']).exists():
        logger.error(f"Source does not exist: {data['source']}")
        raise ValidationError("Source does not exist")
    _validate_currency(data['currency'])
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

def _validate_asset(uid, data:dict, sources, src):
    logger.debug(f"Validating asset: {data} with uid: {uid}")
    if data.get('source'):
        if not sources.filter(source=data['source']).exists():
            logger.error(f"Source does not exist: {data['source']}")
            raise ValidationError("Source does not exist")
    if data.get('currency'):    
        _validate_currency(data['currency'])
    if not sources.filter(source=src).exists():
        logger.error(f"Reference source to change that does not exist: {src}")
        raise ValidationError(f"Asset for {src} not found")
    return data, src

def _validate_expense(uid, data:dict):
    logger.debug(f"Validating expense: {data} with uid: {uid}")
    if UpcomingExpense.objects.for_user(uid).filter(name=data['name']).exists():
        raise ValidationError("Expense already exists")
    _validate_currency(data['currency'])
    return data

def _validate_source(uid, data:dict, sources):
    logger.debug(f"Validating sources: {sources}")
    if data.get('source'):
        if data['source'].lower() == "unknown":
            raise ValidationError("Cannot add unknown source")
        if not sources.filter(source=data['source'].lower()).exists():
            logger.error(f"Source does not exist: {data['source']}")
            raise ValidationError("Source does not exist")
    if data.get('acc_type'):
        if data['acc_type'].upper() == "UNKNOWN":
            raise ValidationError("Cannot add unknown account type")
        if data['acc_type'] not in PaymentSource.AccType.choices:
            logger.error(f"Account type does not exist: {data['acc_type']}")
            raise ValidationError("Account type does not exist")
    return data

def _validate_currency(code):
    logger.debug(f"Validating currency: {code}")
    if not pycountry.currencies.get(alpha_3=code):
        logger.error(f"Currency does not exist: {code}")
        raise ValidationError("Currency does not exist")
    return code

def _validate_timezone(tz):
    logger.debug(f"Validating timezone: {tz}")
    if not zoneinfo.available_timezones.__contains__(tz):
        logger.error(f"Timezone does not exist: {tz}")
        raise ValidationError("Timezone does not exist")
    return tz
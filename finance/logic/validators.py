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
    Category,
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
        sources = kwargs.get('sources') or PaymentSource.objects.for_user(uid)
        tags = set(Tag.objects.for_user(uid).values_list('tags', flat=True))
        upcoming = UpcomingExpense.objects.for_user(uid)
        upcoming_check = set(upcoming.values_list('name', flat=True))
        profile = kwargs.get('profile')
        source_check = kwargs.get('source_check') or set(sources.values_list('source', flat=True))
        cat_check = kwargs.get('cat_check') or set(Category.objects.for_user(uid).values_list('name', flat=True))
        kwargs['source_check'] = source_check
        kwargs['upcoming_check'] = upcoming_check
        kwargs['sources'] = sources
        kwargs['upcoming'] = upcoming
        update = Updater(profile=profile)
        if isinstance(data, list):
            rejected = []
            accepted = []
            for item in data:
                logger.debug(f"Validating transaction: {item} with uid: {uid}")
                try:
                    _validate_transaction(uid, item, source_check, tags, upcoming_check, cat_check, profile)
                    accepted.append(item)
                except ValidationError as e:
                    logger.error(f"Transaction validation failed: {e}")
                    rejected.append(item)
            if not accepted:
                raise ValidationError("No valid transactions")
            kwargs['rejected'] = rejected
            kwargs['accepted'] = accepted
            kwargs['tags'] = tags
            update.fix_tx_data(accepted)
            return func(uid, data,  *args, **kwargs)
        logger.debug(f"Validating transaction: {data} with uid: {uid}")
        _validate_transaction(uid, data, source_check, tags, upcoming_check, cat_check, profile)
        update.fix_data(data)
        kwargs['tags'] = tags
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

# Category Validators
def CategorySetValidator(func):
    @wraps(func)
    def _wrapped(uid, data, *args, **kwargs):
        logger.debug(f"Validating category: {data} with uid: {uid}")
        profile = kwargs.get('profile')
        patch = kwargs.get('patch') or False
        categories = kwargs.get('categories') or Category.objects.for_user(profile.user_id)
        cat_check = kwargs.get('cat_check') or set(categories.values_list('name', flat=True))
        kwargs['categories'] = categories
        if isinstance(data, list):
            rejected = []
            accepted = []
            for item in data:
                try:
                    _validate_category(uid, item, cat_check, patch)
                    accepted.append(item)
                except ValidationError as e:
                    logger.error(f"Category validation failed: {e}")
                    rejected.append(item)
                kwargs['rejected'] = rejected
                kwargs['accepted'] = accepted
            return func(uid, data, *args, **kwargs)
        else:
            _validate_category(uid, data, cat_check, patch)
            return func(uid, data, *args, **kwargs)
    return _wrapped

def CategoryGetValidator(func):
    @wraps(func)
    def _wrapped(uid, data, cat_name, *args, **kwargs):
        logger.debug(f"Validating category: {data} with uid: {uid}")
        profile = kwargs.get('profile')
        categories = Category.objects.for_user(profile.user_id)
        cat_check = set(categories.values_list('name', flat=True))
        kwargs['categories'] = categories
        if cat_name in ['expense', 'income', 'transfer']:
            raise ValidationError("Cannot get default category")
        if not cat_name in cat_check:
            logger.error(f"Category does not exist: {cat_name}")
            raise ValidationError("Category does not exist")
        kwargs['checked'] = categories.get(name=cat_name)
        kwargs['patch'] = True
        return func(uid, cat_name, *args, **kwargs)
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
        profile = AppProfile.objects.for_user(uid).first()
        if not profile:
            logger.error(f"User does not exist: {uid}")
            raise ValidationError("User does not exist")
        kwargs['profile'] = profile
        if data.get('spend_accounts'):
            sources = PaymentSource.objects.for_user(uid)
            source_check = set(sources.values_list('source', flat=True))
            for item in data['spend_accounts']:
                if not item.lower() in source_check:
                    logger.error(f"Source does not exist: {item}")
                    raise ValidationError("Source does not exist")
            kwargs['sources'] = sources
            kwargs['source_check'] =source_check
        if data.get('timezone'):
            _validate_timezone(data['timezone'])
        if data.get('base_currency'):
            _validate_currency(data['base_currency'])
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
        upcoming = kwargs.get('upcoming') or UpcomingExpense.objects.for_user(profile.user_id)
        upcoming_check = kwargs.get('upcoming_check') or set(upcoming.values_list('name', flat=True))
        patch = kwargs.get('patch') or False
        kwargs['upcoming_check'] = upcoming_check
        kwargs['upcoming'] = upcoming
        # Check if it's a list, and treat it as a bulk addition
        if isinstance(data, list):
            rejected = []
            accepted = []
            for item in data:
                try:
                    _validate_expense(uid, item, profile, upcoming_check, patch)
                    accepted.append(item)
                except ValidationError as e:
                    logger.error(f"Expense validation failed: {e}")
                    rejected.append(item)
            kwargs['rejected'] = rejected
            kwargs['accepted'] = accepted
            return func(uid, data, *args, **kwargs)
        else: 
            _validate_expense(uid, data,profile,  upcoming_check, patch)
            kwargs['upcoming'] = upcoming.filter(name=data['name'])
        return func(uid, data, **args, **kwargs)
    return _wrapped

def UpcomingExpenseGetValidator(func):
    @wraps(func)
    def _wrapped(uid, data, expense_name: str, *args, **kwargs):
        logger.debug(f"Validating expense: {data} with uid: {uid}")
        profile = kwargs.get('profile')
        upcoming = UpcomingExpense.for_user(profile.user_id)
        upcoming_check = set(upcoming.values_list('name', flat=True))
        kwargs['upcoming_check'] = upcoming_check
        if not expense_name in upcoming_check:
            logger.error(f"Expense does not exist: {expense_name}")
            raise ValidationError("Expense does not exist")
        kwargs['patch'] = True
        kwargs['upcoming'] = upcoming
        kwargs['existing'] = upcoming.get_by_name(expense_name)
        return func(uid, expense_name, *args, **kwargs)
    return _wrapped


# Tag Validators
def TagSetValidator(func):
    """
    Decorator to validate a tag.
    Checks if the tag exists.
    Raises a ValidationError if the tag already exists.
    """
    @wraps(func)
    def _wrapped(uid, data, *args, **kwargs):
        logger.debug(f"Validating tag: {data} with uid: {uid}")
        profile = kwargs.get('profile')
        tags = Tag.objects.for_user(profile.user_id)
        tag_check = set(tags.values_list('tags', flat=True))
        kwargs['tags'] = tags
        for item in data['tags']:
            rejected = []
            accepted = set()
            if item in tag_check:
                rejected.append(item)
                logger.error(f"Tag already exists: {item}")
            else:
                accepted.add(item)
            if not accepted:
                raise ValidationError("No valid tags")
            kwargs['rejected'] = rejected
            kwargs['accepted'] = accepted
        return func(uid, data, *args, **kwargs)
    return _wrapped

# Created for later, not used in current production
def TagGetValidator(func):
    @wraps(func)
    def _wrapped(uid, data, *args, **kwargs):
        logger.debug(f"Validating tag: {data} with uid: {uid}")
        profile = kwargs.get('profile')
        tags = Tag.objects.for_user(profile.user_id)
        tag_check = set(tags.values_list('tags', flat=True))
        kwargs['tags'] = tags
        for item in data['tags']:
            rejected = []
            accepted = []
            if item not in tag_check:
                logger.error(f"Tag does not exist: {data['name']}")
                rejected.append(item)
            else:
                accepted.append(item)
            if not accepted:
                raise ValidationError("No valid tags")
            kwargs['rejected'] = rejected
            kwargs['accepted'] = accepted
        return func(uid, data, *args, **kwargs)
    return _wrapped

# Source Validators
def SourceSetValidator(func):
    """
    Decorator to validate a payment source.
    Checks if the source exists.
    Raises a ValidationError if the source does not exist.
    """
    @wraps(func)
    def _wrapped(uid, data, *args, **kwargs):
        profile = kwargs.get('profile')
        sources = kwargs.get('sources') or PaymentSource.objects.for_user(uid)
        source_check = kwargs.get('source_check') or set(sources.values_list('source', flat=True))
        patch = kwargs.get('patch') or False
        update = Updater(profile=profile)
        kwargs['sources'] = sources
        logger.debug(f"Validating source: {data} with uid: {uid}")
        if isinstance(data, list):
            rejected = []
            accept = []
            for item in data:
                try:
                    _validate_source(uid, item, source_check, patch)
                    update.fix_source_data(item)
                    accept.append(item)
                except ValidationError as e:
                    logger.error(f"Source validation failed: {e}")
                    rejected.append(item)
            kwargs['rejected'] = rejected
            kwargs['accepted'] = accept
            return func(uid, data, *args, **kwargs)
        else:
            _validate_source(uid, data, source_check, patch)
            update.fix_source_data(data)
            return func(uid, data, *args, **kwargs)
    return _wrapped

def SourceGetValidator(func):
    @wraps(func)
    def _wrapped(uid, source: str, *args, **kwargs):
        logger.debug(f"Validating source: {source} with uid: {uid}")
        sources = PaymentSource.objects.for_user(uid)
        source_check = set(sources.values_list('source', flat=True))
        if not source in source_check:
            logger.error(f"Source does not exist: {source}")
            raise ValidationError("Source does not exist")
        checked = PaymentSource.objects.for_user(uid).get_by_source(source=source)
        kwargs['sources'] = sources
        kwargs['source_check'] = source_check
        kwargs['checked'] = checked
        kwargs['patch'] = True
        return func(uid, source, *args, **kwargs)
    return _wrapped


# Private Functions
def _validate_transaction(uid, data:dict, source_check, tags, upcoming_check, cat_check, profile):
    logger.debug(f"Validating transaction: {data} with uid: {uid}")
    if not data['source'] in source_check:
        logger.error(f"Source does not exist: {data['source']}")
        raise ValidationError("Source does not exist")
    _validate_currency(data['currency'])
    if data.get('category'):
        if not data['category'] in cat_check:
            logger.error(f"Category does not exist: {data['category']}")
            raise ValidationError("Category does not exist")
    if data.get('tags'):
        new_tags = set()
        for tag in data['tags']:
            if not tag not in tags:
                logger.warning(f"Tag does not exist: {tag}.  Creating...")
                new_tags.add(tag)
        if new_tags:
            update_tags = list(new_tags|tags)
            Tag.objects.for_user(uid).update(tags=update_tags)
    if data['date'] > timezone.now(profile.timezone).date():
       raise ValidationError("Date cannot be in the future")
    if data.get('bill'):
        if not data['bill'] in upcoming_check:
            logger.error(f"Expense does not exist: {data['bill']}")
            raise ValidationError("Expense does not exist")
        if data['tx_type'] != 'EXPENSE':
            logger.error(f"Expense must be an expense: {data['tx_type']}")
            raise ValidationError("Expense must be an expense")
    return data

def _validate_expense(uid, data:dict, profile, upcoming_check, patch):
    logger.debug(f"Validating expense: {data} with uid: {uid}")
    if not patch:
        if data['name'] in upcoming_check:
            logger.error(f"Expense already exists: {data['name']}")
            raise ValidationError("Expense already exists")
        if data.get('start_date') and not data.get('due_date'):
            data['due_date'] = data['start_date']
    else:
        if not data['name'] in upcoming_check:
            logger.error(f"Expense does not exist: {data['name']}")
            raise ValidationError("Expense does not exist")
    if data.get('currency'):
        _validate_currency(data['currency'])
    if data.get('end_date'):
        if data.get('due_date'):
            if data['end_date'] < data['due_date']:
                logger.error(f"End date cannot be before due date: {data['end_date']}")
                raise ValidationError("End date cannot be before due date")
        if data['end_date'] < timezone.now(profile.timezone).date():
            logger.error(f"End date cannot be in the past: {data['end_date']}")
            raise ValidationError("End date cannot be in the past")
            
    return data

def _validate_source(uid, data:dict, source_check, patch):
    logger.debug(f"Validating sources: {source_check}")

    # Check if source is provided and is not unknown
    if data.get('source'):
        if data['source'].lower() == "unknown":
            # This should be caught before here.  This is a failsafe
            raise ValidationError("Cannot add unknown source")
        
        # If posting/new source, make sure it doesn't exist
        if not patch:
            if data['source'] in source_check:
                logger.error(f"Source already exists: {data['source']}")
                raise ValidationError("Source already exists")
            
        # If patching a source, make sure it does exist   
        else:
            if not data['source'] in source_check:
                logger.error('Source does not exist')
                raise ValidationError("Cannot update source to one that doesn't exist")

    # Check if acc_type is provided, and is a supported type.  Reject "unknown"      
    if data.get('acc_type'):
        if data['acc_type'].upper() == "UNKNOWN":
            raise ValidationError("Cannot add unknown account type")
        if data['acc_type'] not in PaymentSource.AccType.choices:
            logger.error(f"Account type does not exist: {data['acc_type']}")
            raise ValidationError("Account type does not exist")
        
    # Check and validate currency if provided
    if data.get('currency'):
        _validate_currency(data['currency'])
    return data

def _validate_category(uid, data:dict, cat_check, patch):
    logger.debug(f"Validating category: {data} with uid: {uid}")
    if not patch:
        if data['name'] in cat_check:
            logger.error(f"Category already exists: {data['name']}")
            raise ValidationError("Category already exists")
    else:
        if not data['name'] in cat_check:
            logger.error(f"Category does not exist: {data['name']}")
            raise ValidationError("Category does not exist")
    return data

def _validate_currency(code):
    logger.debug(f"Validating currency: {code}")
    if not pycountry.currencies.get(alpha_3=code.upper()):
        logger.error(f"Currency does not exist: {code}")
        raise ValidationError("Currency does not exist")
    return code

def _validate_timezone(tz):
    logger.debug(f"Validating timezone: {tz}")
    if not zoneinfo.available_timezones.__contains__(tz):
        logger.error(f"Timezone does not exist: {tz}")
        raise ValidationError("Timezone does not exist")
    return tz
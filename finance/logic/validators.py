from functools import wraps
from django.core.exceptions import ValidationError
from django.utils import timezone
from finance.models import *
from loguru import logger

# TODO: Add Docstrings
# TODO: Add tag validation
# TODO: Fix _fix_data to pull from models directly


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

def UserValidator(func):
    @wraps(func)
    def _wrapped(uid, data:dict):
        logger.debug(f"Validating user with uid: {uid}")
        if not AppProfile.objects.filter(user_id=uid).exists():
            raise ValidationError("User does not exist")
        return func(uid, data)
    return _wrapped

def _validate_transaction(uid, data:dict):
    logger.debug(f"Validating transaction: {data} with uid: {uid}")
    if not Category.objects.filter(name=data['category'], uid=uid).exists():
        logger.debug(f"Category does not exist: {data['category']}")
        raise ValidationError("Category does not exist")
    if not PaymentSource.objects.filter(source=data['source'],uid=uid).exists():
        logger.debug(f"Source does not exist: {data['source']}")
        raise ValidationError("Source does not exist")
    if not Currency.objects.filter(code=data['currency'],uid=uid).exists():
        logger.debug(f"Currency does not exist: {data['currency']}")
        raise ValidationError("Currency does not exist")
    for tag in data['tags']:
        if not Tag.objects.filter(name=tag, uid=uid).exists():
            logger.debug(f"Tag does not exist: {tag}.  Creating...")
            uid_instance = AppProfile.objects.get(user_id=uid)
            Tag.objects.create(name=tag, uid=uid_instance)
    if not data.get('date'):
        data['date'] = timezone.now().date()
    return

def _fix_data(uid, data:dict):
    logger.debug(f"Fixing data for {uid}")
    data['category'] = Category.objects.for_user(uid).get_by_name(name=data['category']).get()
    data['source'] = PaymentSource.objects.for_user(uid).get_by_source(source=data['source']).get()
    data['currency'] = AppProfile.objects.for_user(uid).get_base_currency()
    data['uid'] = AppProfile.objects.for_user(uid).get()
    return data
from functools import wraps
from django.core.exceptions import ValidationError
from django.utils import timezone
from models import (
        AppProfile, 
        Category, 
        Currency, 
        Tag, 
        PaymentSource, 
        UpcomingExpense, 
        Transaction, 
        CurrentAsset, 
        FinancialSnapshot,
)



def TransactionValidator(func):
    @wraps(func)
    def _wrapped(uid, data:dict):
        _validate_transaction(uid, data)
        return func(uid, data)
    return _wrapped

def TransferValidator(func):
    @wraps(func)
    def _wrapped(uid, data:list):
        for item in data:
            _validate_transaction(uid, item)
        return func(uid, data)
    return _wrapped


def _validate_transaction(uid, data:dict):
    if not Tranasction.objects.filter(uid=uid, data['category']).exists():
        raise ValidationError("Category does not exist")
    if not Tranasction.objects.filter(uid=uid, data['source']).exists():
        raise ValidationError("Source does not exist")
    if not Tranasction.objects.filter(uid=uid, data['currency']).exists():
        raise ValidationError("Currency does not exist")
    if not Tranasction.objects.filter(uid=uid, data['date']).exists():
        data['date'] = timezone.now().date()
    return

"""
This module handles all signal receivers for the finance manager application.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from finance.models import (
    Transaction, 
    CurrentAsset, 
    AppProfile, 
    FinancialSnapshot, 
    Currency, 
    PaymentSource,
    UpcomingExpense
)
from loguru import logger

@receiver(post_save, sender=User)
def create_user(sender, instance, created, **kwargs):
    """
    Signal receiver for user creation.
    Creates a new AppProfile and FinancialSnapshot for the user.
    Automatically creates a default currency and default payment source.
    """
    if created:
        logger.debug(f"Creating user: {instance}")
        instance.appprofile = AppProfile.objects.create(username=instance)
        FinancialSnapshot.objects.create(uid=instance.appprofile)
        default_currency = Currency.objects.filter(code="USD").first()
        instance.appprofile.base_currency = default_currency
        # PaymentSource.save() will automatically create the CurrentAsset
        default_source = PaymentSource.objects.create(source="cash", acc_type="CASH", uid=instance.appprofile)
        PaymentSource.objects.create(source="unknown", acc_type="UNKNOWN", uid=instance.appprofile)
        instance.appprofile.spend_accounts.set([default_source])
        instance.appprofile.save()
        logger.debug(f"Created user: {instance}.  User: {instance.appprofile}.  Base currency: {default_currency}. Default source: {default_source}")
        return
    else:
        return
    
@receiver(post_save, sender=UpcomingExpense)
def update_monthly(sender, instance, **kwargs):
    """
    Signal receiver for UpcomingExpenses.
    Updates the due date of recurring expenses and resets paid flag.
    """
    uid = instance.uid
    expenses = UpcomingExpense.objects.for_user(uid).get_by_paid_flag(True).get_by_recurring(True)
    # Update expenses if they exist
    if expenses:
        for expense in expenses:
            if  expense.due_date <= timezone.now().date():
                expense.due_date = expense.due_date + relativedelta(months=1)
                expense.paid_flag = False
                expense.save()
    return
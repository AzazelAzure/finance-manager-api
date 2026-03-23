"""
This module handles all signal receivers for the finance manager application.
"""
from django.db.models.signals import post_save, pre_delete, pre_save
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.contrib.auth.models import User
import contextvars
from finance.models import (
    Transaction, 
    AppProfile, 
    FinancialSnapshot, 
    PaymentSource,
    UpcomingExpense,
    Category,
    Tag,
)
from loguru import logger


_SKIP_PAYMENT_SOURCE_PREDELETE = contextvars.ContextVar(
    "_SKIP_PAYMENT_SOURCE_PREDELETE", default=False
)

@receiver(pre_delete, sender=PaymentSource)
def delete_source(sender, instance, **kwargs):
    """
    Signal receiver for PaymentSource deletion.
    Converts any transactions with the deleted source to uncategorized.
    """
    if _SKIP_PAYMENT_SOURCE_PREDELETE.get():
        return
    # Get the 'unknown' source
    unknown_source = PaymentSource.objects.filter(uid=instance.uid, source="unknown").first()

    # Update all transactions that reference the deleted source to the 'unknown' source
    if unknown_source:
        Transaction.objects.filter(uid=instance.uid, source=instance.source).update(
            source=unknown_source.source
        )


# User signals
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
        _generate_base_profile(instance.appprofile)
        return
    else:
        return

@receiver(user_logged_in)
def user_logged_in(sender, request, user, **kwargs):
    """
    Signal receiver for user login.
    Verifies the existence of the 'unknown' source.
    If not found, creates it.
    """

    uid = user.appprofile.user_id

    app_profile = AppProfile.objects.for_user(uid).first()
    if not app_profile:
        logger.critical(f'User {user.username} had no app profile.  Database was tampered with, indicating a security breach.  Recreated app profile.')
        _generate_base_profile(app_profile)
        return

    # Get the 'unknown' source
    unknown_source = PaymentSource.objects.filter(uid=uid, source="unknown").first()

    # If not found, create it
    if not unknown_source:
        logger.critical(f'User{user.username} had unknown source deleted.  Database was tampered with, indicating a security breach.  Recreated unknown source.')
        PaymentSource.objects.create(uid=user.appprofile.user_id, source="unknown", acc_type="UNKNOWN")

    return


@receiver(pre_delete, sender=User)
def delete_user_finance_data(sender, instance, **kwargs):
    """
    Ensure decoupled finance rows keyed by uid are removed with user deletion.
    """
    profile = getattr(instance, "appprofile", None)
    if not profile:
        return
    uid = str(profile.user_id)

    # Delete transaction-like dependents first to avoid source pre_delete side effects.
    Transaction.objects.filter(uid=uid).delete()
    UpcomingExpense.objects.filter(uid=uid).delete()
    Category.objects.filter(uid=uid).delete()
    Tag.objects.filter(uid=uid).delete()

    # When we're deleting the user, we want PaymentSource deletion to be fast/bulk.
    # The PaymentSource pre_delete hook triggers per-instance work and disables fast deletes.
    token = _SKIP_PAYMENT_SOURCE_PREDELETE.set(True)
    try:
        pre_delete.disconnect(delete_source, sender=PaymentSource)
        PaymentSource.objects.filter(uid=uid).delete()
    finally:
        pre_delete.connect(delete_source, sender=PaymentSource, weak=False)
        _SKIP_PAYMENT_SOURCE_PREDELETE.reset(token)

    FinancialSnapshot.objects.filter(uid=uid).delete()


# Helper Functions
def _generate_base_profile(app_profile):
    """
    Seeds a new app profile with default values.
    """
    FinancialSnapshot.objects.create(uid=app_profile.user_id)
    default_currency = 'USD'
    app_profile.base_currency = default_currency
    default_source = PaymentSource.objects.create(source="cash", acc_type="CASH", uid=app_profile.user_id)
    PaymentSource.objects.create(source="unknown", acc_type="UNKNOWN", uid=app_profile.user_id)
    app_profile.spend_accounts = default_source.source
    app_profile.save()
    logger.debug(f"Created user: User: {app_profile.username}.  Base currency: {default_currency}. Default source: {default_source}")
    return
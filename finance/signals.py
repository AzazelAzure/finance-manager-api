from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import *
from loguru import logger

@receiver(post_save, sender=User)
def create_user(sender, instance, created, **kwargs):
    if created:
        logger.debug(f"Creating user: {instance}")
        instance.appprofile = AppProfile.objects.create(username=instance)
        FinancialSnapshot.objects.create(uid=instance.appprofile)
        default_currency = Currency.objects.create(code="USD", name="US Dollar", symbol="$", uid=instance.appprofile)
        instance.appprofile.base_currency = default_currency
        # PaymentSource.save() will automatically create the CurrentAsset
        default_source = PaymentSource.objects.create(source="Cash", acc_type="CASH", uid=instance.appprofile)
        instance.appprofile.spend_accounts.set([default_source])
        instance.appprofile.save()
        logger.debug(f"Created user: {instance}.  User: {instance.appprofile}.  Base currency: {default_currency}. Default source: {default_source}")
        return
    else:
        logger.debug(f"Updating user: {instance}")
        return
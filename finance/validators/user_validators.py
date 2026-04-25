"""
User-scoped validators.
"""

from functools import wraps

from rest_framework.exceptions import ValidationError

from finance.models import AppProfile, PaymentSource
from finance.validators.profile_validators import validate_profile_update_payload
from loguru import logger


def UserValidator(func):
    """
    Validate a user by uid and inject profile into kwargs.
    """

    @wraps(func)
    def _wrapped(uid, *args, **kwargs):
        logger.debug(f"Validating user with uid: {uid}")
        profile = AppProfile.objects.for_user(uid).first()
        if not profile:
            logger.error(f"User does not exist: {uid}")
            raise ValidationError("User does not exist")
        kwargs["profile"] = profile

        data = None
        if args:
            data = args[0]
        elif "data" in kwargs:
            data = kwargs["data"]

        normalized_data, _ = validate_profile_update_payload(uid, data)
        if isinstance(normalized_data, dict) and normalized_data.get("spend_accounts") is not None:
            sources = PaymentSource.objects.for_user(uid)
            kwargs["sources"] = list(sources)
            kwargs["source_check"] = set(sources.values_list("source", flat=True))

        if args and isinstance(normalized_data, dict):
            args = (normalized_data, *args[1:])
        elif "data" in kwargs and isinstance(normalized_data, dict):
            kwargs["data"] = normalized_data

        return func(uid, *args, **kwargs)

    return _wrapped

"""
Profile payload validation helpers.
"""

from rest_framework.exceptions import ValidationError

from finance.models import PaymentSource
from finance.validators.validation_core import _validate_currency, _validate_timezone
from loguru import logger


def validate_profile_update_payload(uid, data):
    """
    Validate and normalize profile update payload fields.
    """
    if not isinstance(data, dict):
        return data, None

    normalized = dict(data)

    if normalized.get("spend_accounts") is not None:
        spend_accounts = normalized["spend_accounts"]
        if not isinstance(spend_accounts, list):
            spend_accounts = [spend_accounts]
        spend_accounts = [str(item).lower() for item in spend_accounts]
        if "unknown" in spend_accounts:
            raise ValidationError("Unknown source cannot be used as spend account")

        sources = PaymentSource.objects.for_user(uid)
        source_check = set(sources.values_list("source", flat=True))
        for item in spend_accounts:
            if item not in source_check:
                logger.error(f"Source does not exist: {item}")
                raise ValidationError("Source does not exist")

        normalized["spend_accounts"] = spend_accounts

    if normalized.get("timezone"):
        _validate_timezone(normalized["timezone"])

    if normalized.get("base_currency"):
        normalized["base_currency"] = _validate_currency(normalized["base_currency"])

    if normalized.get("start_week") is not None:
        if normalized["start_week"] < 0 or normalized["start_week"] > 6:
            raise ValidationError("Start week must be between 0 and 6")

    return normalized, None

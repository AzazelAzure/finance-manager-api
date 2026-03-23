"""
Shared validation primitives used across domain-specific validators (currency, timezone).
"""

import zoneinfo

from django.conf import settings
from rest_framework.exceptions import ValidationError

from loguru import logger


def _validate_currency(code):
    """Ensure ``code`` is a supported currency string; returns uppercase code."""
    logger.debug(f"Validating currency: {code}")
    if code is None or code == "":
        raise ValidationError("Currency does not exist")
    code_upper = code.upper()
    if code_upper not in settings.SUPPORTED_CURRENCIES:
        logger.error(f"Currency does not exist: {code}")
        raise ValidationError("Currency does not exist")
    return code_upper


def _validate_timezone(tz):
    """Ensure timezone string exists in IANA timezone database."""
    logger.debug("Validating timezone value")
    if tz not in zoneinfo.available_timezones():
        logger.error(f"Timezone does not exist: {tz}")
        raise ValidationError("Timezone does not exist")
    return tz

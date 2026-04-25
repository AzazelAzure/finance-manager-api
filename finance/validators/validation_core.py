"""
Shared validation primitives used across domain-specific validators (currency, timezone).
"""

import zoneinfo

from django.conf import settings
from rest_framework.exceptions import ValidationError

from loguru import logger

_TZ_LOWER_TO_CANONICAL = {n.lower(): n for n in zoneinfo.available_timezones()}


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
    """Ensure timezone string exists in IANA database; return canonical casing."""
    logger.debug("Validating timezone value")
    if tz is None:
        raise ValidationError("Timezone does not exist")
    raw = str(tz).strip()
    if not raw:
        raise ValidationError("Timezone does not exist")
    if raw in zoneinfo.available_timezones():
        return raw
    canonical = _TZ_LOWER_TO_CANONICAL.get(raw.lower())
    if canonical is not None:
        return canonical
    logger.error(f"Timezone does not exist: {tz}")
    raise ValidationError(
        "Timezone does not exist. Use an IANA name such as Asia/Manila (not abbreviations like PHT)."
    )

"""
Profile payload validation helpers.
"""

from datetime import date

from rest_framework.exceptions import ValidationError

from finance.models import AppProfile, PaymentSource
from finance.logic.source_linkage import names_to_ids
from finance.validators.validation_core import _validate_currency, _validate_timezone
from loguru import logger

_PAY_CYCLE_FREQUENCIES = {c.value for c in AppProfile.PayCycleFrequency}
_STS_WINDOW_MODES = {c.value for c in AppProfile.StsWindowMode}


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
        from finance.logic.source_linkage import build_source_maps

        maps = build_source_maps(sources)
        normalized["spend_accounts"] = names_to_ids(spend_accounts, maps)

    if normalized.get("timezone") is not None:
        normalized["timezone"] = _validate_timezone(normalized["timezone"])

    if normalized.get("base_currency"):
        normalized["base_currency"] = _validate_currency(normalized["base_currency"])

    if normalized.get("start_week") is not None:
        if normalized["start_week"] < 0 or normalized["start_week"] > 6:
            raise ValidationError("Start week must be between 0 and 6")

    if normalized.get("sts_window_mode") is not None:
        mode = str(normalized["sts_window_mode"]).strip().lower()
        if mode not in _STS_WINDOW_MODES:
            raise ValidationError("Invalid sts_window_mode")
        normalized["sts_window_mode"] = mode

    if normalized.get("pay_cycle_frequency") is not None:
        freq = str(normalized["pay_cycle_frequency"]).strip().lower()
        if freq not in _PAY_CYCLE_FREQUENCIES:
            raise ValidationError("Invalid pay_cycle_frequency")
        normalized["pay_cycle_frequency"] = freq

    if normalized.get("pay_cycle_anchor_date") is not None:
        try:
            normalized["pay_cycle_anchor_date"] = date.fromisoformat(
                str(normalized["pay_cycle_anchor_date"])
            )
        except ValueError as exc:
            raise ValidationError("Invalid pay_cycle_anchor_date") from exc

    return normalized, None

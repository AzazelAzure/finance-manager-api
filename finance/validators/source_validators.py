from functools import wraps

from rest_framework.exceptions import ValidationError

from loguru import logger

from finance.logic.updaters import Updater
from finance.validators.validation_core import _validate_currency
from finance.models import PaymentSource


def SourceSetValidator(func):
    """
    Decorator to validate payment sources for create flows.

    Supports both:
    - single-object POST: payload is a dict
    - bulk POST: payload is a list of dicts
    """

    @wraps(func)
    def _wrapped(uid, data, *args, **kwargs):
        profile = kwargs.get("profile")
        sources = kwargs.get("sources") or PaymentSource.objects.for_user(uid)

        # Normalize to lower-case so input comparisons are case-insensitive.
        source_check = kwargs.get("source_check") or {
            str(s).lower() for s in sources.values_list("source", flat=True)
        }
        patch = kwargs.get("patch") or False

        update = Updater(profile=profile)
        kwargs["sources"] = sources

        logger.debug(f"Validating source payload: {data} with uid: {uid}")

        if isinstance(data, list):
            rejected = []
            accepted = []
            for item in data:
                try:
                    _validate_source(uid, item, source_check, patch)
                    update.fix_source_data([item])
                    accepted.append(item)
                except ValidationError as e:
                    logger.error(f"Source validation failed: {e}")
                    rejected.append(item)

            if not accepted:
                raise ValidationError("No valid sources")

            kwargs["rejected"] = rejected
            kwargs["accepted"] = accepted
            return func(uid, data, *args, **kwargs)

        _validate_source(uid, data, source_check, patch)
        update.fix_source_data([data])
        return func(uid, data, *args, **kwargs)

    return _wrapped


def SourceGetValidator(func):
    """
    Decorator to validate payment-source existence for single-resource flows.
    Used by PUT/PATCH/DELETE-style operations that identify a source by name.
    """

    @wraps(func)
    def _wrapped(uid, source: str, *args, **kwargs):
        logger.debug(f"Validating source: {source} with uid: {uid}")
        sources = PaymentSource.objects.for_user(uid)

        source_obj = sources.get_by_source(source=source.lower()).first()
        if not source_obj:
            logger.error(f"Source does not exist: {source}")
            raise ValidationError("Source does not exist")

        # Keep both historical keys since different service functions read different kwargs.
        kwargs["sources"] = sources
        kwargs["source_check"] = source_obj
        kwargs["checked"] = source_obj
        return func(uid, source, *args, **kwargs)

    return _wrapped


def _validate_source(uid, data: dict, source_check: set, patch: bool):
    """
    Validate a single source dict against business rules.
    """

    # Validate source identity (and reject reserved "unknown" source).
    if data.get("source"):
        incoming_source = str(data["source"]).lower()
        if incoming_source == "unknown":
            raise ValidationError("Cannot add unknown source")

        if not patch:
            if incoming_source in source_check:
                raise ValidationError("Source already exists")
        else:
            if incoming_source not in source_check:
                raise ValidationError("Cannot update source to one that doesn't exist")

        # Normalize in-place so later layers (Updater/source snapshots) stay consistent.
        data["source"] = incoming_source

    # Validate supported account types (reject reserved UNKNOWN).
    if data.get("acc_type"):
        incoming_acc_type = str(data["acc_type"]).upper()
        if incoming_acc_type == "UNKNOWN":
            raise ValidationError("Cannot add unknown account type")

        valid_acc_types = {choice[0] for choice in PaymentSource.AccType.choices}
        if incoming_acc_type not in valid_acc_types:
            logger.error(f"Account type does not exist: {data['acc_type']}")
            raise ValidationError("Account type does not exist")

        data["acc_type"] = incoming_acc_type

    # Validate currency if provided (returns upper-case).
    if data.get("currency"):
        data["currency"] = _validate_currency(data["currency"])

    return data


def validate_source_put_payload(uid, data: dict, existing_source_obj):
    """
    Validate and normalize a PUT payload for source full-replacement updates.
    """
    if str(existing_source_obj.source).lower() == "unknown":
        raise ValidationError("Cannot update unknown source")
    if str(data.get("source", "")).lower() == "unknown":
        raise ValidationError("Cannot update unknown source")

    normalized_existing = str(existing_source_obj.source).lower()
    source_check = {
        str(s).lower()
        for s in PaymentSource.objects.for_user(uid).values_list("source", flat=True)
    }
    incoming = str(data["source"]).lower()
    if incoming != normalized_existing and incoming in source_check:
        raise ValidationError("Source already exists")

    _validate_source(uid, data, source_check, patch=False)
    return data


def validate_source_patch_payload(uid, data: dict, existing_source_obj):
    """
    Validate and normalize PATCH payload for partial source updates.
    """
    if str(existing_source_obj.source).lower() == "unknown":
        raise ValidationError("Cannot update unknown source")
    if not data:
        raise ValidationError("No fields to update")

    source_check = {
        str(s).lower()
        for s in PaymentSource.objects.for_user(uid).values_list("source", flat=True)
    }
    incoming = data.get("source")
    if incoming is not None:
        normalized_incoming = str(incoming).lower()
        if normalized_incoming == "unknown":
            raise ValidationError("Cannot update unknown source")
        if (
            normalized_incoming != str(existing_source_obj.source).lower()
            and normalized_incoming in source_check
        ):
            raise ValidationError("Source already exists")
    _validate_source(uid, data, source_check, patch=True)
    return data


"""Service layer for payment source CRUD operations."""

from decimal import Decimal

from django.db import transaction
from loguru import logger
from rest_framework.exceptions import ValidationError

import finance.logic.validators as validator
from finance.logic.fincalc import Calculator
from finance.logic.source_linkage import load_source_maps, resolve_name_to_id
from finance.logic.updaters import Updater
from finance.models import PaymentSource
from finance.validators.source_validators import (
    SourceGetValidator,
    SourceSetValidator,
    validate_source_patch_payload,
    validate_source_put_payload,
)


# Payment Source Functions
@validator.UserValidator
@SourceSetValidator
@transaction.atomic
def add_source(uid, data, *args, **kwargs):
    """Create one or more sources and return accepted/rejected + snapshot."""
    logger.debug(f"Creating source payload for {uid}")
    sources = kwargs.get("sources")
    if isinstance(data, list):
        rejected = kwargs.get("rejected", [])
        accepted = kwargs.get("accepted", [])
        sources.bulk_create([PaymentSource(**item) for item in accepted])
        update = Updater(profile=kwargs.get("profile"), sources=kwargs.get("sources"))
        snapshot = update.source_handler()
        return {"accepted": accepted, "rejected": rejected, "snapshot": snapshot}

    new_source = sources.create(**data)
    update = Updater(profile=kwargs.get("profile"), sources=kwargs.get("sources"))
    snapshot = update.source_handler()
    return {"accepted": [new_source], "rejected": [], "snapshot": snapshot}


@validator.UserValidator
@SourceGetValidator
@transaction.atomic
def delete_source(uid, source: str, *args, **kwargs):
    """Delete one source and return deleted payload + refreshed snapshot."""
    logger.debug(f"Deleting source {source} for {uid}")
    source_obj = kwargs.get("source_check")
    source_payload = {
        "source": source_obj.source,
        "acc_type": source_obj.acc_type,
        "amount": source_obj.amount,
        "currency": source_obj.currency,
    }
    source_obj.delete()
    update = Updater(profile=kwargs.get("profile"), sources=kwargs.get("sources"))
    snapshot = update.source_handler()
    return {"deleted": source_payload, "snapshot": snapshot}


@validator.UserValidator
@SourceGetValidator
@transaction.atomic
def update_source(uid, source: str, data: dict, *, partial: bool = False, **kwargs):
    """Update one source (PATCH/PUT validation differs via ``partial`` flag)."""
    logger.debug(f"Updating source {source} for {uid}")
    source_obj = kwargs.get("checked")
    if partial:
        validate_source_patch_payload(uid, data, source_obj)
    else:
        validate_source_put_payload(uid, data, source_obj)
    locked = PaymentSource.objects.for_user(uid).select_for_update().get(pk=source_obj.pk)
    amount_declared = Decimal(str(data["amount"])) if "amount" in data else None
    update_fields = []
    for field, value in data.items():
        if field in {"amount", "opening_amount"}:
            continue
        setattr(locked, field, value)
        update_fields.append(field)
    if amount_declared is not None:
        fc = Calculator(profile=kwargs.get("profile"))
        ledger = fc.ledger_sum_for_source(locked)
        locked.opening_amount = (amount_declared - ledger).quantize(Decimal("0.01"))
        locked.amount = amount_declared.quantize(Decimal("0.01"))
        update_fields.extend(["amount", "opening_amount"])
    if update_fields:
        locked.save(update_fields=list(dict.fromkeys(update_fields)))
    update = Updater(profile=kwargs.get("profile"), sources=kwargs.get("sources"))
    snapshot = update.source_handler()
    return {"updated": locked, "snapshot": snapshot}


@validator.UserValidator
def get_sources(uid, **kwargs):
    """Return source queryset, optionally filtered by account type/source name."""
    sources = PaymentSource.objects.for_user(uid)
    acc_type = kwargs.get("acc_type")
    source = kwargs.get("source")
    if acc_type:
        sources = sources.filter(acc_type=str(acc_type).upper())
    if source:
        sources = sources.filter(source__icontains=str(source).lower())
    return {"sources": sources}


@validator.UserValidator
@SourceGetValidator
def get_source(uid, source: str, *args, **kwargs):
    """Return a single validated source object."""
    return {"source": kwargs.get("checked")}


@validator.UserValidator
def preview_source_balance_rebuild(uid, **kwargs):
    """Read-only Data Hub preview: current vs ledger vs unexplained. No writes."""
    profile = kwargs.get("profile")
    fc = Calculator(profile=profile)
    rows = [fc.source_balance_preview(source) for source in PaymentSource.objects.for_user(uid)]
    return {"sources": rows}


@validator.UserValidator
@transaction.atomic
def apply_source_balance_rebuild(uid, data, **kwargs):
    """Apply user-accepted proposed amounts: opening = proposed - ledger, amount = proposed."""
    items = data.get("sources") if isinstance(data, dict) else None
    if not items:
        raise ValidationError("No sources to rebuild")
    profile = kwargs.get("profile")
    fc = Calculator(profile=profile)
    maps = load_source_maps(uid)
    applied = []
    for item in items:
        name = str(item.get("source") or "").strip()
        if not name:
            raise ValidationError("Source does not exist")
        source_id = resolve_name_to_id(name.lower(), maps)
        if not source_id:
            raise ValidationError("Source does not exist")
        locked = (
            PaymentSource.objects.for_user(uid)
            .select_for_update()
            .filter(source_id=source_id)
            .first()
        )
        if not locked:
            raise ValidationError("Source does not exist")
        proposed = Decimal(str(item["proposed_amount"])).quantize(Decimal("0.01"))
        ledger = fc.ledger_sum_for_source(locked)
        locked.opening_amount = (proposed - ledger).quantize(Decimal("0.01"))
        locked.amount = proposed
        locked.save(update_fields=["opening_amount", "amount"])
        applied.append(locked)
    update = Updater(profile=profile, sources=list(PaymentSource.objects.for_user(uid)))
    snapshot = update.source_handler()
    return {"updated": applied, "snapshot": snapshot}

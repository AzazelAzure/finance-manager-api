"""Service layer for payment source CRUD operations."""

import finance.logic.validators as validator
from finance.validators.source_validators import (
    SourceGetValidator,
    SourceSetValidator,
    validate_source_patch_payload,
    validate_source_put_payload,
)
from finance.logic.updaters import Updater 
from django.db import transaction
from loguru import logger
from finance.models import PaymentSource

# Payment Source Functions
@validator.UserValidator
@SourceSetValidator
@transaction.atomic
def add_source(uid, data, *args, **kwargs):
    """Create one or more sources and return accepted/rejected + snapshot."""
    logger.debug(f"Creating source payload for {uid}")
    sources = kwargs.get('sources')
    if isinstance(data, list):
        rejected = kwargs.get('rejected',[])
        accepted = kwargs.get('accepted',[])
        sources.bulk_create([PaymentSource(**item) for item in accepted])
        update = Updater(profile=kwargs.get('profile'), sources=kwargs.get('sources'))
        snapshot = update.source_handler()
        return {'accepted': accepted, 'rejected': rejected, 'snapshot': snapshot}

    else:
        new_source = sources.create(**data)
        update = Updater(profile=kwargs.get('profile'), sources=kwargs.get('sources'))
        snapshot = update.source_handler()
    return {'accepted': [new_source], 'rejected': [], 'snapshot': snapshot}


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
    update = Updater(profile=kwargs.get('profile'), sources=kwargs.get('sources'))
    snapshot = update.source_handler()
    return {"deleted": source_payload, "snapshot": snapshot}


@validator.UserValidator
@SourceGetValidator
@transaction.atomic
def update_source(uid, source: str, data: dict, *, partial: bool = False, **kwargs):
    """Update one source (PATCH/PUT validation differs via ``partial`` flag)."""
    logger.debug(f"Updating source {source} for {uid}")
    source_obj = kwargs.get('checked')
    if partial:
        validate_source_patch_payload(uid, data, source_obj)
    else:
        validate_source_put_payload(uid, data, source_obj)
    for field, value in data.items():
        setattr(source_obj, field, value)
    source_obj.save(update_fields=list(data.keys()))
    update = Updater(profile=kwargs.get('profile'), sources=kwargs.get('sources'))
    snapshot = update.source_handler()
    return {"updated": source_obj, "snapshot": snapshot}

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


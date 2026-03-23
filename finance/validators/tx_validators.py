"""
Transaction-specific validation decorators and helpers.

Used by :mod:`finance.services.transaction_services`. Expects ``profile`` (``AppProfile``)
to be injected by :func:`finance.logic.validators.UserValidator` when the view is
authenticated; if missing, :func:`_ensure_profile` loads it once by ``uid`` so services
stay usable when composed without the full decorator stack.
"""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from functools import wraps

from django.forms.models import model_to_dict
from rest_framework.exceptions import ValidationError

import zoneinfo
from finance.logic.updaters import Updater
from finance.models import AppProfile, Category, PaymentSource, Tag, Transaction, UpcomingExpense
from finance.validators.validation_core import _validate_currency
from loguru import logger

# Client may send these on payloads; they must not change persisted identity fields.
_IMMUTABLE_TRANSACTION_KEYS = frozenset({"tx_id", "entry_id", "id"})


def _ensure_profile(uid, kwargs) -> AppProfile:
    """
    Resolve ``AppProfile`` for this user.

    Prefer ``kwargs['profile']`` when the view / outer validators already passed it
    (avoids an extra query). Otherwise load by ``uid`` once and cache on ``kwargs``.
    """
    profile = kwargs.get("profile")
    if profile is not None:
        return profile
    profile = AppProfile.objects.for_user(uid).first()
    if not profile:
        logger.error(f"User does not exist: {uid}")
        raise ValidationError("User does not exist")
    kwargs["profile"] = profile
    return profile


def _tag_string_set_for_user(uid) -> set:
    """
    All tag strings available for this user, from Tag rows (one query).
    Flattens JSON tag lists without using values_list on nested structures.
    """
    out: set = set()
    for row in Tag.objects.for_user(uid).only("tags"):
        raw = row.tags
        if raw is None:
            continue
        if isinstance(raw, list):
            for t in raw:
                if t is not None and t != "":
                    out.add(str(t))
        else:
            out.add(str(raw))
    return out


def _merge_transaction_patch(tx: Transaction, patch: dict) -> dict:
    """
    Full row dict for validation/fixers: DB row overlaid with PATCH keys.
    Ignores immutable / relic keys (tx_id, entry_id, uid from stale clients).
    """
    merged = model_to_dict(tx)
    merged.setdefault("tx_id", tx.tx_id)
    merged.setdefault("created_on", tx.created_on)
    for key, value in patch.items():
        if key in _IMMUTABLE_TRANSACTION_KEYS:
            continue
        if key == "uid":
            continue
        merged[key] = value
    return merged


def _validated_patch_for_save(merged: dict, original_patch_keys: set) -> dict:
    """Subset of merged fields that the client attempted to change (fixed values)."""
    allowed = original_patch_keys - _IMMUTABLE_TRANSACTION_KEYS - {"uid"}
    return {k: merged[k] for k in allowed if k in merged}


def _validate_transaction(
    uid,
    data: dict,
    source_check,
    tags,
    upcoming_check,
    cat_check,
    profile: AppProfile,
    *,
    accumulated_new_tags=None,
    validate_keys=None,
):
    logger.debug(f"Validating transaction payload for {uid}")
    if "amount" in data and data["amount"] is not None:
        if isinstance(data["amount"], (list, dict, set)):
            raise ValidationError("Invalid amount")
        if data["amount"] == "":
            raise ValidationError("Invalid amount")
        try:
            Decimal(str(data["amount"]))
        except (InvalidOperation, ValueError, TypeError):
            raise ValidationError("Invalid amount")
    if "amount" in data and data["amount"] is None:
        raise ValidationError("Invalid amount")
    if data.get("tx_type") is None:
        raise ValidationError("Invalid transaction type")
    if not isinstance(data["tx_type"], str):
        raise ValidationError("Invalid transaction type")
    valid_types = {choice.value for choice in Transaction.TxType}
    if data["tx_type"] not in valid_types:
        raise ValidationError("Invalid transaction type")
    if data.get("date") is not None:
        d = data["date"]
        if isinstance(d, (list, tuple, dict, set)):
            raise ValidationError("Invalid date")
        if isinstance(d, str):
            try:
                date.fromisoformat(d)
            except ValueError:
                raise ValidationError("Invalid date")
    for scalar_key in ("source", "currency", "category", "bill", "description"):
        if data.get(scalar_key) is not None and isinstance(
            data[scalar_key], (list, dict, set)
        ):
            raise ValidationError(f"Invalid {scalar_key}")
    if data.get("source") is None or data.get("source") == "":
        raise ValidationError("Source does not exist")
    if not data["source"] in source_check:
        logger.error(f"Source does not exist: {data['source']}")
        raise ValidationError("Source does not exist")
    if data.get("currency") is None or data.get("currency") == "":
        raise ValidationError("Currency does not exist")
    _validate_currency(data["currency"])
    if (validate_keys is None or "category" in validate_keys) and data.get("category"):
        if data["category"] not in cat_check:
            logger.error(f"Category does not exist: {data['category']}")
            raise ValidationError("Category does not exist")
    if "tags" in data:
        if data["tags"] is None or data["tags"] == "":
            data["tags"] = []
        elif isinstance(data["tags"], str):
            data["tags"] = [data["tags"]]
        elif not isinstance(data["tags"], (list, tuple)):
            raise ValidationError("Invalid tags")
        else:
            data["tags"] = list(data["tags"])
    if data.get("tags"):
        new_tags = set()
        for tag in data["tags"]:
            if not isinstance(tag, str):
                raise ValidationError("Invalid tags")
            if tag not in tags:
                logger.warning(f"Tag does not exist: {tag}.  Creating...")
                new_tags.add(tag)
        if new_tags:
            if accumulated_new_tags is not None:
                accumulated_new_tags.update(new_tags)
            else:
                update_tags = list(new_tags | tags)
                Tag.objects.for_user(uid).update(tags=update_tags)
    else:
        today = datetime.now(zoneinfo.ZoneInfo(profile.timezone)).date()
        tx_date = data["date"]
        if isinstance(tx_date, str):
            tx_date = date.fromisoformat(tx_date)
        if tx_date > today:
            raise ValidationError("Date cannot be in the future")
    if data.get("bill"):
        if not data["bill"] in upcoming_check:
            logger.error(f"Expense does not exist: {data['bill']}")
            raise ValidationError("Expense does not exist")
        if data["tx_type"] != "EXPENSE":
            logger.error(f"Expense must be an expense: {data['tx_type']}")
            raise ValidationError("Expense must be an expense")
    return data


def TransactionValidator(func):
    """
    Decorator to validate a transaction.
    Checks if all required fields are valid, and fixes any data that needs to be fixed.
    Raises a ValidationError if any validation fails.

    Supports:
        - add_transaction(uid, data | list)
        - update_transaction(uid, tx_id, data) — after TransactionIDValidator sets
          id_check and patch=True on kwargs.

    Requires ``AppProfile`` in kwargs when available (typically from UserValidator);
    otherwise loads it once.
    """
    @wraps(func)
    def _wrapped(uid, *args, **kwargs):
        profile = _ensure_profile(uid, kwargs)
        sources_obj = kwargs.get("sources") or PaymentSource.objects.for_user(uid)
        sources = sources_obj if isinstance(sources_obj, list) else list(sources_obj)
        tags = _tag_string_set_for_user(uid)
        upcoming_obj = kwargs.get("upcoming") or UpcomingExpense.objects.for_user(uid)
        upcoming = upcoming_obj if isinstance(upcoming_obj, list) else list(upcoming_obj)
        upcoming_check = {u.name for u in upcoming}

        source_check = kwargs.get("source_check") or {s.source for s in sources}
        # `cat_check` is loaded lazily only when needed by validation.
        cat_check = set()
        kwargs["source_check"] = source_check
        kwargs["upcoming_check"] = upcoming_check
        kwargs["sources"] = sources
        kwargs["upcoming"] = upcoming
        update = Updater(profile=profile)

        id_check = kwargs.get("id_check")
        patch = kwargs.get("patch")

        if patch and id_check is not None:
            if len(args) < 2:
                raise ValidationError("Invalid transaction update payload")
            tx_id, data = args[0], args[1]
            if not isinstance(data, dict):
                raise ValidationError("Transaction update payload must be a dict")
            if data.get("uid") is not None and not isinstance(data["uid"], str):
                raise ValidationError("Invalid uid")
            if str(tx_id) != str(id_check.tx_id):
                logger.error(f"Transaction id mismatch: {tx_id} vs {id_check.tx_id}")
                raise ValidationError("Transaction does not exist")
            original_keys = set(data.keys())
            merged = _merge_transaction_patch(id_check, data)
            # PATCH validation runs against a merged full row so required fields remain enforced.
            logger.debug(f"Validating merged PATCH payload for {uid}")

            # Only validate `category` if the client explicitly provided it.
            if "category" in original_keys:
                cat_check = set(Category.objects.for_user(uid).values_list("name", flat=True))
            else:
                cat_check = set()

            _validate_transaction(
                uid,
                merged,
                source_check,
                tags,
                upcoming_check,
                cat_check,
                profile,
                validate_keys=original_keys,
            )
            update.fix_tx_data([merged])
            patch_save = _validated_patch_for_save(merged, original_keys)
            kwargs["tags"] = tags
            rest = args[2:] if len(args) > 2 else ()
            return func(uid, tx_id, patch_save, *rest, **kwargs)

        if not args:
            raise ValidationError("Missing transaction payload")

        data = args[0]
        rest = args[1:]

        if isinstance(data, list):
            rejected = []
            accepted = []
            accumulated_new_tags = set()

            # For POST/bulk payloads, validate category only if present.
            cat_check = (
                set(Category.objects.for_user(uid).values_list("name", flat=True))
                if any(isinstance(item, dict) and item.get("category") for item in data)
                else set()
            )

            for item in data:
                logger.debug(f"Validating transaction item for {uid}")
                try:
                    _validate_transaction(
                        uid,
                        item,
                        source_check,
                        tags,
                        upcoming_check,
                        cat_check,
                        profile,
                        accumulated_new_tags=accumulated_new_tags,
                    )
                    accepted.append(item)
                except ValidationError as e:
                    logger.error(f"Transaction validation failed: {e}")
                    rejected.append(item)
            if not accepted:
                raise ValidationError("No valid transactions")
            if accumulated_new_tags:
                update_tags = list(tags | accumulated_new_tags)
                Tag.objects.for_user(uid).update(tags=update_tags)
            kwargs["rejected"] = rejected
            kwargs["accepted"] = accepted
            kwargs["tags"] = tags
            update.fix_tx_data(accepted)
            return func(uid, data, *rest, **kwargs)

        if isinstance(data, dict):
            logger.debug(f"Validating single transaction payload for {uid}")

            cat_check = (
                set(Category.objects.for_user(uid).values_list("name", flat=True))
                if data.get("category")
                else set()
            )

            _validate_transaction(
                uid, data, source_check, tags, upcoming_check, cat_check, profile
            )
            update.fix_tx_data([data])
            kwargs["tags"] = tags
            return func(uid, data, *rest, **kwargs)

        raise ValidationError("Invalid transaction payload")
    return _wrapped


def TransactionIDValidator(func):
    """
    Decorator to validate a transaction id.
    Checks if the transaction exists for this user (scoped queryset).
    Raises a ValidationError if the transaction does not exist.
    """
    @wraps(func)
    def _wrapped(uid, tx_id: str, *args, **kwargs):
        logger.debug(f"Validating transaction id for {uid}")
        to_check = Transaction.objects.for_user(uid).get_tx(tx_id=tx_id).first()
        if not to_check:
            logger.error(f"Transaction does not exist: {tx_id}")
            raise ValidationError("Transaction does not exist")
        kwargs["id_check"] = to_check
        kwargs["patch"] = True
        return func(uid, tx_id, *args, **kwargs)
    return _wrapped

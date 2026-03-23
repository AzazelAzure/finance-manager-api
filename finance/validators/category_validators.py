from functools import wraps

from rest_framework.exceptions import ValidationError

from finance.models import Category
from loguru import logger

_DEFAULT_CATEGORIES = {"expense", "income", "transfer"}


def _validate_category(uid, data: dict, cat_check: set, patch: bool):
    """Validate and normalize category payload fields."""
    logger.debug(f"Validating category payload for {uid}")
    name = str(data.get("name", "")).strip().lower()
    if not name:
        raise ValidationError("Category name required")
    data["name"] = name
    if not patch and name in cat_check:
        raise ValidationError("Category already exists")
    if patch and name in _DEFAULT_CATEGORIES:
        raise ValidationError("Cannot use default category")
    return data


def CategorySetValidator(func):
    """Validate category create payloads (single and bulk)."""
    @wraps(func)
    def _wrapped(uid, data, *args, **kwargs):
        categories = kwargs.get("categories") or Category.objects.for_user(uid)
        cat_check = set(categories.values_list("name", flat=True))
        patch = kwargs.get("patch") or False
        kwargs["categories"] = categories
        if isinstance(data, list):
            rejected = []
            accepted = []
            for item in data:
                try:
                    _validate_category(uid, item, cat_check, patch)
                    accepted.append(item)
                except ValidationError:
                    rejected.append(item)
            if not accepted:
                raise ValidationError("No valid categories")
            kwargs["accepted"] = accepted
            kwargs["rejected"] = rejected
            return func(uid, data, *args, **kwargs)
        _validate_category(uid, data, cat_check, patch)
        return func(uid, data, *args, **kwargs)

    return _wrapped


def CategoryGetValidator(func):
    """Validate category identity for get/update/delete operations."""
    @wraps(func)
    def _wrapped(uid, cat_name: str, *args, **kwargs):
        categories = Category.objects.for_user(uid)
        normalized = str(cat_name).strip().lower()
        if normalized in _DEFAULT_CATEGORIES:
            raise ValidationError("Cannot modify default category")
        checked = categories.filter(name=normalized).first()
        if not checked:
            raise ValidationError("Category does not exist")
        kwargs["categories"] = categories
        kwargs["checked"] = checked
        kwargs["patch"] = True
        return func(uid, normalized, *args, **kwargs)

    return _wrapped

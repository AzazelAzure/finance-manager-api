from functools import wraps

from rest_framework.exceptions import ValidationError

from finance.models import Tag
from loguru import logger


def _normalize_tags(tag_rows):
    """Flatten stored tag rows into a lowercase unique set."""
    normalized = set()
    for row in tag_rows:
        raw = row.tags
        if isinstance(raw, list):
            for item in raw:
                if item:
                    normalized.add(str(item).lower())
        elif raw:
            normalized.add(str(raw).lower())
    return normalized


def _validate_tags(data, tags, update=False):
    """Validate a tag for create/delete/rename operations."""
    data = str(data).lower()
    logger.debug("Validating tag payload")
    if update:
        if data in tags:
            raise ValidationError("Tag already exists")
    else:
        if data not in tags:
            raise ValidationError("Tag does not exist")
    return data


def TagSetValidator(func):
    """Validate tag create payloads and split into accepted/rejected."""
    @wraps(func)
    def _wrapped(uid, data, *args, **kwargs):
        tag_rows = Tag.objects.for_user(uid)
        tags = _normalize_tags(tag_rows)
        incoming = data.get("tags") if isinstance(data, dict) else data
        if incoming is None:
            raise ValidationError("No valid tags")
        if not isinstance(incoming, list):
            incoming = [incoming]
        accepted = []
        rejected = []
        for item in incoming:
            item = str(item).lower()
            if item in tags:
                rejected.append(item)
            else:
                accepted.append(item)
        if not accepted:
            raise ValidationError("No valid tags")
        kwargs["accepted"] = accepted
        kwargs["rejected"] = rejected
        kwargs["existing_tags"] = tags
        return func(uid, {"tags": incoming}, *args, **kwargs)

    return _wrapped


def TagGetValidator(func):
    """Validate tag patch payload and derive delete/update operation sets."""
    @wraps(func)
    def _wrapped(uid, data: dict, *args, **kwargs):
        tags = _normalize_tags(Tag.objects.for_user(uid))
        payload = data.get("tags")
        if not isinstance(payload, dict):
            raise ValidationError("tags must be an object")
        accepted = []
        rejected = []
        to_delete = []
        update = {}
        for key, value in payload.items():
            current = str(key).lower()
            try:
                _validate_tags(current, tags)
                if value in [None, False, "", "''", '""', "delete"]:
                    to_delete.append(current)
                else:
                    new_name = _validate_tags(value, tags, update=True)
                    update[current] = new_name
                accepted.append(current)
            except ValidationError:
                rejected.append(current)
        if not accepted:
            raise ValidationError("No valid tags")
        if to_delete and update:
            raise ValidationError("Cannot delete and update tags at the same time")
        kwargs["accepted"] = accepted
        kwargs["rejected"] = rejected
        kwargs["to_delete"] = to_delete
        kwargs["update"] = update
        kwargs["existing_tags"] = tags
        return func(uid, data, *args, **kwargs)

    return _wrapped

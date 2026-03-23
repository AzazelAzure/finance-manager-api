"""
This module handles all tag-related functionality for the finance manager application.

Attributes:
    add_tag: Adds a tag to the user's account.
    delete_tag: Deletes a tag from the user's account.
    bulk_add_tags: Adds a list of tags to the user's account.
    get_tags: Retrieves a list of tags for a user.
    bulk_delete_tags: Deletes a list of tags from the user's account.
"""
from django.db import transaction
import finance.logic.validators as validator
from finance.validators.tag_validators import TagGetValidator, TagSetValidator
from loguru import logger
from finance.models import  Tag


@validator.UserValidator
@TagSetValidator
@transaction.atomic
def add_tags(uid, data, *args, **kwargs):
    """
    Adds a tag to the user's account.

    :param uid: The user id.
    :type uid: str
    :param data: The data for the tag.
    :type data: dict
    :returns: {'added': queryset}
    :rtype: dict
    """
    logger.debug(f"Adding tag: {data}")
    accepted = kwargs.get("accepted", [])
    rejected = kwargs.get("rejected", [])
    existing = set(kwargs.get("existing_tags", set()))
    update_tags = sorted(existing | set(accepted))
    tag_obj = Tag.objects.for_user(uid).first()
    if tag_obj:
        tag_obj.tags = update_tags
        tag_obj.save(update_fields=["tags"])
    else:
        Tag.objects.create(uid=uid, tags=update_tags)
    return {"accepted": accepted, "rejected": rejected}


@validator.UserValidator
@TagGetValidator
@transaction.atomic
def delete_tag(uid, data, *args, **kwargs):
    """
    Deletes a tag from the user's account.

    :param uid: The user id.
    :type uid: str
    :param tag_name: The name of the tag to delete.
    :type tag_name: str
    :returns: {'deleted': queryset}
    :rtype: dict
    """
    logger.debug(f"Deleting tags: {data}")
    to_delete = set(kwargs.get("to_delete", []))
    existing = set(kwargs.get("existing_tags", set()))
    updated_tags = sorted(existing - to_delete)
    tag_obj = Tag.objects.for_user(uid).first()
    if tag_obj:
        tag_obj.tags = updated_tags
        tag_obj.save(update_fields=["tags"])
    return {"deleted": sorted(to_delete), "rejected": kwargs.get("rejected", [])}

@validator.UserValidator
@TagGetValidator
@transaction.atomic
def update_tag(uid, data, *args, **kwargs):
    """
    Updates a tag in the user's account.

    :param uid: The user id.
    :type uid: str
    :param data: The data for the tag.
    :type data: dict
    :returns: {'updated': queryset}
    :rtype: dict
    """
    logger.debug(f"Updating tag: {data}")
    mapping = kwargs.get("update", {})
    existing = list(kwargs.get("existing_tags", set()))
    if not mapping:
        return {"updated": []}
    normalized = []
    for tag in existing:
        if tag in mapping:
            normalized.append(mapping[tag])
        else:
            normalized.append(tag)
    tag_obj = Tag.objects.for_user(uid).first()
    if tag_obj:
        tag_obj.tags = sorted(set(normalized))
        tag_obj.save(update_fields=["tags"])
    return {"updated": sorted(mapping.values()), "rejected": kwargs.get("rejected", [])}


@validator.UserValidator
def get_tags(uid, *args, **kwargs):
    """
    Retrieves all tags for a user.

    :param uid: The user id.
    :type uid: str
    :returns: {'tags': queryset}
    :rtype: dict
    """
    logger.debug(f"Getting all tags for {uid}")
    tag_obj = Tag.objects.for_user(uid).first()
    if not tag_obj:
        return {"tags": []}
    tags = tag_obj.tags if isinstance(tag_obj.tags, list) else [tag_obj.tags]
    return {"tags": sorted({str(item).lower() for item in tags if item})}

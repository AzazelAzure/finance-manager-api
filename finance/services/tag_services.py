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
from loguru import logger
from finance.models import AppProfile, Tag

@transaction.atomic
@validator.UserValidator
@validator.TagValidator
def add_tag(uid, data: dict):
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
    uid = AppProfile.objects.for_user(uid)
    tag = Tag.objects.create(uid=uid, **data)
    return {'added': tag}

@transaction.atomic
@validator.UserValidator
@validator.TagValidator
def delete_tag(uid, tag_name: str):
    """
    Deletes a tag from the user's account.

    :param uid: The user id.
    :type uid: str
    :param tag_name: The name of the tag to delete.
    :type tag_name: str
    :returns: {'deleted': queryset}
    :rtype: dict
    """
    logger.debug(f"Deleting tag: {tag_name}")
    tag = Tag.objects.for_user(uid).get_by_name(tag_name)
    tag.delete()
    return {'deleted': tag}

@transaction.atomic
@validator.UserValidator
@validator.TagValidator
def update_tag(uid, name: str, data: dict):
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
    tag = Tag.objects.for_user(uid).get_by_name(name)
    tag.update(**data)
    return {'updated': tag}

@validator.UserValidator
def bulk_add_tags(uid, data: list):
    """
    Adds a list of tags to the user's account.

    :param uid: The user id.
    :type uid: str
    :param data: A list of dictionaries representing the tags to add.
    :type data: list
    :returns: {'added': [queryset]}
    :rtype: dict
    """
    logger.debug(f"Adding bulk tags: {data}")
    added = []
    for item in data:
        logger.debug(f"Adding tag: {item}")
        add_tag(uid, item)
        added.append(Tag.objects.for_user(uid).get_by_name(item['name']))
    return {'added': added}

@validator.UserValidator
def get_tags(uid):
    """
    Retrieves all tags for a user.

    :param uid: The user id.
    :type uid: str
    :returns: {'tags': queryset}
    :rtype: dict
    """
    logger.debug(f"Getting all tags for {uid}")
    return {'tags': Tag.objects.for_user(uid)}

@validator.UserValidator
def bulk_delete_tags(uid, data: list):
    """
    Deletes a list of tags from the user's account.

    :param uid: The user id.
    :type uid: str
    :param data: A list of tag names to delete.
    :type data: list
    :returns: {'deleted': [queryset]}
    :rtype: dict
    """
    logger.debug(f"Deleting bulk tags: {data}")
    deleted = []
    for item in data:
        logger.debug(f"Deleting tag: {item}")
        delete_tag(uid, item)
        deleted.append(Tag.objects.for_user(uid).get_by_name(item))
    return {'deleted': deleted}

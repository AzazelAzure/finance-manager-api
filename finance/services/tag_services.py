"""
This module handles all tag-related functionality for the finance manager application.

Attributes:
    add_tag: Adds a tag to the user's account.
    delete_tag: Deletes a tag from the user's account.
    bulk_add_tags: Adds a list of tags to the user's account.
    get_tags: Retrieves a list of tags for a user.
    bulk_delete_tags: Deletes a list of tags from the user's account.
"""

import finance.logic.validators as validator
from loguru import logger
from finance.models import AppProfile, Tag


@validator.UserValidator
@validator.TagValidator
def add_tag(uid, data: dict):
    """
    Adds a tag to the user's account.

    :param uid: The user id.
    :type uid: str
    :param data: The data for the tag.
    :type data: dict
    :returns: {'message': "Tag added successfully"}
    :rtype: dict
    """
    logger.debug(f"Adding tag: {data}")
    uid = AppProfile.objects.for_user(uid).get()
    tag = Tag.objects.create(uid=uid, **data)
    return {'message': "Tag added successfully"}

@validator.UserValidator
@validator.TagValidator
def delete_tag(uid, tag_name: str):
    """
    Deletes a tag from the user's account.

    :param uid: The user id.
    :type uid: str
    :param tag_name: The name of the tag to delete.
    :type tag_name: str
    :returns: {'message': "Tag deleted successfully"}
    :rtype: dict
    """
    logger.debug(f"Deleting tag: {tag_name}")
    tag = Tag.objects.for_user(uid).get_by_name(tag_name)
    tag.delete()
    return {'message': "Tag deleted successfully"}

@validator.UserValidator
def user_bulk_add_tags(uid, data: list):
    """
    Adds a list of tags to the user's account.

    :param uid: The user id.
    :type uid: str
    :param data: A list of dictionaries representing the tags to add.
    :type data: list
    :returns: {'message': "Bulk tags added successfully"}
    :rtype: dict
    """
    logger.debug(f"Adding bulk tags: {data}")
    for item in data:
        logger.debug(f"Adding tag: {item}")
        add_tag(uid, item)
    return {'message': "Bulk tags added successfully"}

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
    return {'tags': Tag.objects.for_user(uid).all()}

@validator.UserValidator
def bulk_delete_tags(uid, data: list):
    """
    Deletes a list of tags from the user's account.

    :param uid: The user id.
    :type uid: str
    :param data: A list of tag names to delete.
    :type data: list
    :returns: {'message': "Bulk tags deleted successfully"}
    :rtype: dict
    """
    logger.debug(f"Deleting bulk tags: {data}")
    for item in data:
        logger.debug(f"Deleting tag: {item}")
        delete_tag(uid, item)
    return {'message': "Bulk tags deleted successfully"}
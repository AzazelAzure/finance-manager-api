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
from finance.models import  Tag


@validator.UserValidator
@validator.TagSetValidator
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
    profile = kwargs.get('profile')
    tags = kwargs.get('tags')
    accepted = kwargs.get('accepted')
    rejected = kwargs.get('rejected')
    tags += accepted
    tags.save()
    return {'accepted': accepted, 'rejected': rejected}


@validator.UserValidator
@validator.TagGetValidator
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
    tags = kwargs.get('tags')
    delete_tag = set(kwargs.get('to_delete'))
    tags = [item for item in tags if item not in delete_tag]
    tags.save()
    delete_tag = list(delete_tag)
    return {'deleted': delete_tag}

@validator.UserValidator
@validator.TagGetValidator
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
    tags = kwargs.get('tags')
    update_tag = kwargs.get('update')
    accepted = set(kwargs.get('accepted'))
    tags += update_tag
    tags = [item for item in tags if item not in accepted]
    tags.save()
    updated = list(accepted)
    return {'updated': updated}


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
    return {'tags': Tag.objects.for_user(kwargs.get('profile').user_id)}

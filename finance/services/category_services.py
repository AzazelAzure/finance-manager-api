"""

"""


import finance.logic.validators as validator
from finance.logic.updaters import Updater
from django.db import transaction
from loguru import logger
from finance.models import Category

# TODO: Update docstrings for repurpose of this

@validator.UserValidator
@validator.CategorySetValidator
@transaction.atomic
def add_category(uid, data, *args, **kwargs):
    categories = kwargs.get('categories')
    if isinstance(data, list):
        reject = kwargs.get('rejected')
        accept = kwargs.get('accepted')
        categories.bulk_create([Category(**item) for item in data]) 
        if reject:
            return {'accepted':accept, 'rejected':reject}
        return {'accepted': accept}
    else:
        categories.create(**data)
        return {'accepted': data}
    
@validator.UserValidator
@validator.CategoryGetValidator
@validator.CategorySetValidator
@transaction.atomic
def update_category(uid, cat_name, data, *args, **kwargs):
    categories = kwargs.get('categories')
    categories.filter(name=cat_name).update(**data)
    update = Updater(profile=kwargs.get('profile'))
    update.category_changed(cat_name, data['name'])
    return {'updated': data}

@validator.UserValidator
@validator.CategoryGetValidator
def get_category(uid, cat_name, *args, **kwargs):
    checked = kwargs.get('checked')
    return {'category': checked}

@validator.UserValidator
@validator.CategoryGetValidator
@transaction.atomic
def delete_category(uid, cat_name, *args, **kwargs):
    checked = kwargs.get('checked')
    deleted = checked['name']
    checked.delete()
    update = Updater(profile=kwargs.get('profile'))
    update.category_deleted(deleted)
    return {'deleted': checked}

@validator.UserValidator
def get_all_categories(uid, *args, **kwargs):
    categories = Category.objects.for_user(uid)
    return {'categories': categories}

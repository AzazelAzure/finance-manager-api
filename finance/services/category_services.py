"""Service layer for category CRUD operations."""


import finance.logic.validators as validator
from finance.validators.category_validators import CategoryGetValidator, CategorySetValidator
from finance.logic.updaters import Updater
from django.db import transaction
from rest_framework.exceptions import ValidationError
from finance.models import Category

@validator.UserValidator
@CategorySetValidator
@transaction.atomic
def add_category(uid, data, *args, **kwargs):
    """Create one or more categories and return accepted/rejected rows."""
    categories = kwargs.get('categories')
    if isinstance(data, list):
        reject = kwargs.get("rejected", [])
        accept = kwargs.get("accepted", [])
        created = categories.bulk_create([Category(uid=uid, **item) for item in accept])
        return {"accepted": created, "rejected": reject}
    created = categories.create(uid=uid, **data)
    return {"accepted": [created], "rejected": []}
    
@validator.UserValidator
@CategoryGetValidator
@transaction.atomic
def update_category(uid, cat_name, data, *args, **kwargs):
    """Rename a category and propagate the change to matching transactions."""
    checked = kwargs.get("checked")
    new_name = str(data.get("name", "")).strip().lower()
    if not new_name:
        raise ValidationError("Category name required")
    if new_name in {"expense", "income", "transfer"}:
        raise ValidationError("Cannot use default category")
    existing = set(Category.objects.for_user(uid).values_list("name", flat=True))
    if new_name != checked.name and new_name in existing:
        raise ValidationError("Category already exists")
    previous_name = checked.name
    checked.name = new_name
    checked.save(update_fields=["name"])
    if previous_name != checked.name:
        update = Updater(profile=kwargs.get("profile"))
        update.category_changed(previous_name, checked.name)
    return {"updated": checked}

@validator.UserValidator
@CategoryGetValidator
def get_category(uid, cat_name, *args, **kwargs):
    """Return a single validated category row."""
    checked = kwargs.get("checked")
    return {"category": checked}

@validator.UserValidator
@CategoryGetValidator
@transaction.atomic
def delete_category(uid, cat_name, *args, **kwargs):
    """Delete a category and reset affected transactions to default categories."""
    checked = kwargs.get("checked")
    deleted_name = checked.name
    deleted = {"name": checked.name}
    checked.delete()
    update = Updater(profile=kwargs.get("profile"))
    update.category_deleted(deleted_name)
    return {"deleted": deleted}

@validator.UserValidator
def get_categories(uid, *args, **kwargs):
    """Return all categories for the user."""
    categories = Category.objects.for_user(uid)
    return {'categories': categories}

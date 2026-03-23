from datetime import date, datetime
from functools import wraps

import zoneinfo
from loguru import logger
from rest_framework.exceptions import ValidationError

from finance.logic.updaters import Updater
from finance.models import UpcomingExpense
from finance.validators.validation_core import _validate_currency


def UpcomingExpenseSetValidator(func):
    """Validate expense payloads for create/update handlers."""
    @wraps(func)
    def _wrapped(uid, *args, **kwargs):
        if not args:
            raise ValidationError("Missing expense payload")
        patch = kwargs.get("patch") or False
        if patch and len(args) >= 2 and isinstance(args[1], dict):
            expense_name = args[0]
            data = args[1]
            rest = args[2:]
        else:
            expense_name = None
            data = args[0]
            rest = args[1:]
        logger.debug(f"Validating expense payload for {uid}")
        profile = kwargs.get("profile")
        upcoming = kwargs.get("upcoming") or UpcomingExpense.objects.for_user(profile.user_id)
        upcoming_check = set(upcoming.values_list("name", flat=True))
        existing_name = kwargs.get("existing_name")
        kwargs["upcoming"] = upcoming
        update = Updater(profile=profile)

        if isinstance(data, list):
            rejected = []
            accepted = []
            for item in data:
                try:
                    _validate_expense(
                        uid, item, profile, upcoming_check, patch, existing_name=existing_name
                    )
                    accepted.append(item)
                except ValidationError as e:
                    logger.error(f"Expense validation failed: {e}")
                    rejected.append(item)
            if not accepted:
                raise ValidationError("No valid expenses")
            kwargs["rejected"] = rejected
            kwargs["accepted"] = accepted
            update.fix_expense_data(accepted)
            if expense_name is not None:
                return func(uid, expense_name, data, *rest, **kwargs)
            return func(uid, data, *rest, **kwargs)

        _validate_expense(
            uid, data, profile, upcoming_check, patch, existing_name=existing_name
        )
        update.fix_expense_data([data])
        if expense_name is not None:
            return func(uid, expense_name, data, *rest, **kwargs)
        return func(uid, data, *rest, **kwargs)

    return _wrapped


def UpcomingExpenseGetValidator(func):
    """Ensure expense exists and inject checked/upcoming kwargs."""
    @wraps(func)
    def _wrapped(uid, expense_name: str, *args, **kwargs):
        logger.debug(f"Validating expense lookup for {uid}")
        profile = kwargs.get("profile")
        upcoming = UpcomingExpense.objects.for_user(profile.user_id)
        upcoming_check = upcoming.filter(name=expense_name).first()
        if not upcoming_check:
            logger.error(f"Expense does not exist: {expense_name}")
            raise ValidationError("Expense does not exist")
        kwargs["patch"] = True
        kwargs["upcoming"] = upcoming
        kwargs["checked"] = upcoming_check
        kwargs["existing_name"] = upcoming_check.name
        return func(uid, expense_name, *args, **kwargs)

    return _wrapped


def _validate_expense(uid, data: dict, profile, upcoming_check, patch, existing_name=None):
    """Validate a single expense payload; mutates defaults for date fields."""
    logger.debug(f"Validating expense fields for {uid}")
    if not patch:
        if data["name"] in upcoming_check:
            logger.error(f"Expense already exists: {data['name']}")
            raise ValidationError("Expense already exists")
        if data.get("start_date") and not data.get("due_date"):
            data["due_date"] = data["start_date"]
        if not data.get("start_date") and data.get("due_date"):
            data["start_date"] = data["due_date"]
        if not data.get("start_date") and not data.get("due_date"):
            logger.error(f"Must have either a start date or due date: {data}")
            raise ValidationError("Must have either a start date or due date")
    else:
        if existing_name and existing_name not in upcoming_check:
            logger.error(f"Expense does not exist: {existing_name}")
            raise ValidationError("Expense does not exist")
        new_name = data.get("name")
        if new_name and new_name != existing_name and new_name in upcoming_check:
            logger.error(f"Expense already exists: {new_name}")
            raise ValidationError("Expense already exists")

    if data.get("currency"):
        _validate_currency(data["currency"])
    if data.get("end_date"):
        if data.get("due_date") and data["end_date"] < data["due_date"]:
            logger.error(f"End date cannot be before due date: {data['end_date']}")
            raise ValidationError("End date cannot be before due date")
        today = datetime.now(zoneinfo.ZoneInfo(profile.timezone)).date()
        end_date = data["end_date"]
        if isinstance(end_date, str):
            end_date = date.fromisoformat(end_date)
        if end_date < today:
            logger.error(f"End date cannot be in the past: {data['end_date']}")
            raise ValidationError("End date cannot be in the past")
    return data

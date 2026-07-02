from datetime import date, datetime
from decimal import Decimal
from functools import wraps

import zoneinfo
from loguru import logger
from rest_framework.exceptions import ValidationError

from finance.logic.updaters import Updater
from finance.logic.source_linkage import build_source_check
from finance.models import PaymentSource, UpcomingExpense
from finance.validators.validation_core import _validate_currency

_BILL_CLASSES = {c.value for c in UpcomingExpense.BillClass}


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
        sources_obj = kwargs.get("sources") or PaymentSource.objects.for_user(profile.user_id)
        sources = sources_obj if isinstance(sources_obj, list) else list(sources_obj)
        source_check = kwargs.get("source_check") or build_source_check(sources)
        kwargs["sources"] = sources
        kwargs["source_check"] = source_check
        upcoming = kwargs.get("upcoming") or UpcomingExpense.objects.for_user(profile.user_id)
        upcoming_names = list(upcoming.values_list("name", flat=True))
        upcoming_check = set(upcoming_names)
        upcoming_lower = {n.lower() for n in upcoming_names}
        existing_name = kwargs.get("existing_name")
        kwargs["upcoming"] = upcoming
        update = Updater(profile=profile, sources=sources)

        if isinstance(data, list):
            rejected = []
            accepted = []
            for item in data:
                try:
                    _validate_expense(
                        uid,
                        item,
                        profile,
                        upcoming_check,
                        patch,
                        existing_name=existing_name,
                        upcoming_lower=upcoming_lower,
                        source_check=source_check,
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
            uid,
            data,
            profile,
            upcoming_check,
            patch,
            existing_name=existing_name,
            upcoming_lower=upcoming_lower,
            source_check=source_check,
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
        upcoming_check = upcoming.filter(name__iexact=str(expense_name).strip()).first()
        if not upcoming_check:
            logger.error(f"Expense does not exist: {expense_name}")
            raise ValidationError("Expense does not exist")
        kwargs["patch"] = True
        kwargs["upcoming"] = upcoming
        kwargs["checked"] = upcoming_check
        kwargs["existing_name"] = upcoming_check.name
        return func(uid, expense_name, *args, **kwargs)

    return _wrapped


def _validate_expense(
    uid,
    data: dict,
    profile,
    upcoming_check,
    patch,
    existing_name=None,
    *,
    upcoming_lower=None,
    source_check=None,
):
    """Validate a single expense payload; mutates defaults for date fields."""
    logger.debug(f"Validating expense fields for {uid}")
    if upcoming_lower is None:
        upcoming_lower = {n.lower() for n in upcoming_check}
    if not patch:
        if data["name"].strip().lower() in upcoming_lower:
            logger.error("Expense already exists (name omitted from logs)")
            raise ValidationError("Expense already exists")
        if data.get("start_date") and not data.get("due_date"):
            data["due_date"] = data["start_date"]
        if not data.get("start_date") and data.get("due_date"):
            data["start_date"] = data["due_date"]
        if not data.get("start_date") and not data.get("due_date"):
            logger.error("Must have either a start date or due date (payload keys omitted from logs)")
            raise ValidationError("Must have either a start date or due date")
    else:
        if existing_name and str(existing_name).lower() not in upcoming_lower:
            logger.error("Expense does not exist (name omitted from logs)")
            raise ValidationError("Expense does not exist")
        new_name = data.get("name")
        if new_name is not None:
            nn = str(new_name).strip()
            en = str(existing_name).strip() if existing_name else ""
            if nn and nn.lower() != en.lower() and nn.lower() in upcoming_lower:
                logger.error("Expense already exists under new name (name omitted from logs)")
                raise ValidationError("Expense already exists")

    if data.get("currency"):
        _validate_currency(data["currency"])
    if data.get("end_date"):
        if data.get("due_date") and data["end_date"] < data["due_date"]:
            logger.error("End date cannot be before due date (values omitted from logs)")
            raise ValidationError("End date cannot be before due date")
        today = datetime.now(zoneinfo.ZoneInfo(profile.timezone)).date()
        end_date = data["end_date"]
        if isinstance(end_date, str):
            end_date = date.fromisoformat(end_date)
        if end_date < today:
            logger.error("End date cannot be in the past (value omitted from logs)")
            raise ValidationError("End date cannot be in the past")

    if data.get("bill_class") is not None:
        bill_class = str(data["bill_class"]).strip().lower()
        if bill_class not in _BILL_CLASSES:
            raise ValidationError("Invalid bill_class")
        data["bill_class"] = bill_class

    amount = data.get("amount")
    partial = data.get("planned_partial_amount")
    if partial is not None:
        partial_dec = Decimal(str(partial))
        if partial_dec <= 0:
            raise ValidationError("planned_partial_amount must be positive")
        if amount is not None and partial_dec > Decimal(str(amount)):
            raise ValidationError("planned_partial_amount cannot exceed bill amount")

    if "source" in data:
        src = data.get("source")
        if src is None or src == "":
            data["source"] = None
        elif source_check is not None and src not in source_check:
            logger.error("Source does not exist (rejected at validation; value omitted from logs)")
            raise ValidationError("Source does not exist")

    if "auto_deduct" in data and data["auto_deduct"] is not None:
        if not isinstance(data["auto_deduct"], bool):
            raise ValidationError("Invalid auto_deduct")

    return data

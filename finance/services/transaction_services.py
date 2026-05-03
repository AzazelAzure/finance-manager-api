"""Transaction service functions used by API views."""

import finance.logic.validators as validator
from finance.validators.tx_validators import TransactionIDValidator, TransactionValidator
from finance.logic.updaters import Updater
from finance.logic.fincalc import Calculator
from django.db import transaction
from django.db.models import Count, Sum
from loguru import logger
from rest_framework.exceptions import ValidationError
from finance.models import Transaction, UpcomingExpense, AppProfile, FinancialSnapshot, PaymentSource
import copy
from decimal import Decimal
from types import SimpleNamespace
from datetime import timedelta
from finance.api_tools.query_utils import apply_transaction_filters

# Kwargs injected by decorators (not query filters)
_GET_TX_IGNORE_KEYS = frozenset({"profile"})


def _query_param_bool(value):
    """Interpret query-string booleans; non-empty unknown strings are false."""
    if value is None:
        return False
    return str(value).lower() in ("1", "true", "yes", "on")


# Public Functions

@validator.UserValidator
def get_transactions(uid,**kwargs):
    """Return filtered transactions plus computed totals by transaction type."""

    logger.debug(f"Fetching transactions for {uid}")
    queryset = Transaction.objects.for_user(uid=uid)
    profile = kwargs.get('profile', AppProfile.objects.for_user(uid))
    fc = Calculator(profile)

    filter_kwargs = {k: v for k, v in kwargs.items() if k not in _GET_TX_IGNORE_KEYS}
    # Use shared filtering logic
    queryset = apply_transaction_filters(queryset, **filter_kwargs)

    # Default ordering
    queryset = queryset.order_by('-date', '-tx_id')

    # Compute all totals in a single grouped query to avoid repeated aggregates.
    # This keeps GET transactions requests within a small number of DB executions.
    grouped_totals = (
        queryset.values("tx_type", "currency")
        .annotate(total=Sum("amount"))
    )

    total_expenses = Decimal("0")
    total_income = Decimal("0")
    total_transfer_out = Decimal("0")
    total_transfer_in = Decimal("0")
    transfer_net = Decimal("0")

    for row in grouped_totals:
        item_currency = row["currency"]
        tx_type = row["tx_type"]
        converted = fc._calc_totals(item_currency, fc.base_currency, row["total"])

        if tx_type == "EXPENSE":
            total_expenses += Decimal(converted)
        elif tx_type == "INCOME":
            total_income += Decimal(converted)
        elif tx_type == "XFER_OUT":
            total_transfer_out += Decimal(converted)
        elif tx_type == "XFER_IN":
            total_transfer_in += Decimal(converted)

        # Net transfer flow: grouped Sum(amount) is signed (OUT negative, IN positive).
        if tx_type in {"XFER_OUT", "XFER_IN"}:
            transfer_net += Decimal(converted)

    # Category aggregation for the filtered queryset
    category_rows = (
        queryset.filter(tx_type__in=["EXPENSE", "XFER_OUT"])
        .values("category", "currency")
        .annotate(total=Sum("amount"))
    )
    cat_totals: dict[str, Decimal] = {}
    for row in category_rows:
        cat_name = str(row["category"] or "Uncategorized").strip()
        if not cat_name:
            cat_name = "Uncategorized"
        amount = Decimal(fc._calc_totals(row["currency"], fc.base_currency, row["total"]))
        cat_totals[cat_name] = cat_totals.get(cat_name, Decimal("0")) + abs(amount)

    quant = Decimal("0.01")
    expense_by_category = {
        k: v.quantize(quant) for k, v in sorted(cat_totals.items(), key=lambda item: item[1], reverse=True)
    }

    return {
        "transactions": queryset,
        "total_expenses": total_expenses.quantize(quant),
        "total_income": total_income.quantize(quant),
        "total_transfer_out": total_transfer_out.quantize(quant),
        "total_transfer_in": total_transfer_in.quantize(quant),
        "total_leaks": abs(transfer_net).quantize(quant),
        "expense_by_category": expense_by_category,
    }

@validator.UserValidator
@TransactionValidator
@transaction.atomic
def add_transaction(uid, data, *args, **kwargs):
    """Create one or more transactions and return accepted/rejected + snapshot."""
    upcoming = kwargs.get('upcoming', UpcomingExpense.objects.for_user(uid))
    sources = kwargs.get('sources')
    profile = kwargs.get('profile', AppProfile.objects.for_user(uid))
    if isinstance(data, list):
        logger.debug(f"Creating {len(data)} transactions for {uid}")
        rejected = kwargs.get('rejected', [])
        accepted = kwargs.get('accepted', [])
        to_update = Transaction.objects.bulk_create([Transaction(**item) for item in accepted])
        update = Updater(profile=profile, transactions=to_update, upcoming=upcoming, sources=sources)
        snapshot = update.transaction_handler()
        return {'accepted': to_update, 'rejected': rejected, 'snapshot': snapshot}
    else:
        logger.debug(f"Creating single transaction for {uid}")
        tx = [Transaction.objects.create(**data)]
        update = Updater(profile=profile, transactions=tx, upcoming=upcoming, sources=sources)
        snapshot = update.transaction_handler()
        return {'accepted': tx, 'snapshot': snapshot}

@validator.UserValidator
@TransactionIDValidator
@TransactionValidator
@transaction.atomic
def update_transaction(uid, tx_id: str, data: dict, *args, **kwargs):
    """Partially update a transaction and recompute dependent snapshot totals."""
    logger.debug(f"Updating transaction {tx_id} for {uid}")
    tx = kwargs.get("id_check")
    profile = kwargs.get("profile", AppProfile.objects.for_user(uid))
    if not data:
        raise ValidationError("No fields to update")

    # Capture pre-update values so we can detect whether balance-affecting fields
    # genuinely changed (tests often send a full transaction payload where only
    # one field differs, e.g. tags).
    old_values = {field: getattr(tx, field, None) for field in data.keys()}

    # _handle_tx_update must reverse the row **as it was before PATCH**; `tx` is mutated below.
    prior_for_reversal = SimpleNamespace(
        bill=tx.bill,
        source=tx.source,
        amount=tx.amount,
        currency=tx.currency,
        date=tx.date,
    )

    for field, value in data.items():
        setattr(tx, field, value)
    tx.save(update_fields=list(data.keys()))

    # Avoid expensive recalculation when the patch does not impact balances/snapshot totals.
    # Tags/description (and non-balance category changes) should not require recomputing sources/snapshot.
    balance_fields = {"amount", "source", "currency", "tx_type"}
    changed_fields = {k for k, v in data.items() if old_values.get(k) != v}
    needs_recalc = bool(balance_fields & changed_fields)

    # Date and bill matter only when the transaction is linked to a bill (due-date rollover logic).
    if not needs_recalc and "date" in changed_fields and getattr(tx, "bill", None):
        needs_recalc = True
    if not needs_recalc and "bill" in changed_fields:
        needs_recalc = True

    if not needs_recalc:
        tx.refresh_from_db()
        snapshot = FinancialSnapshot.objects.for_user(uid).first()
        return {"updated": [tx], "snapshot": snapshot}

    new_tx = copy.copy(tx)
    update = Updater(
        profile=profile,
        transactions=[new_tx],
        upcoming=kwargs.get("upcoming"),
        sources=kwargs.get("sources"),
    )
    snapshot = update.transaction_handler(update=prior_for_reversal)
    # Reload so the API returns persisted values (signed amounts, etc.).
    tx.refresh_from_db()
    return {"updated": [tx], "snapshot": snapshot}

@validator.UserValidator
@TransactionIDValidator
@transaction.atomic
def delete_transaction(uid, tx_id: str, *args, **kwargs):
    """Delete one transaction and return deleted payload plus refreshed snapshot."""
    logger.debug(f"Deleting transaction {tx_id} for {uid}")
    tx = kwargs.get('id_check')
    to_delete = copy.copy(tx)
    to_delete.amount = 0
    if to_delete.bill:
        to_delete.bill = None
    profile = kwargs.get('profile', AppProfile.objects.for_user(uid))
    update = Updater(
        profile=profile,
        transactions=[to_delete],
        upcoming=kwargs.get("upcoming"),
        sources=kwargs.get("sources"),
    )
    # Update balances to reverse changes (bills / upcoming) before row removal
    update.transaction_handler(update=tx)

    # Delete transaction
    tx.delete()
    # Snapshot and KPI fields must not still reference the removed row (e.g. transfers / monthly spend).
    fresh_sources = list(PaymentSource.objects.for_user(uid))
    snapshot = Updater(
        profile=profile,
        sources=fresh_sources,
        upcoming=kwargs.get("upcoming"),
    ).source_handler()
    return {f'deleted': tx, 'snapshot': snapshot}

@validator.UserValidator
@TransactionIDValidator
def get_transaction(uid, tx_id: str, *args, **kwargs):
    """Return a single transaction row and its amount."""
    logger.debug(f"Fetching transaction {tx_id} for {uid}")
    tx = kwargs.get('id_check', Transaction.objects.for_user(uid).get_tx(tx_id).first())
    return {'transaction': tx, 'amount': tx.amount}


@validator.UserValidator
def get_transaction_calendar(uid, *, start_date, end_date, **kwargs):
    """Return calendar aggregates (daily/weekly/monthly) and selected-day drill rows."""
    profile = kwargs.get("profile", AppProfile.objects.for_user(uid))
    fc = Calculator(profile)
    display_currency_mode = str(kwargs.get("display_currency_mode", "base")).lower()
    if display_currency_mode not in {"base", "original"}:
        raise ValidationError({"display_currency_mode": "Use 'base' or 'original'."})
    heat_metric_mode = str(kwargs.get("heat_metric_mode", "net")).lower()
    if heat_metric_mode not in {"net", "expense_only", "count"}:
        raise ValidationError({"heat_metric_mode": "Use 'net', 'expense_only', or 'count'."})

    queryset = (
        Transaction.objects.for_user(uid=uid)
        .filter(date__gte=start_date, date__lte=end_date)
        .order_by("date", "tx_id")
    )

    rows = list(queryset.values("date", "amount", "currency", "tx_type"))
    quant = Decimal("0.01")
    daily_map: dict = {}
    weekly_map: dict = {}
    monthly_map: dict = {}
    heat_values: dict = {}
    for row in rows:
        tx_date = row["date"]
        raw_amount = Decimal(str(row["amount"] or 0))
        amount_base = Decimal(
            str(fc._calc_totals(str(row["currency"] or fc.base_currency), fc.base_currency, raw_amount))
        ).quantize(quant)

        current_daily = daily_map.get(tx_date, {"amount": Decimal("0"), "tx_count": 0})
        current_daily["amount"] += amount_base
        current_daily["tx_count"] += 1
        daily_map[tx_date] = current_daily

        week_start = tx_date - timedelta(days=tx_date.weekday())
        weekly_map[week_start] = weekly_map.get(week_start, Decimal("0")) + amount_base

        month_start = tx_date.replace(day=1)
        monthly_map[month_start] = monthly_map.get(month_start, Decimal("0")) + amount_base

        metric = heat_values.get(tx_date, Decimal("0"))
        if heat_metric_mode == "count":
            metric += Decimal("1")
        elif heat_metric_mode == "expense_only":
            if str(row["tx_type"] or "").upper() in {"EXPENSE", "XFER_OUT"}:
                metric += abs(amount_base)
        else:
            metric += abs(amount_base)
        heat_values[tx_date] = metric

    heat_max = max(heat_values.values(), default=Decimal("0")).quantize(quant)

    daily = [
        {
            "date": d,
            "amount": values["amount"].quantize(quant),
            "tx_count": values["tx_count"],
            "heat_value": heat_values.get(d, Decimal("0")).quantize(quant),
            "heat_intensity": (
                int((heat_values.get(d, Decimal("0")) / heat_max) * 100)
                if heat_max > 0
                else 0
            ),
        }
        for d, values in sorted(daily_map.items())
    ]
    weekly = [
        {"period": period.isoformat(), "amount": amount.quantize(quant)}
        for period, amount in sorted(weekly_map.items())
    ]
    monthly = [
        {"period": period.isoformat(), "amount": amount.quantize(quant)}
        for period, amount in sorted(monthly_map.items())
    ]

    day_drill = queryset.filter(date=start_date).order_by("date", "tx_id")
    due_events_queryset = (
        UpcomingExpense.objects.for_user(uid)
        .filter(due_date__isnull=False, due_date__gte=start_date, due_date__lte=end_date)
        .order_by("due_date", "name")
    )
    due_events = [
        {
            "date": item.due_date,
            "expense_name": str(item.name or ""),
            "amount": Decimal(str(item.amount or 0)).quantize(quant),
            "amount_base": Decimal(
                str(fc._calc_totals(str(item.currency or fc.base_currency), fc.base_currency, item.amount))
            ).quantize(quant),
            "currency": str(item.currency or ""),
            "paid_flag": bool(item.paid_flag),
            "is_recurring": bool(item.is_recurring),
        }
        for item in due_events_queryset
    ]

    return {
        "start_date": start_date,
        "end_date": end_date,
        "base_currency": fc.base_currency,
        "display_currency_mode": display_currency_mode,
        "heat_metric_mode": heat_metric_mode,
        "heat_max": heat_max,
        "monthly": monthly,
        "weekly": weekly,
        "daily": daily,
        "due_events": due_events,
        "day_drill": day_drill,
    }


@validator.UserValidator
def get_transaction_visualization(uid, *, start_date, end_date, **kwargs):
    """Return chart-ready packets for transaction and upcoming-expense deep-dive views."""
    quant = Decimal("0.01")
    tx_queryset = (
        Transaction.objects.for_user(uid=uid)
        .filter(date__gte=start_date, date__lte=end_date)
        .order_by("date", "tx_id")
    )
    tx_rows = list(tx_queryset.values("date", "tx_type", "amount", "category"))

    daily_map: dict = {}
    type_totals = {
        "EXPENSE": Decimal("0"),
        "INCOME": Decimal("0"),
        "XFER_OUT": Decimal("0"),
        "XFER_IN": Decimal("0"),
    }
    expense_categories: dict[str, Decimal] = {}
    for row in tx_rows:
        tx_date = row["date"]
        tx_type = str(row["tx_type"] or "")
        amount = Decimal(str(row["amount"] or 0))
        abs_amount = abs(amount)

        day_bucket = daily_map.get(
            tx_date,
            {"income": Decimal("0"), "expense": Decimal("0"), "net": Decimal("0"), "tx_count": 0},
        )
        if tx_type in {"INCOME", "XFER_IN"}:
            day_bucket["income"] += abs_amount
        else:
            day_bucket["expense"] += abs_amount
        day_bucket["net"] = day_bucket["income"] - day_bucket["expense"]
        day_bucket["tx_count"] += 1
        daily_map[tx_date] = day_bucket

        if tx_type in type_totals:
            type_totals[tx_type] += abs_amount

        if tx_type == "EXPENSE":
            category_name = str(row["category"] or "Uncategorized").strip() or "Uncategorized"
            expense_categories[category_name] = expense_categories.get(category_name, Decimal("0")) + abs_amount

    flow_daily = [
        {
            "date": d,
            "income": values["income"].quantize(quant),
            "expense": values["expense"].quantize(quant),
            "net": values["net"].quantize(quant),
            "tx_count": values["tx_count"],
        }
        for d, values in sorted(daily_map.items())
    ]
    tx_type_totals = [
        {"tx_type": key, "amount": value.quantize(quant)}
        for key, value in type_totals.items()
        if value > 0
    ]
    top_expense_categories = [
        {"category": category, "amount": amount.quantize(quant)}
        for category, amount in sorted(expense_categories.items(), key=lambda item: item[1], reverse=True)[:8]
    ]

    upcoming_queryset = (
        UpcomingExpense.objects.for_user(uid)
        .filter(due_date__isnull=False, due_date__gte=start_date, due_date__lte=end_date)
        .order_by("due_date", "name")
    )
    upcoming_rows = list(
        upcoming_queryset.values("due_date", "name", "amount", "currency", "paid_flag")
    )

    upcoming_monthly_map: dict = {}
    paid_count = 0
    unpaid_count = 0
    paid_amount = Decimal("0")
    unpaid_amount = Decimal("0")
    timeline = []
    for row in upcoming_rows:
        due_date = row["due_date"]
        amount = Decimal(str(row["amount"] or 0))
        timeline.append(
            {
                "due_date": due_date,
                "name": str(row["name"] or ""),
                "amount": amount.quantize(quant),
                "currency": str(row["currency"] or ""),
                "paid_flag": bool(row["paid_flag"]),
            }
        )
        month_start = due_date.replace(day=1)
        bucket = upcoming_monthly_map.get(month_start, {"amount": Decimal("0"), "expense_count": 0})
        bucket["amount"] += amount
        bucket["expense_count"] += 1
        upcoming_monthly_map[month_start] = bucket

        if row["paid_flag"]:
            paid_count += 1
            paid_amount += amount
        else:
            unpaid_count += 1
            unpaid_amount += amount

    upcoming_expenses_monthly = [
        {
            "period": period.isoformat(),
            "amount": values["amount"].quantize(quant),
            "expense_count": values["expense_count"],
        }
        for period, values in sorted(upcoming_monthly_map.items())
    ]

    return {
        "start_date": start_date,
        "end_date": end_date,
        "flow_daily": flow_daily,
        "tx_type_totals": tx_type_totals,
        "top_expense_categories": top_expense_categories,
        "upcoming_expenses_timeline": timeline,
        "upcoming_expenses_monthly": upcoming_expenses_monthly,
        "upcoming_expenses_status": {
            "paid_count": paid_count,
            "unpaid_count": unpaid_count,
            "paid_amount": paid_amount.quantize(quant),
            "unpaid_amount": unpaid_amount.quantize(quant),
        },
    }

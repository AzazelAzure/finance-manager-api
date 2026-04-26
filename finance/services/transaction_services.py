"""Transaction service functions used by API views."""

import finance.logic.validators as validator
from finance.validators.tx_validators import TransactionIDValidator, TransactionValidator
from finance.logic.updaters import Updater
from finance.logic.fincalc import Calculator
from django.db import transaction
from django.db.models import Sum
from loguru import logger
from rest_framework.exceptions import ValidationError
from finance.models import Transaction, UpcomingExpense, AppProfile, FinancialSnapshot
import copy
from decimal import Decimal
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
    snapshot = update.transaction_handler(update=tx)
    # _handle_tx_update mutates the passed-in instance's amount in memory for balance math;
    # reload so the API returns persisted values (signed amounts, etc.).
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
    # Update balances to reverse changes
    snapshot = update.transaction_handler(update=tx)

    # Delete transaction
    tx.delete()
    return {f'deleted': tx, 'snapshot': snapshot}

@validator.UserValidator
@TransactionIDValidator
def get_transaction(uid, tx_id: str, *args, **kwargs):
    """Return a single transaction row and its amount."""
    logger.debug(f"Fetching transaction {tx_id} for {uid}")
    tx = kwargs.get('id_check', Transaction.objects.for_user(uid).get_tx(tx_id).first())
    return {'transaction': tx, 'amount': tx.amount}

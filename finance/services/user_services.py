"""
This module handles all user-related functionality for the finance manager application.

Attributes:
    user_update_spend_accounts: Updates the spend accounts for a user.
    user_get_spend_accounts: Retrieves the spend accounts for a user.
    user_update_base_currency: Updates the base currency for a user.
    user_get_base_currency: Retrieves the base currency for a user.
    user_get_totals: Retrieves the totals for a user.
"""
# TODO: Update logging


import finance.logic.validators as validator
from finance.logic.updaters import Updater
from finance.logic.fincalc import Calculator
from finance.api_tools.query_utils import apply_transaction_filters
from django.db import transaction
from django.conf import settings
from django.db.models import Sum
from decimal import Decimal
from loguru import logger
from finance.models import (
    Transaction,
    AppProfile,
    FinancialSnapshot,
    PaymentSource,
)

@transaction.atomic
@validator.UserValidator
def user_update(uid: str, data: dict, *args, **kwargs):
    """
    Updates the spend accounts for a user.
    Raises a ValidationError if any of the sources do not exist.
    
    Merge rule for lists (e.g. `completed_tours`, `spend_accounts`):
    - Replaces the existing array with the provided array. Unioning must be handled by the client.
    
    :param uid: The user id.
    :type uid: str
    :param data: The data for the spend accounts.
    :type data: list
    :returns: {'spend_accounts': [list], 'message': "Spend accounts updated successfully"}
    :rtype: dict
    """
    logger.debug(f'Updating {uid}')
    profile = kwargs.get('profile')
    sources = kwargs.get('sources') or list(PaymentSource.objects.for_user(uid))
    if data.get('spend_accounts'):
        if isinstance(data['spend_accounts'], list):
            data['spend_accounts'] = [item.lower() for item in data['spend_accounts']]
            profile.spend_accounts = data['spend_accounts']
        else:
            profile.spend_accounts = [str(data['spend_accounts']).lower()]
    if data.get('base_currency'):
        profile.base_currency = data['base_currency'].upper()
    if data.get("timezone") is not None:
        # IANA IDs are case-sensitive (e.g. Asia/Manila); never apply .upper() like currency codes.
        profile.timezone = str(data["timezone"]).strip()
    if data.get('start_week') is not None:
        profile.start_of_week = data['start_week']
    if data.get('completed_tours') is not None:
        if isinstance(data['completed_tours'], list):
            profile.completed_tours = data['completed_tours']
    profile.save()
    update = Updater(profile=profile, sources=sources)
    snapshot = update.user_handler()
    return {'message': "User updated successfully", 'snapshot': snapshot}

        
@validator.UserValidator
def user_get_info(uid: str, *args, **kwargs):
    """
    Retrieves the spend accounts and base currency for a user.
    
    :param uid: The user id.
    :type uid: str
    :returns: {'spend_accounts': list, 'base_currency': str}
    :rtype: dict
    """
    logger.debug(f"Getting spend accounts and base currency for {uid}")
    profile = kwargs.get('profile')
    spend_accounts = profile.spend_accounts
    base_currency = profile.base_currency
    timezone = profile.timezone
    start_week = profile.start_of_week
    completed_tours = profile.completed_tours
    return {
        'spend_accounts': spend_accounts, 
        'base_currency': base_currency,
        'timezone': timezone,
        'start_of_week': start_week,
        'completed_tours': completed_tours,
        'feature_requests_enabled': getattr(settings, "BETA_FEATURE_REQUESTS_ENABLED", False),
        }


# Data Getterss
@validator.UserValidator
def user_get_totals(uid, *args, **kwargs):
    """
    Retrieves the totals for a user.  Acts as a basic dashboard retrieval for relevant data.
    
    :param uid: The user id.
    :type uid: str
    :returns: {'Snapshot': queryset, 'transactions for month': queryset, 'total expenses for month': decimal, 'total income for month': decimal, 'total transfer out for month': decimal, 'total transfer in for month': decimal}
    :rtype: dict
    """
    logger.debug(f"Getting all totals for {uid}")
    
    # Apply standard transaction filters to support dynamic dashboard charts
    queryset = Transaction.objects.for_user(uid)
    queryset = apply_transaction_filters(queryset, **kwargs)
    queryset = queryset.order_by('-date', '-tx_id')
    fc = Calculator(profile=kwargs.get('profile'))
    transfer_out_month = fc.calc_queryset(queryset.get_by_tx_type('XFER_OUT'))
    transfer_in_month = fc.calc_queryset(queryset.get_by_tx_type('XFER_IN'))
    leaks_for_month = abs(Decimal(transfer_out_month) + Decimal(transfer_in_month)).quantize(Decimal("0.01"))
    snapshot = FinancialSnapshot.objects.for_user(uid).first()
    if snapshot is not None:
        # Keep snapshot payload aligned with dashboard month rollups.
        snapshot.total_leaks = leaks_for_month
    flow_rows = (
        queryset.values("date", "tx_type", "currency")
        .annotate(total=Sum("amount"))
        .order_by("date")
    )
    by_day: dict[str, dict[str, Decimal]] = {}
    for row in flow_rows:
        day_key = str(row["date"])
        bucket = by_day.setdefault(
            day_key,
            {"incoming": Decimal("0.00"), "outgoing": Decimal("0.00"), "leaks": Decimal("0.00")},
        )
        amount = Decimal(fc._calc_totals(row["currency"], fc.base_currency, row["total"]))
        tx_type = row["tx_type"]
        if tx_type == "INCOME":
            bucket["incoming"] += abs(amount)
        elif tx_type == "EXPENSE":
            bucket["outgoing"] += abs(amount)
        elif tx_type in ("XFER_OUT", "XFER_IN"):
            bucket["leaks"] += amount
    flow_series = [
        {
            "label": day,
            "incoming": values["incoming"].quantize(Decimal("0.01")),
            "outgoing": values["outgoing"].quantize(Decimal("0.01")),
            "leaks": abs(values["leaks"]).quantize(Decimal("0.01")),
        }
        for day, values in sorted(by_day.items())
    ]
    
    # Category Breakdown
    category_rows = (
        queryset.filter(tx_type='EXPENSE')
        .values("category", "currency")
        .annotate(total=Sum("amount"))
    )
    cat_totals: dict[str, Decimal] = {}
    for row in category_rows:
        cat_name = str(row["category"] or "Uncategorized").strip()
        if not cat_name:
            cat_name = "Uncategorized"
        amount = Decimal(fc._calc_totals(row["currency"], fc.base_currency, row["total"]))
        
        if cat_name in cat_totals:
            cat_totals[cat_name] += abs(amount)
        else:
            cat_totals[cat_name] = abs(amount)
            
    # Format for Recharts: list of {"name": "Category", "value": 100.00}
    expense_by_category = [
        {"name": k, "value": float(v.quantize(Decimal("0.01")))} 
        for k, v in sorted(cat_totals.items(), key=lambda item: item[1], reverse=True)
    ]

    daily_spend = [{"date": p["label"], "amount": p["outgoing"]} for p in flow_series if p["outgoing"] > 0]
    daily_income = [{"date": p["label"], "amount": p["incoming"]} for p in flow_series if p["incoming"] > 0]

    # Source Balances (Live account status)
    sources = PaymentSource.objects.for_user(uid)
    source_balances = [
        {
            "source": s.source,
            "acc_type": s.acc_type,
            "amount": str(s.amount.quantize(Decimal("0.01"))),
            "currency": s.currency
        }
        for s in sources
    ]

    return {
        'snapshot': snapshot,
        'transactions_for_month': queryset,
        'flow_series': flow_series,
        'expense_by_category': expense_by_category,
        'source_balances': source_balances,
        'daily_spend': daily_spend,
        'daily_income': daily_income,
        'total_expenses_for_month': fc.calc_queryset(queryset.get_by_tx_type('EXPENSE')),
        'total_income_for_month': fc.calc_queryset(queryset.get_by_tx_type('INCOME')),
        'total_transfer_out_for_month': transfer_out_month,
        'total_transfer_in_for_month': transfer_in_month,
        'total_leaks_for_month': leaks_for_month,
    }



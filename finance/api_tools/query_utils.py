"""Shared query filtering logic for transactions."""

from django.utils import timezone
from dateutil.relativedelta import relativedelta

def _query_param_bool(value):
    """Interpret query-string booleans; non-empty unknown strings are false."""
    if value is None:
        return False
    return str(value).lower() in ("1", "true", "yes", "on")

def _safe_int(value):
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

def apply_transaction_filters(queryset, **kwargs):
    """Apply standard transaction filters to a queryset."""
    
    # Mapping of query parameter names to manager method names
    SINGLE_ARG_FILTER_MAP = {
        'tx_type': 'get_by_tx_type',
        'tag_name': 'get_by_tag_name',
        'category': 'get_by_category',
        'source': 'get_by_source',
        'currency_code': 'get_by_currency',
        'by_year': 'get_by_year',
        'by_date': 'get_by_date',
        'date': 'get_by_date',
        'gte': 'get_gte',
        'lte': 'get_lte',
    }

    filter_keys = (
        'tx_type', 'tag_name', 'category', 'source', 'currency_code',
        'gte', 'lte', 'date', 'by_date', 'by_year',
    )

    # Handle period-based filters first
    if _query_param_bool(kwargs.get("current_month")):
        queryset = queryset.get_current_month()
    elif _query_param_bool(kwargs.get("last_month")):
        queryset = queryset.get_last_month()
    elif _query_param_bool(kwargs.get("previous_week")):
        queryset = queryset.get_previous_week()
    elif kwargs.get('start_date') and kwargs.get('end_date'):
        queryset = queryset.get_by_period(kwargs['start_date'], kwargs['end_date'])
    elif kwargs.get('month') and kwargs.get('year'):
        queryset = queryset.get_by_month(_safe_int(kwargs['month']), _safe_int(kwargs['year']))
    elif kwargs.get('start_date'):
        queryset = queryset.get_all_after(kwargs['start_date'])
    elif kwargs.get('end_date'):
        queryset = queryset.get_all_before(kwargs['end_date'])
    elif kwargs.get('month'):
        queryset = queryset.get_current_month()
    elif kwargs.get('year'):
        queryset = queryset.get_by_year(_safe_int(kwargs['year']))
    elif not any(k in kwargs for k in filter_keys):
        queryset = queryset.get_latest()

    # Dynamically apply other single-argument filters
    for param_name, manager_method_name in SINGLE_ARG_FILTER_MAP.items():
        val = kwargs.get(param_name)
        if val is not None and val != "":
            method = getattr(queryset, manager_method_name)
            queryset = method(val)

    return queryset

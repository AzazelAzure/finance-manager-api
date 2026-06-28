"""Bill due-date interval helpers (T02 stopgap — see strategy/anomalies bill-interval-cycle-revamp)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

from dateutil.relativedelta import relativedelta

if TYPE_CHECKING:
    from finance.models import UpcomingExpense

MAX_CATCH_UP_PERIODS = 24


def bill_interval_timedelta(bill: UpcomingExpense) -> relativedelta | timedelta:
    """Interval between bill periods.

    Uses days between ``start_date`` and ``due_date`` when positive; otherwise
    falls back to one calendar month (legacy monthly formatting).
    """
    if bill.start_date and bill.due_date:
        days = (bill.due_date - bill.start_date).days
        if days > 0:
            return timedelta(days=days)
    return relativedelta(months=1)


def add_interval_to_date(due: date, bill: UpcomingExpense, periods: int = 1) -> date:
    step = bill_interval_timedelta(bill)
    result = due
    for _ in range(max(periods, 0)):
        if isinstance(step, relativedelta):
            result = result + step
        else:
            result = result + step
    return result


def periods_behind(bill: UpcomingExpense, today: date, max_periods: int = MAX_CATCH_UP_PERIODS) -> int:
    """How many interval steps are needed so ``due_date`` reaches or passes ``today``."""
    if not bill.due_date or bill.due_date >= today:
        return 0
    periods = 0
    due = bill.due_date
    while due < today and periods < max_periods:
        due = add_interval_to_date(due, bill, 1)
        periods += 1
    return periods


def advance_bill_due_date(bill: UpcomingExpense, periods: int = 1) -> None:
    if not bill.due_date:
        return
    bill.due_date = add_interval_to_date(bill.due_date, bill, periods)

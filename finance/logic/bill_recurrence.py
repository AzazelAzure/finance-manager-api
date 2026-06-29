"""Bill due-date interval helpers driven by explicit UpcomingExpense.cadence."""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

from dateutil.relativedelta import relativedelta

if TYPE_CHECKING:
    from finance.models import UpcomingExpense

MAX_CATCH_UP_PERIODS = 24

_SEMIMONTHLY_ANCHORS = (1, 15)


def bill_interval_step(bill: UpcomingExpense) -> relativedelta | timedelta:
    """Return the interval step for a bill's cadence (semimonthly handled separately)."""
    c = bill.cadence
    if c == "weekly":
        return timedelta(days=7)
    if c == "biweekly":
        return timedelta(days=14)
    if c == "monthly":
        return relativedelta(months=1)
    if c == "quarterly":
        return relativedelta(months=3)
    if c == "annual":
        return relativedelta(years=1)
    if c == "custom":
        return timedelta(days=bill.custom_interval_days or 30)
    if c == "semimonthly":
        raise ValueError("semimonthly uses _advance_semimonthly, not a fixed step")
    raise ValueError(f"unknown cadence {c!r}")


def _first_of_next_month(due: date) -> date:
    if due.month == 12:
        return date(due.year + 1, 1, 1)
    return date(due.year, due.month + 1, 1)


def _advance_semimonthly(due: date) -> date:
    """Advance to the next half-month anchor (1st and 15th).

    Bills on anchors alternate 1 ↔ 15 within the month pair, then 15 → 1st of
    next month. Non-anchor days snap forward to the nearer upcoming anchor in
    that rhythm (never backward): below the 15th → the 15th; on/after the
    16th → the 1st of the next month.
    """
    day = due.day
    if day == _SEMIMONTHLY_ANCHORS[0]:
        return date(due.year, due.month, _SEMIMONTHLY_ANCHORS[1])
    if day == _SEMIMONTHLY_ANCHORS[1]:
        return _first_of_next_month(due)
    if day < _SEMIMONTHLY_ANCHORS[1]:
        return date(due.year, due.month, _SEMIMONTHLY_ANCHORS[1])
    return _first_of_next_month(due)


def _advance_one_period(due: date, bill: UpcomingExpense) -> date:
    if bill.cadence == "semimonthly":
        return _advance_semimonthly(due)
    step = bill_interval_step(bill)
    return due + step


def add_interval_to_date(due: date, bill: UpcomingExpense, periods: int = 1) -> date:
    result = due
    for _ in range(max(periods, 0)):
        result = _advance_one_period(result, bill)
    return result


def periods_behind(bill: UpcomingExpense, today: date, max_periods: int = MAX_CATCH_UP_PERIODS) -> int:
    """How many interval steps are needed so ``due_date`` reaches or passes ``today``."""
    if not bill.due_date or bill.due_date >= today:
        return 0
    periods = 0
    due = bill.due_date
    while due < today and periods < max_periods:
        due = _advance_one_period(due, bill)
        periods += 1
    return periods


def advance_bill_due_date(bill: UpcomingExpense, periods: int = 1) -> None:
    if not bill.due_date:
        return
    bill.due_date = add_interval_to_date(bill.due_date, bill, periods)

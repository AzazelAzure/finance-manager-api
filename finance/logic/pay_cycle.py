"""Pay-cycle window helpers for safe-to-spend calculations."""

from __future__ import annotations

from datetime import date, timedelta

from dateutil.relativedelta import relativedelta


def current_pay_cycle_window(profile, today: date | None = None) -> tuple[date, date]:
    """Return the pay-cycle window ``[start, end)`` containing ``today``.

    ``pay_cycle_anchor_date`` is treated as a payday boundary. For example, a
    biweekly anchor of July 15 means the window immediately before that payday
    starts July 1 and ends July 15.
    """
    anchor = profile.pay_cycle_anchor_date
    frequency = profile.pay_cycle_frequency
    if anchor is None or not frequency:
        raise ValueError("pay_cycle_anchor_date and pay_cycle_frequency are required")

    today = today or date.today()
    step = _cycle_step(frequency)
    start = anchor
    end = _add_step(start, step)

    while today < start:
        end = start
        start = _subtract_step(start, step)

    while today >= end:
        start = end
        end = _add_step(end, step)

    return start, end


def _cycle_step(frequency: str) -> relativedelta | timedelta:
    if frequency == "weekly":
        return timedelta(days=7)
    if frequency == "biweekly":
        return timedelta(days=14)
    if frequency == "semimonthly":
        # V1 uses a 15-day cadence; richer 1st/15th anchoring is deferred.
        return timedelta(days=15)
    if frequency == "monthly":
        return relativedelta(months=1)
    raise ValueError(f"Unsupported pay_cycle_frequency: {frequency}")


def _add_step(value: date, step: relativedelta | timedelta) -> date:
    return value + step


def _subtract_step(value: date, step: relativedelta | timedelta) -> date:
    return value - step

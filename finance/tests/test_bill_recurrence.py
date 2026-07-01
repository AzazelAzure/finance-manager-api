"""Unit tests for cadence-driven bill recurrence."""

from datetime import date
from types import SimpleNamespace

import pytest

from finance.logic.bill_recurrence import (
    MAX_CATCH_UP_PERIODS,
    add_interval_to_date,
    advance_bill_due_date,
    periods_behind,
    retreat_bill_due_date,
    subtract_interval_from_date,
)


def _bill(cadence: str, due_date: date, custom_interval_days: int | None = None):
    return SimpleNamespace(
        cadence=cadence,
        due_date=due_date,
        custom_interval_days=custom_interval_days,
    )


class TestFixedDayCadences:
    @pytest.mark.parametrize(
        ("cadence", "start", "expected"),
        [
            ("weekly", date(2026, 1, 1), date(2026, 1, 8)),
            ("biweekly", date(2026, 1, 1), date(2026, 1, 15)),
        ],
    )
    def test_single_advance(self, cadence, start, expected):
        bill = _bill(cadence, start)
        assert add_interval_to_date(start, bill, 1) == expected

    def test_custom_interval(self):
        bill = _bill("custom", date(2026, 3, 1), custom_interval_days=10)
        assert add_interval_to_date(date(2026, 3, 1), bill, 1) == date(2026, 3, 11)

    def test_custom_missing_interval_defaults_to_30(self):
        bill = _bill("custom", date(2026, 3, 1), custom_interval_days=None)
        assert add_interval_to_date(date(2026, 3, 1), bill, 1) == date(2026, 3, 31)


class TestCalendarCadences:
    def test_monthly_jan_31_to_feb(self):
        bill = _bill("monthly", date(2026, 1, 31))
        assert add_interval_to_date(date(2026, 1, 31), bill, 1) == date(2026, 2, 28)

    def test_monthly_leap_year(self):
        bill = _bill("monthly", date(2024, 1, 31))
        assert add_interval_to_date(date(2024, 1, 31), bill, 1) == date(2024, 2, 29)

    def test_quarterly(self):
        bill = _bill("quarterly", date(2026, 1, 15))
        assert add_interval_to_date(date(2026, 1, 15), bill, 1) == date(2026, 4, 15)

    def test_annual(self):
        bill = _bill("annual", date(2024, 2, 29))
        assert add_interval_to_date(date(2024, 2, 29), bill, 1) == date(2025, 2, 28)


class TestSemimonthly:
    def test_anchor_1_to_15(self):
        bill = _bill("semimonthly", date(2026, 6, 1))
        assert add_interval_to_date(date(2026, 6, 1), bill, 1) == date(2026, 6, 15)

    def test_anchor_15_to_next_month_1(self):
        bill = _bill("semimonthly", date(2026, 6, 15))
        assert add_interval_to_date(date(2026, 6, 15), bill, 1) == date(2026, 7, 1)

    def test_non_anchor_day_3_snaps_forward_to_15(self):
        bill = _bill("semimonthly", date(2026, 6, 3))
        assert add_interval_to_date(date(2026, 6, 3), bill, 1) == date(2026, 6, 15)

    def test_non_anchor_day_20_goes_to_next_month_1(self):
        bill = _bill("semimonthly", date(2026, 6, 20))
        assert add_interval_to_date(date(2026, 6, 20), bill, 1) == date(2026, 7, 1)

    def test_alternation_over_two_periods(self):
        bill = _bill("semimonthly", date(2026, 6, 15))
        assert add_interval_to_date(date(2026, 6, 15), bill, 2) == date(2026, 7, 15)

    def test_december_15_rolls_to_january_1(self):
        bill = _bill("semimonthly", date(2026, 12, 15))
        assert add_interval_to_date(date(2026, 12, 15), bill, 1) == date(2027, 1, 1)


class TestCatchUpAndAdvance:
    def test_periods_behind_weekly(self):
        bill = _bill("weekly", date(2026, 1, 1))
        bill.due_date = date(2026, 1, 1)
        assert periods_behind(bill, date(2026, 1, 22)) == 3

    def test_periods_behind_respects_cap(self):
        bill = _bill("weekly", date(2020, 1, 1))
        bill.due_date = date(2020, 1, 1)
        assert periods_behind(bill, date(2026, 1, 1), max_periods=5) == 5

    def test_periods_behind_zero_when_current(self):
        bill = _bill("monthly", date(2026, 6, 15))
        bill.due_date = date(2026, 6, 15)
        assert periods_behind(bill, date(2026, 6, 10)) == 0

    def test_advance_bill_due_date_mutates(self):
        bill = _bill("weekly", date(2026, 6, 1))
        advance_bill_due_date(bill, periods=2)
        assert bill.due_date == date(2026, 6, 15)

    def test_retreat_mirrors_advance_weekly(self):
        bill = _bill("weekly", date(2026, 6, 8))
        assert subtract_interval_from_date(date(2026, 6, 8), bill, 1) == date(2026, 6, 1)

    def test_retreat_bill_due_date_mutates(self):
        bill = _bill("weekly", date(2026, 6, 15))
        retreat_bill_due_date(bill, periods=2)
        assert bill.due_date == date(2026, 6, 1)

    def test_max_catch_up_constant(self):
        assert MAX_CATCH_UP_PERIODS == 24

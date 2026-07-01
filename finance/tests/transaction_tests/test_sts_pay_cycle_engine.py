from datetime import date, datetime, timedelta
from decimal import Decimal

import zoneinfo
from rest_framework import status

from finance.logic.pay_cycle import current_pay_cycle_window
from finance.models import AppProfile, UpcomingExpense
from finance.tests.transaction_tests.transaction_base import TransactionBase


class PayCycleWindowHelperTests(TransactionBase):
    def test_biweekly_window_uses_anchor_as_payday_boundary(self):
        self.profile.pay_cycle_frequency = AppProfile.PayCycleFrequency.BIWEEKLY
        self.profile.pay_cycle_anchor_date = date(2026, 7, 15)

        cases = [
            (date(2026, 7, 10), date(2026, 7, 1), date(2026, 7, 15)),
            (date(2026, 7, 15), date(2026, 7, 15), date(2026, 7, 29)),
            (date(2026, 7, 30), date(2026, 7, 29), date(2026, 8, 12)),
        ]
        for today, expected_start, expected_end in cases:
            with self.subTest(today=today):
                self.assertEqual(
                    current_pay_cycle_window(self.profile, today=today),
                    (expected_start, expected_end),
                )


class StsPayCycleEngineTests(TransactionBase):
    def _prepare_spend_and_trigger_sources(self):
        spend_source = self.sources[0]
        non_spend_source = self.sources[1]
        self.profile.spend_accounts = [spend_source.source_id]
        self.profile.save(update_fields=["spend_accounts"])
        spend_source.amount = Decimal("1000.00")
        spend_source.currency = str(self.profile.base_currency).upper()
        spend_source.save(update_fields=["amount", "currency"])
        non_spend_source.currency = str(self.profile.base_currency).upper()
        non_spend_source.save(update_fields=["currency"])
        return spend_source, non_spend_source

    def _post_snapshot_trigger(self, source):
        payload = self.expense_data.copy()
        payload["date"] = str(datetime.now(zoneinfo.ZoneInfo(self.profile.timezone)).date())
        payload["source"] = source.source
        payload["currency"] = str(self.profile.base_currency).upper()
        payload["amount"] = "10.00"
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, msg=response.data)
        return response.data["snapshot"]

    def test_pay_cycle_mode_counts_bills_due_in_current_pay_window(self):
        _, non_spend_source = self._prepare_spend_and_trigger_sources()
        today = datetime.now(zoneinfo.ZoneInfo(self.profile.timezone)).date()
        self.profile.sts_window_mode = AppProfile.StsWindowMode.PAY_CYCLE
        self.profile.pay_cycle_frequency = AppProfile.PayCycleFrequency.BIWEEKLY
        self.profile.pay_cycle_anchor_date = today + timedelta(days=3)
        self.profile.save(
            update_fields=["sts_window_mode", "pay_cycle_frequency", "pay_cycle_anchor_date"]
        )
        uid = str(self.profile.user_id)

        UpcomingExpense.objects.create(
            uid=uid,
            name="electric-partial",
            amount=Decimal("200.00"),
            planned_partial_amount=Decimal("120.00"),
            due_date=today + timedelta(days=1),
            paid_flag=False,
            currency=str(self.profile.base_currency).upper(),
        )
        UpcomingExpense.objects.create(
            uid=uid,
            name="outside-window",
            amount=Decimal("300.00"),
            due_date=today + timedelta(days=4),
            paid_flag=False,
            currency=str(self.profile.base_currency).upper(),
        )

        snap = self._post_snapshot_trigger(non_spend_source)
        self.assertEqual(Decimal(str(snap["total_remaining_expenses"])), Decimal("120.00"))
        self.assertEqual(Decimal(str(snap["safe_to_spend"])), Decimal("880.00"))

    def test_calendar_month_mode_keeps_legacy_current_month_window(self):
        _, non_spend_source = self._prepare_spend_and_trigger_sources()
        today = datetime.now(zoneinfo.ZoneInfo(self.profile.timezone)).date()
        next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
        uid = str(self.profile.user_id)

        UpcomingExpense.objects.create(
            uid=uid,
            name="this-month-bill",
            amount=Decimal("100.00"),
            due_date=today,
            paid_flag=False,
            currency=str(self.profile.base_currency).upper(),
        )
        UpcomingExpense.objects.create(
            uid=uid,
            name="next-month-bill",
            amount=Decimal("300.00"),
            due_date=next_month,
            paid_flag=False,
            currency=str(self.profile.base_currency).upper(),
        )

        snap = self._post_snapshot_trigger(non_spend_source)
        self.assertEqual(Decimal(str(snap["total_remaining_expenses"])), Decimal("100.00"))
        self.assertEqual(Decimal(str(snap["safe_to_spend"])), Decimal("900.00"))

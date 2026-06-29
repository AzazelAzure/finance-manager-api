from datetime import date, timedelta

from django.urls import reverse
from rest_framework import status

from finance.models import UpcomingExpense
from finance.tests.expense_tests.expense_base import ExpenseBase


class ExpenseCadenceApiTests(ExpenseBase):
    def test_create_without_cadence_defaults_monthly(self):
        payload = dict(self.expense_payload)
        payload["name"] = "no-cadence-bill"
        response = self.create_expense(payload)
        accepted = response.data["accepted"][0]
        self.assertEqual(accepted.get("cadence", "monthly"), "monthly")

        row = UpcomingExpense.objects.for_user(self.profile.user_id).get(name="no-cadence-bill")
        self.assertEqual(row.cadence, "monthly")

    def test_get_includes_cadence_fields(self):
        payload = dict(self.expense_payload)
        payload["name"] = "cadence-get-bill"
        payload["cadence"] = "biweekly"
        self.create_expense(payload)

        response = self.client.get(self.detail_url("cadence-get-bill"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expense = response.data["expense"]
        self.assertEqual(expense["cadence"], "biweekly")
        self.assertIsNone(expense["custom_interval_days"])

    def test_custom_cadence_requires_positive_interval(self):
        payload = dict(self.expense_payload)
        payload["name"] = "bad-custom"
        payload["cadence"] = "custom"
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_custom_cadence_accepts_interval_days(self):
        payload = dict(self.expense_payload)
        payload["name"] = "good-custom"
        payload["cadence"] = "custom"
        payload["custom_interval_days"] = 10
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, msg=response.data)
        row = UpcomingExpense.objects.for_user(self.profile.user_id).get(name="good-custom")
        self.assertEqual(row.cadence, "custom")
        self.assertEqual(row.custom_interval_days, 10)

    def test_patch_non_custom_clears_custom_interval_days(self):
        payload = dict(self.expense_payload)
        payload["name"] = "clear-custom-days"
        payload["cadence"] = "custom"
        payload["custom_interval_days"] = 21
        self.create_expense(payload)

        response = self.client.patch(
            self.detail_url("clear-custom-days"),
            {"cadence": "monthly"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.data)
        row = UpcomingExpense.objects.for_user(self.profile.user_id).get(name="clear-custom-days")
        self.assertEqual(row.cadence, "monthly")
        self.assertIsNone(row.custom_interval_days)

    def test_weekly_bill_advances_seven_days_on_settlement(self):
        due = date(2026, 6, 1)
        payload = {
            "name": "weekly-gym",
            "amount": "50.00",
            "currency": self.profile.base_currency,
            "due_date": str(due),
            "start_date": str(due),
            "is_recurring": True,
            "cadence": "weekly",
        }
        self.create_expense(payload)
        self.create_linked_expense_transaction("weekly-gym")

        row = UpcomingExpense.objects.for_user(self.profile.user_id).get(name="weekly-gym")
        self.assertEqual(row.due_date, due + timedelta(days=7))
        self.assertFalse(row.paid_flag)

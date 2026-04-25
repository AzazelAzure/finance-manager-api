import calendar
from datetime import date

from django.utils import timezone
from rest_framework import status

from finance.tests.expense_tests.expense_base import ExpenseBase


class ExpensePostTestCase(ExpenseBase):
    def test_post_single_creates_expense(self):
        response = self.client.post(self.list_url, self.expense_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("accepted", response.data)
        self.assertEqual(len(response.data["accepted"]), 1)
        self.assert_expense_saved(self.expense_payload)

    def test_post_preserves_multi_word_expense_name(self):
        payload = dict(self.expense_payload)
        payload["name"] = "YouTube Premium"
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        row = self.client.get(self.detail_url("YouTube Premium"))
        self.assertEqual(row.status_code, status.HTTP_200_OK)
        self.assertEqual(row.data["expense"]["name"], "YouTube Premium")

    def test_post_bulk_partial_reject(self):
        good = dict(self.expense_payload)
        bad = dict(self.expense_payload)
        bad["name"] = "bad-expense"
        bad["currency"] = "ZZZ"
        response = self.client.post(self.list_url, [good, bad], format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["accepted"]), 1)
        self.assertEqual(len(response.data["rejected"]), 1)

    def test_post_future_due_date_in_current_month_updates_safe_to_spend(self):
        today = timezone.now().date()
        last_day = calendar.monthrange(today.year, today.month)[1]
        last_of_month = date(today.year, today.month, last_day)
        if today >= last_of_month:
            self.skipTest("No future date left in current month to validate this regression path.")
        due_date = date(today.year, today.month, today.day + 1)

        before = self.client.get(self.snapshot_url)
        self.assertEqual(before.status_code, status.HTTP_200_OK)
        before_sts = before.data["snapshot"]["safe_to_spend"]

        payload = dict(self.expense_payload)
        payload["name"] = "future month debt"
        payload["amount"] = "123.45"
        payload["due_date"] = str(due_date)
        payload["start_date"] = str(due_date)
        payload["paid_flag"] = False
        create = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(create.status_code, status.HTTP_201_CREATED, msg=create.data)

        after = self.client.get(self.snapshot_url)
        self.assertEqual(after.status_code, status.HTTP_200_OK)
        after_sts = after.data["snapshot"]["safe_to_spend"]
        self.assertNotEqual(before_sts, after_sts)

    def test_post_missing_required_field_returns_400(self):
        payload = dict(self.expense_payload)
        payload.pop("amount")
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

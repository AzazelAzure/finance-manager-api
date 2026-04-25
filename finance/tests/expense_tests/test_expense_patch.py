from datetime import date

from dateutil.relativedelta import relativedelta
from rest_framework import status

from finance.models import UpcomingExpense
from finance.tests.expense_tests.expense_base import ExpenseBase


class ExpensePatchTestCase(ExpenseBase):
    def test_patch_partial_update(self):
        self.create_expense()
        response = self.client.patch(
            self.detail_url("rent"),
            {"amount": "1600.00", "currency": self.profile.base_currency},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["updated"][0]["name"], "rent")
        self.assertEqual(str(response.data["updated"][0]["amount"]), "1600.00")

    def test_patch_rename_updates_linked_transaction_bill(self):
        self.create_expense()
        tx_id = self.create_linked_expense_transaction("rent")
        response = self.client.patch(
            self.detail_url("rent"),
            {"name": "rent-updated", "currency": self.profile.base_currency},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assert_tx_bill(tx_id, "rent-updated")

    def test_transaction_payment_advances_recurring_due_date(self):
        payload = dict(self.expense_payload)
        payload["name"] = "internet"
        payload["due_date"] = str(date.today())
        payload["start_date"] = str(date.today())
        payload["is_recurring"] = True
        self.create_expense(payload)

        original = UpcomingExpense.objects.for_user(self.profile.user_id).get(name="internet")
        self.create_linked_expense_transaction("internet")

        original.refresh_from_db()
        expected_due = date.today() + relativedelta(months=1)
        self.assertEqual(original.due_date, expected_due)
        self.assertFalse(original.paid_flag)

"""Integration tests: cadence-aware bill due-date reversal on tx edit/delete."""

from datetime import date, timedelta

from django.urls import reverse
from rest_framework import status

from finance.models import UpcomingExpense, Transaction
from finance.tests.expense_tests.expense_base import ExpenseBase


class BillTxLinkageReversalTests(ExpenseBase):
    def _weekly_bill_payload(self, name: str, due: date) -> dict:
        return {
            "name": name,
            "amount": "50.00",
            "currency": self.profile.base_currency,
            "due_date": str(due),
            "start_date": str(due),
            "is_recurring": True,
            "cadence": "weekly",
        }

    def test_weekly_bill_edit_linked_transaction_reverses_due_date(self):
        due = date(2026, 6, 1)
        self.create_expense(self._weekly_bill_payload("weekly-edit", due))
        tx_id = self.create_linked_expense_transaction("weekly-edit", payment_date=due)

        row = UpcomingExpense.objects.for_user(self.profile.user_id).get(name="weekly-edit")
        self.assertEqual(row.due_date, due + timedelta(days=7))

        tx = Transaction.objects.for_user(self.profile.user_id).get(tx_id=tx_id)
        patch_url = reverse("transaction_detail", kwargs={"tx_id": tx_id})
        response = self.client.patch(
            patch_url,
            {"date": str(tx.date + timedelta(days=1))},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.data)

        row.refresh_from_db()
        self.assertEqual(row.due_date, due)
        self.assertFalse(row.paid_flag)

    def test_weekly_bill_delete_linked_transaction_reverses_due_date(self):
        due = date(2026, 6, 1)
        self.create_expense(self._weekly_bill_payload("weekly-delete", due))
        tx_id = self.create_linked_expense_transaction("weekly-delete", payment_date=due)

        row = UpcomingExpense.objects.for_user(self.profile.user_id).get(name="weekly-delete")
        self.assertEqual(row.due_date, due + timedelta(days=7))

        delete_url = reverse("transaction_detail", kwargs={"tx_id": tx_id})
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.data)
        self.assertFalse(Transaction.objects.for_user(self.profile.user_id).filter(tx_id=tx_id).exists())

        row.refresh_from_db()
        self.assertEqual(row.due_date, due)
        self.assertFalse(row.paid_flag)

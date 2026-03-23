from rest_framework import status

from finance.models import UpcomingExpense
from finance.tests.expense_tests.expense_base import ExpenseBase


class ExpenseDeleteTestCase(ExpenseBase):
    def test_delete_expense_success(self):
        self.create_expense()
        response = self.client.delete(self.detail_url("rent"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            UpcomingExpense.objects.for_user(self.profile.user_id).filter(name="rent").exists()
        )

    def test_delete_nonexistent_returns_400(self):
        response = self.client.delete(self.detail_url("missing-expense"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_expense_sets_linked_transaction_bill_unknown(self):
        self.create_expense()
        tx_id = self.create_linked_expense_transaction("rent")
        response = self.client.delete(self.detail_url("rent"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assert_tx_bill(tx_id, "unknown")

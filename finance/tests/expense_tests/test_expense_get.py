from rest_framework import status

from finance.tests.expense_tests.expense_base import ExpenseBase


class ExpenseGetTestCase(ExpenseBase):
    def test_get_list_returns_expenses(self):
        self.create_expense()
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("expenses", response.data)
        self.assertGreaterEqual(len(response.data["expenses"]), 1)
        self.assertIn("amount", response.data)

    def test_get_detail_returns_expense(self):
        self.create_expense()
        response = self.client.get(self.detail_url("rent"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("expense", response.data)
        self.assertEqual(response.data["expense"]["name"], "rent")
        self.assertIn("amount", response.data)

    def test_get_detail_nonexistent_returns_400(self):
        response = self.client.get(self.detail_url("missing-expense"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

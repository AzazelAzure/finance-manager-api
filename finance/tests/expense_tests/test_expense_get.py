from datetime import date

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

    def test_get_list_without_filters_returns_all_months(self):
        self.create_expense(
            {
                **self.expense_payload,
                "name": "rent_current",
            }
        )

        today = date.today()
        prev_month = 12 if today.month == 1 else today.month - 1
        prev_year = today.year - 1 if today.month == 1 else today.year
        previous_date = date(prev_year, prev_month, 15)
        self.create_expense(
            {
                **self.expense_payload,
                "name": "rent_previous",
                "due_date": previous_date.isoformat(),
                "start_date": previous_date.isoformat(),
            }
        )

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = {row["name"] for row in response.data["expenses"]}
        self.assertIn("rent_current", names)
        self.assertIn("rent_previous", names)

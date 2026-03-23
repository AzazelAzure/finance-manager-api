from rest_framework import status

from finance.tests.expense_tests.expense_base import ExpenseBase


class ExpensePostTestCase(ExpenseBase):
    def test_post_single_creates_expense(self):
        response = self.client.post(self.list_url, self.expense_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("accepted", response.data)
        self.assertEqual(len(response.data["accepted"]), 1)
        self.assert_expense_saved(self.expense_payload)

    def test_post_bulk_partial_reject(self):
        good = dict(self.expense_payload)
        bad = dict(self.expense_payload)
        bad["name"] = "bad-expense"
        bad["currency"] = "ZZZ"
        response = self.client.post(self.list_url, [good, bad], format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["accepted"]), 1)
        self.assertEqual(len(response.data["rejected"]), 1)

    def test_post_missing_required_field_returns_400(self):
        payload = dict(self.expense_payload)
        payload.pop("amount")
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

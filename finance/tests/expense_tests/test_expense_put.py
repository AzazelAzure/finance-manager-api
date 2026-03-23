from rest_framework import status

from finance.tests.expense_tests.expense_base import ExpenseBase


class ExpensePutTestCase(ExpenseBase):
    def test_put_full_update_success(self):
        self.create_expense()
        payload = dict(self.expense_payload)
        payload["name"] = "rent-renamed"
        payload["amount"] = "1700.00"
        response = self.client.put(self.detail_url("rent"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["updated"][0]["name"], "rent-renamed")
        self.assertEqual(str(response.data["updated"][0]["amount"]), "1700.00")

    def test_put_incomplete_payload_rejected(self):
        self.create_expense()
        payload = {"name": "rent-renamed", "amount": "1700.00"}
        response = self.client.put(self.detail_url("rent"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

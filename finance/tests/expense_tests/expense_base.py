from datetime import date
from decimal import Decimal

from django.urls import reverse
from rest_framework import status

from finance.models import PaymentSource, Transaction, UpcomingExpense
from finance.tests.basetest import BaseTestCase


class ExpenseBase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.list_url = reverse("upcoming_expenses")
        self.detail_url = lambda name: reverse(
            "upcoming_expense_detail_update_delete", kwargs={"name": name}
        )
        self.tx_list_url = reverse("transactions_list_create")

        self.expense_payload = {
            "name": "rent",
            "amount": Decimal("1500.00"),
            "due_date": str(date.today()),
            "start_date": str(date.today()),
            "end_date": None,
            "paid_flag": False,
            "currency": self.profile.base_currency,
            "is_recurring": True,
        }

    def _normalize_expense(self, payload: dict) -> dict:
        out = dict(payload)
        out["name"] = str(out["name"]).lower()
        out["currency"] = str(out["currency"]).upper()
        out["amount"] = Decimal(str(out["amount"])).quantize(Decimal("0.01"))
        return out

    def create_expense(self, payload=None):
        payload = payload or self.expense_payload
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, msg=response.data)
        return response

    def create_linked_expense_transaction(self, bill_name: str):
        source_obj = PaymentSource.objects.for_user(self.profile.user_id).first()
        tx_payload = {
            "date": str(date.today()),
            "description": "expense payment",
            "amount": "25.00",
            "source": source_obj.source,
            "currency": source_obj.currency,
            "tags": [self.tag_list[0]],
            "tx_type": "EXPENSE",
            "category": self.categories[0].name,
            "bill": bill_name,
        }
        response = self.client.post(self.tx_list_url, tx_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, msg=response.data)
        return response.data["accepted"][0]["tx_id"]

    def assert_expense_saved(self, payload: dict):
        expected = self._normalize_expense(payload)
        db_row = UpcomingExpense.objects.for_user(self.profile.user_id).get(name=expected["name"])
        self.assertEqual(db_row.currency, expected["currency"])
        self.assertEqual(
            Decimal(str(db_row.amount)).quantize(Decimal("0.01")),
            expected["amount"],
        )

    def assert_tx_bill(self, tx_id: str, expected_bill: str):
        tx = Transaction.objects.for_user(self.profile.user_id).get(tx_id=tx_id)
        self.assertEqual(tx.bill, expected_bill)

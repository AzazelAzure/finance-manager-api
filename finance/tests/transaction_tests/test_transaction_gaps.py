from datetime import date

from django.urls import reverse
from rest_framework import status

from finance.models import Transaction, UpcomingExpense
from finance.tests.transaction_tests.transaction_base import TransactionPatchBase


class TransactionGapTestCase(TransactionPatchBase):
    def setUp(self):
        super().setUp()
        self.tx_list_url = reverse("transactions_list_create")
        self.expense_list_url = reverse("upcoming_expenses")
        self.expense_detail_url = lambda name: reverse(
            "upcoming_expense_detail_update_delete", kwargs={"name": name}
        )

    def test_patch_forbidden_tx_id_without_tags_still_rejected(self):
        payload = dict(self.update_amount_data)
        payload.pop("tags", None)
        payload["tx_id"] = "2099-01-01-FORBIDDEN"
        response = self.client.patch(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_forbidden_entry_id_without_tags_still_rejected(self):
        payload = dict(self.update_amount_data)
        payload.pop("tags", None)
        payload["entry_id"] = 999999
        response = self.client.patch(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_expense_rename_propagates_to_transaction_bill(self):
        expense_payload = {
            "name": "water-bill",
            "amount": "45.00",
            "due_date": str(date.today()),
            "start_date": str(date.today()),
            "end_date": None,
            "paid_flag": False,
            "currency": self.profile.base_currency,
            "is_recurring": True,
        }
        expense_create = self.client.post(
            self.expense_list_url, expense_payload, format="json"
        )
        self.assertEqual(expense_create.status_code, status.HTTP_201_CREATED)

        tx_payload = dict(self.expense_data)
        tx_payload["bill"] = "water-bill"
        tx_payload["currency"] = self.sources[0].currency
        tx_payload["source"] = self.sources[0].source
        tx_payload["date"] = str(date.today())
        tx_response = self.client.post(self.tx_list_url, tx_payload, format="json")
        self.assertEqual(tx_response.status_code, status.HTTP_201_CREATED, msg=tx_response.data)
        tx_id = tx_response.data["accepted"][0]["tx_id"]

        rename = self.client.patch(
            self.expense_detail_url("water-bill"),
            {"name": "water-bill-next", "currency": self.profile.base_currency},
            format="json",
        )
        self.assertEqual(rename.status_code, status.HTTP_200_OK, msg=rename.data)
        tx = Transaction.objects.for_user(self.profile.user_id).get(tx_id=tx_id)
        self.assertEqual(tx.bill, "water-bill-next")

    def test_expense_delete_sets_transaction_bill_unknown(self):
        UpcomingExpense.objects.create(
            uid=self.profile.user_id,
            name="phone",
            amount="70.00",
            due_date=date.today(),
            start_date=date.today(),
            paid_flag=False,
            currency=self.profile.base_currency,
            is_recurring=True,
        )
        tx_payload = dict(self.expense_data)
        tx_payload["bill"] = "phone"
        tx_payload["currency"] = self.sources[0].currency
        tx_payload["source"] = self.sources[0].source
        tx_payload["date"] = str(date.today())
        tx_response = self.client.post(self.tx_list_url, tx_payload, format="json")
        self.assertEqual(tx_response.status_code, status.HTTP_201_CREATED, msg=tx_response.data)
        tx_id = tx_response.data["accepted"][0]["tx_id"]

        delete = self.client.delete(self.expense_detail_url("phone"))
        self.assertEqual(delete.status_code, status.HTTP_200_OK, msg=delete.data)
        tx = Transaction.objects.for_user(self.profile.user_id).get(tx_id=tx_id)
        self.assertEqual(tx.bill, "unknown")

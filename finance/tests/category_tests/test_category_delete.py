from decimal import Decimal

from django.urls import reverse
from rest_framework import status

from finance.models import Transaction
from finance.tests.category_tests.category_base import CategoryBase


class CategoryDeleteTestCase(CategoryBase):
    def test_delete_reassigns_linked_transactions(self):
        name = self.seed_category("delete-cat")
        tx_payload = {
            "date": "2024-01-01",
            "description": "category-delete",
            "amount": "15.00",
            "source": self.sources.source,
            "currency": self.sources.currency,
            "tx_type": "EXPENSE",
            "tags": [],
            "category": name,
        }
        tx = self.client.post(reverse("transactions_list_create"), tx_payload, format="json")
        self.assertEqual(tx.status_code, status.HTTP_201_CREATED)
        tx_id = tx.data["accepted"][0]["tx_id"]
        before_amount = Transaction.objects.for_user(self.profile.user_id).get_tx(tx_id).first().amount
        url = reverse("category_detail_update_delete", kwargs={"cat_name": name})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tx_obj = Transaction.objects.for_user(self.profile.user_id).get_tx(tx_id).first()
        self.assertEqual(tx_obj.category, tx_obj.tx_type.lower())
        self.assertEqual(Decimal(str(tx_obj.amount)), Decimal(str(before_amount)))

    def test_delete_nonexistent_rejected(self):
        url = reverse("category_detail_update_delete", kwargs={"cat_name": "not-real"})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

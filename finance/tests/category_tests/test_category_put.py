from django.urls import reverse
from rest_framework import status

from finance.models import Transaction
from finance.tests.category_tests.category_base import CategoryBase


class CategoryPutTestCase(CategoryBase):
    def test_put_updates_category_name_and_tx_side_effect(self):
        name = self.seed_category("old-cat")
        tx_payload = {
            "date": "2024-01-01",
            "description": "category-rename",
            "amount": "10.00",
            "source": self.sources.source,
            "currency": self.sources.currency,
            "tx_type": "EXPENSE",
            "tags": [],
            "category": name,
        }
        tx = self.client.post(reverse("transactions_list_create"), tx_payload, format="json")
        self.assertEqual(tx.status_code, status.HTTP_201_CREATED)
        tx_id = tx.data["accepted"][0]["tx_id"]
        url = reverse("category_detail_update_delete", kwargs={"cat_name": name})
        response = self.client.put(url, {"name": "new-cat"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["updated"]["name"], "new-cat")
        tx_obj = Transaction.objects.for_user(self.profile.user_id).get_tx(tx_id).first()
        self.assertEqual(tx_obj.category, "new-cat")

    def test_put_invalid_payload_rejected(self):
        name = self.seed_category("put-invalid")
        url = reverse("category_detail_update_delete", kwargs={"cat_name": name})
        response = self.client.put(url, {"name": ""}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

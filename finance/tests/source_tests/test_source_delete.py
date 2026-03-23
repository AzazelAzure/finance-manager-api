from django.urls import reverse
from rest_framework import status

from finance.models import PaymentSource, Transaction
from finance.tests.source_tests.source_base import SourceBase


class SourceDeleteTestCase(SourceBase):
    def test_delete_collection_body_success(self):
        expected = self.seed_source("delete-source")
        response = self.client.delete(self.url, {"source": expected["source"]}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            PaymentSource.objects.for_user(self.profile.user_id)
            .get_by_source(expected["source"])
            .exists()
        )

    def test_delete_nonexistent_source_rejected(self):
        response = self.client.delete(self.url, {"source": "missing"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_unknown_rejected(self):
        response = self.client.delete(self.url, {"source": "unknown"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_updates_safe_to_spend_for_spend_account(self):
        expected = self.seed_source("spend-delete", amount="200.00")
        self.profile.spend_accounts = [expected["source"]]
        self.profile.save(update_fields=["spend_accounts"])
        response = self.client.delete(self.url, {"source": expected["source"]}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("snapshot", response.data)
        self.assertIsNotNone(response.data["snapshot"]["safe_to_spend"])

    def test_delete_reassigns_transactions_to_unknown(self):
        expected = self.seed_source("tx-reassign")
        tx_payload = {
            "date": "2024-01-01",
            "description": "for source delete",
            "amount": "10.00",
            "source": expected["source"],
            "currency": expected["currency"],
            "tx_type": "EXPENSE",
            "tags": [],
            "category": self.categories[0].name,
        }
        tx_response = self.client.post(reverse("transactions_list_create"), tx_payload, format="json")
        self.assertEqual(tx_response.status_code, status.HTTP_201_CREATED)
        response = self.client.delete(self.url, {"source": expected["source"]}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tx = Transaction.objects.for_user(self.profile.user_id).get_tx(
            tx_response.data["accepted"][0]["tx_id"]
        ).first()
        self.assertEqual(tx.source, "unknown")

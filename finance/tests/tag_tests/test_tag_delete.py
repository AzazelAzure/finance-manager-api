from rest_framework import status
from django.urls import reverse

from finance.tests.tag_tests.tag_base import TagBase


class TagDeleteTestCase(TagBase):
    def test_delete_removes_tag(self):
        existing = self.tag_list[0]
        response = self.client.delete(self.url, {"tags": {existing: "delete"}}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(existing, response.data["deleted"])

    def test_transaction_post_with_new_tag_auto_adds_tag(self):
        payload = {
            "date": "2024-01-01",
            "description": "tag auto add",
            "amount": "12.00",
            "source": self.sources.source,
            "currency": self.sources.currency,
            "tx_type": "EXPENSE",
            "tags": ["brand-new-tag"],
            "category": self.categories[0].name,
        }
        response = self.client.post(reverse("transactions_list_create"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        tags_response = self.client.get(self.url)
        self.assertEqual(tags_response.status_code, status.HTTP_200_OK)
        self.assertIn("brand-new-tag", tags_response.data["tags"])

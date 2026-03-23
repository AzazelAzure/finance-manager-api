from rest_framework import status

from finance.tests.category_tests.category_base import CategoryBase


class CategoryPostTestCase(CategoryBase):
    def test_post_valid_category(self):
        response = self.client.post(self.url, {"name": "food-custom"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["accepted"][0]["name"], "food-custom")

    def test_post_duplicate_category_rejected(self):
        self.seed_category("dup-cat")
        response = self.client.post(self.url, {"name": "dup-cat"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_invalid_payload_rejected(self):
        response = self.client.post(self.url, {"name": ""}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

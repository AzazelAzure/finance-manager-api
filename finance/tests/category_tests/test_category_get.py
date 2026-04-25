from django.urls import reverse
from rest_framework import status

from finance.tests.category_tests.category_base import CategoryBase


class CategoryGetTestCase(CategoryBase):
    def test_get_list(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_get_detail(self):
        name = self.seed_category("detail-cat")
        url = reverse("category_detail_update_delete", kwargs={"cat_name": name})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], name)

    def test_get_nonexistent_rejected(self):
        url = reverse("category_detail_update_delete", kwargs={"cat_name": "no-cat"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

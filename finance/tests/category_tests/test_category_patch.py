from django.urls import reverse
from rest_framework import status

from finance.tests.category_tests.category_base import CategoryBase


class CategoryPatchTestCase(CategoryBase):
    def test_patch_updates_name(self):
        name = self.seed_category("patch-old")
        url = reverse("category_detail_update_delete", kwargs={"cat_name": name})
        response = self.client.patch(url, {"name": "patch-new"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["updated"]["name"], "patch-new")

    def test_patch_nonexistent_rejected(self):
        url = reverse("category_detail_update_delete", kwargs={"cat_name": "none"})
        response = self.client.patch(url, {"name": "x"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

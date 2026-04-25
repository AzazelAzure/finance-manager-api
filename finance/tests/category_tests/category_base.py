from django.urls import reverse

from finance.tests.basetest import BaseTestCase


class CategoryBase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("categories")

    def seed_category(self, name="custom-category"):
        payload = {"name": name}
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, 201)
        return name

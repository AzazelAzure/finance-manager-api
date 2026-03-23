from rest_framework import status

from finance.tests.tag_tests.tag_base import TagBase


class TagGetTestCase(TagBase):
    def test_get_returns_tags(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("tags", response.data)
        self.assertIsInstance(response.data["tags"], list)

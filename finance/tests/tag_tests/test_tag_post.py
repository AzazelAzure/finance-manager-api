from rest_framework import status

from finance.tests.tag_tests.tag_base import TagBase


class TagPostTestCase(TagBase):
    def test_post_creates_tags(self):
        response = self.client.post(self.url, {"tags": ["lane-a-tag"]}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("lane-a-tag", response.data["accepted"])

    def test_post_duplicate_rejected(self):
        existing = self.tag_list[0]
        response = self.client.post(self.url, {"tags": [existing]}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

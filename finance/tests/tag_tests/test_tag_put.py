from rest_framework import status

from finance.tests.tag_tests.tag_base import TagBase


class TagPutTestCase(TagBase):
    def test_put_renames_tag(self):
        existing = self.tag_list[0]
        response = self.client.put(self.url, {"tags": {existing: "put-renamed"}}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("put-renamed", response.data["updated"])

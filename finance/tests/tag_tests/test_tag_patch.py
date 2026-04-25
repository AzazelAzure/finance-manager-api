from rest_framework import status

from finance.tests.tag_tests.tag_base import TagBase


class TagPatchTestCase(TagBase):
    def test_patch_renames_tag(self):
        existing = self.tag_list[0]
        response = self.client.patch(self.url, {"tags": {existing: "renamed-tag"}}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("renamed-tag", response.data["updated"])

    def test_patch_nonexistent_tag_rejected(self):
        response = self.client.patch(self.url, {"tags": {"missing-tag": "new"}}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

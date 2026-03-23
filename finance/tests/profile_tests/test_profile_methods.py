from rest_framework import status

from finance.tests.profile_tests.profile_base import ProfileBase


class AppProfileMethodTests(ProfileBase):
    def test_post_denied(self):
        response = self.client.post(self.profile_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_put_denied(self):
        response = self.client.put(self.profile_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_denied(self):
        response = self.client.delete(self.profile_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_501_NOT_IMPLEMENTED)

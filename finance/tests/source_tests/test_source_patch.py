from django.urls import reverse
from rest_framework import status

from finance.tests.source_tests.source_base import SourceBase


class SourcePatchTestCase(SourceBase):
    def test_patch_partial_single_field(self):
        expected = self.seed_source("patch-source")
        url = reverse("source_detail_update_delete", kwargs={"source": expected["source"]})
        response = self.client.patch(url, {"acc_type": "savings"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["updated"]["acc_type"], "SAVINGS")

    def test_patch_partial_multiple_fields(self):
        expected = self.seed_source("patch-multi")
        url = reverse("source_detail_update_delete", kwargs={"source": expected["source"]})
        payload = {"acc_type": "checking", "currency": "eur"}
        response = self.client.patch(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["updated"]["acc_type"], "CHECKING")
        self.assertEqual(response.data["updated"]["currency"], "EUR")

    def test_patch_invalid_payload_rejected(self):
        expected = self.seed_source("patch-invalid")
        url = reverse("source_detail_update_delete", kwargs={"source": expected["source"]})
        response = self.client.patch(url, {"amount": "oops"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_unknown_forbidden(self):
        url = reverse("source_detail_update_delete", kwargs={"source": "unknown"})
        response = self.client.patch(url, {"acc_type": "cash"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_nonexistent_source_rejected(self):
        url = reverse("source_detail_update_delete", kwargs={"source": "does-not-exist"})
        response = self.client.patch(url, {"acc_type": "cash"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

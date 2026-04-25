from django.urls import reverse
from rest_framework import status

from finance.tests.source_tests.source_base import SourceBase


class SourcePutTestCase(SourceBase):
    def test_put_full_payload_success(self):
        expected = self.seed_source("put-source")
        url = reverse("source_detail_update_delete", kwargs={"source": expected["source"]})
        payload = {
            "source": "put-source-renamed",
            "acc_type": "investment",
            "amount": "1234.56",
            "currency": "usd",
        }
        response = self.client.put(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["updated"]["source"], "put-source-renamed")
        self.assertEqual(response.data["updated"]["acc_type"], "INVESTMENT")

    def test_put_missing_required_fields_rejected(self):
        expected = self.seed_source("put-missing")
        url = reverse("source_detail_update_delete", kwargs={"source": expected["source"]})
        response = self.client.put(url, {"source": "x"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_invalid_fields_rejected(self):
        expected = self.seed_source("put-invalid")
        url = reverse("source_detail_update_delete", kwargs={"source": expected["source"]})
        payload = {
            "source": "put-invalid",
            "acc_type": "not-real",
            "amount": "1.00",
            "currency": "usd",
        }
        response = self.client.put(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_unknown_forbidden(self):
        url = reverse("source_detail_update_delete", kwargs={"source": "unknown"})
        payload = {
            "source": "unknown",
            "acc_type": "cash",
            "amount": "1.00",
            "currency": "usd",
        }
        response = self.client.put(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

from django.urls import reverse
from rest_framework import status

from finance.tests.source_tests.source_base import SourceBase


class SourceGetTestCase(SourceBase):
    def test_get_list_returns_sources(self):
        self.seed_source("wallet-a")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertGreaterEqual(len(response.data), 1)

    def test_get_list_filters_by_source_and_acc_type(self):
        self.seed_source("filter-source", acc_type="cash")
        self.seed_source("other-source", acc_type="savings")
        response = self.client.get(self.url, {"source": "filter-source", "acc_type": "cash"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_get_detail_returns_single_source(self):
        expected = self.seed_source("detail-source")
        url = reverse("source_detail_update_delete", kwargs={"source": expected["source"]})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["source"], expected["source"])

    def test_get_detail_missing_source_returns_400(self):
        url = reverse("source_detail_update_delete", kwargs={"source": "missing-source"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

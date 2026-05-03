from django.urls import reverse
from rest_framework import status

from finance.tests.transaction_tests.transaction_base import TransactionBase


class ExchangeRatesMatrixTests(TransactionBase):
    def setUp(self):
        super().setUp()
        self.url = reverse("finance_exchange_rates")

    def test_requires_auth(self):
        self.client.logout()
        res = self.client.get(self.url, {"currencies": "USD,EUR"})
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_returns_rates_for_subset(self):
        res = self.client.get(self.url, {"currencies": "USD,EUR"})
        self.assertEqual(res.status_code, status.HTTP_200_OK, msg=res.data)
        self.assertIn("rates", res.data)
        self.assertIn("fetched_at_ms", res.data)
        self.assertIn("currencies", res.data)
        self.assertIn("USD", res.data["currencies"])
        self.assertIn("EUR", res.data["currencies"])
        self.assertIn("USD:EUR", res.data["rates"])
        self.assertIsInstance(res.data["rates"]["USD:EUR"], float)

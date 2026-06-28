from datetime import date
from decimal import Decimal

from django.urls import reverse
from rest_framework import status

from finance.models import BalanceSnapshot
from finance.tests.basetest import BaseTestCase


class BalanceHistoryApiTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.uid = str(self.profile.user_id)
        self.url = reverse("balance_history")

    def test_requires_auth(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_empty_series(self):
        resp = self.client.get(self.url, {"range": "7d"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["series"], [])
        self.assertEqual(resp.data["base_currency"], self.profile.base_currency)

    def test_returns_snapshots_in_base_currency(self):
        source = self.sources.source
        BalanceSnapshot.objects.create(
            uid=self.uid,
            source=source,
            snapshot_date=date(2026, 1, 10),
            closing_balance=Decimal("100.00"),
            currency="USD",
        )
        BalanceSnapshot.objects.create(
            uid=self.uid,
            source=source,
            snapshot_date=date(2026, 1, 11),
            closing_balance=Decimal("150.00"),
            currency="USD",
        )
        resp = self.client.get(
            self.url,
            {"start_date": "2026-01-01", "end_date": "2026-12-31"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["series"]), 2)
        self.assertEqual(resp.data["series"][0]["currency"], self.profile.base_currency)

    def test_source_filter(self):
        BalanceSnapshot.objects.create(
            uid=self.uid,
            source="cash",
            snapshot_date=date(2026, 2, 1),
            closing_balance=Decimal("10.00"),
            currency="USD",
        )
        BalanceSnapshot.objects.create(
            uid=self.uid,
            source="savings",
            snapshot_date=date(2026, 2, 1),
            closing_balance=Decimal("20.00"),
            currency="USD",
        )
        resp = self.client.get(
            self.url,
            {"source": "cash", "start_date": "2026-01-01", "end_date": "2026-12-31"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["series"]), 1)
        self.assertEqual(resp.data["series"][0]["source"], "cash")

from decimal import Decimal

from django.urls import reverse
from freezegun import freeze_time
from rest_framework import status

from finance.models import PaymentSource
from finance.tests.profile_tests.profile_base import ProfileBase


@freeze_time("2024-06-15 12:00:00")
class SnapshotSourceFilterTests(ProfileBase):
    """Snapshot source filter must resolve display names like GET /transactions/."""

    def setUp(self):
        super().setUp()
        self.tx_url = reverse("transactions_list_create")
        self.uid = str(self.profile.user_id)

        PaymentSource.objects.create(
            uid=self.uid,
            source="Cash",
            source_id="2024-06-15-CASH0001",
            acc_type="CASH",
            amount=Decimal("1000.00"),
            currency=self.profile.base_currency,
        )
        PaymentSource.objects.create(
            uid=self.uid,
            source="Savings",
            source_id="2024-06-15-SAVE0001",
            acc_type="SAVINGS",
            amount=Decimal("500.00"),
            currency=self.profile.base_currency,
        )

        self.cash_current_tx_id = self._post_tx(
            source="Cash",
            amount=Decimal("50.00"),
            date="2024-06-10",
            tx_type="EXPENSE",
        )
        self.other_current_tx_id = self._post_tx(
            source="Savings",
            amount=Decimal("30.00"),
            date="2024-06-12",
            tx_type="EXPENSE",
        )
        self.cash_old_tx_id = self._post_tx(
            source="Cash",
            amount=Decimal("20.00"),
            date="2024-05-01",
            tx_type="EXPENSE",
        )

    def _post_tx(self, **fields):
        payload = {
            "uid": self.uid,
            "description": "snapshot-source-filter",
            "amount": fields["amount"],
            "source": fields["source"],
            "currency": self.profile.base_currency,
            "tx_type": fields["tx_type"],
            "tags": [self.tag_list[0]],
            "category": self.categories[0].name,
            "date": fields["date"],
        }
        response = self.client.post(self.tx_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.data["accepted"][0]["tx_id"]

    def test_cash_current_month_matches_get_transactions_parity(self):
        params = {"source": "Cash", "current_month": "true"}
        tx_resp = self.client.get(self.tx_url, params)
        snap_resp = self.client.get(self.snapshot_url, params)
        self.assertEqual(snap_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(tx_resp.status_code, status.HTTP_200_OK)

        tx_ids = {row["tx_id"] for row in tx_resp.data["transactions"]}
        snap_ids = {row["tx_id"] for row in snap_resp.data["transactions_for_month"]}
        self.assertEqual(snap_ids, tx_ids)
        self.assertEqual(snap_ids, {self.cash_current_tx_id})

    def test_unknown_source_yields_empty_parity(self):
        params = {"source": "NotARealSourceName"}
        tx_resp = self.client.get(self.tx_url, params)
        snap_resp = self.client.get(self.snapshot_url, params)
        self.assertEqual(tx_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(snap_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(tx_resp.data["transactions"]), 0)
        self.assertEqual(len(snap_resp.data["transactions_for_month"]), 0)
        self.assertEqual(
            Decimal(str(snap_resp.data["total_expenses_for_month"])),
            Decimal("0.00"),
        )

    def test_unfiltered_regression_current_month_default(self):
        snap_resp = self.client.get(self.snapshot_url)
        self.assertEqual(snap_resp.status_code, status.HTTP_200_OK)
        ids = {row["tx_id"] for row in snap_resp.data["transactions_for_month"]}
        self.assertIn(self.cash_current_tx_id, ids)
        self.assertIn(self.other_current_tx_id, ids)
        self.assertNotIn(self.cash_old_tx_id, ids)

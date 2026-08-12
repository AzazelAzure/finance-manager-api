from decimal import Decimal

from django.urls import reverse
from freezegun import freeze_time
from rest_framework import status

from finance.models import PaymentSource
from finance.tests.profile_tests.profile_base import ProfileBase


@freeze_time("2024-06-15 12:00:00")
class AppProfileSnapshotTests(ProfileBase):
    def setUp(self):
        super().setUp()
        self.uid = str(self.profile.user_id)
        self.tx_url = reverse("transactions_list_create")
        PaymentSource.objects.create(
            uid=self.uid,
            source="eur-wallet",
            acc_type="EWALLET",
            amount=Decimal("100.00"),
            currency="EUR",
        )
        self.named_source = PaymentSource.objects.create(
            uid=self.uid,
            source="Cash Display",
            source_id="2024-06-15-CASH0001",
            acc_type="CASH",
            amount=Decimal("500.00"),
            currency=self.profile.base_currency,
        )
        payload = {
            "uid": self.uid,
            "description": "snapshot-source-hydrate",
            "amount": Decimal("25.00"),
            "source": "Cash Display",
            "currency": self.profile.base_currency,
            "tx_type": "EXPENSE",
            "tags": [self.tag_list[0]],
            "category": self.categories[0].name,
            "date": "2024-06-10",
        }
        created = self.client.post(self.tx_url, payload, format="json")
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.hydrate_tx_id = created.data["accepted"][0]["tx_id"]

    def test_profile_get_shape(self):
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("spend_accounts", response.data)
        self.assertIn("base_currency", response.data)
        self.assertIn("timezone", response.data)
        self.assertIn("start_of_week", response.data)

    def test_snapshot_route_returns_snapshot_payload_shape(self):
        response = self.client.get(self.snapshot_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("snapshot", response.data)
        self.assertIn("transactions_for_month", response.data)
        self.assertIn("total_expenses_for_month", response.data)
        self.assertIn("total_income_for_month", response.data)
        self.assertIn("total_transfer_out_for_month", response.data)
        self.assertIn("total_transfer_in_for_month", response.data)

    def test_snapshot_includes_dashboard_chart_support_fields(self):
        response = self.client.get(self.snapshot_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("expense_by_category", response.data)
        self.assertIn("source_balances", response.data)
        self.assertIsInstance(response.data["expense_by_category"], list)
        self.assertIsInstance(response.data["source_balances"], list)
        self.assertGreaterEqual(len(response.data["source_balances"]), 1)

    def test_snapshot_includes_dashboard_series_support_fields(self):
        response = self.client.get(self.snapshot_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("flow_series", response.data)
        self.assertIn("daily_spend", response.data)
        self.assertIn("daily_income", response.data)
        self.assertIsInstance(response.data["flow_series"], list)
        self.assertIsInstance(response.data["daily_spend"], list)
        self.assertIsInstance(response.data["daily_income"], list)

    def test_base_currency_change_updates_snapshot_totals(self):
        before = self.client.get(self.snapshot_url)
        self.assertEqual(before.status_code, 200)
        before_assets = Decimal(str(before.data["snapshot"]["total_assets"]))

        patch = self.client.patch(self.profile_url, {"base_currency": "EUR"}, format="json")
        self.assertEqual(patch.status_code, 200)
        after = self.client.get(self.snapshot_url)
        self.assertEqual(after.status_code, 200)
        after_assets = Decimal(str(after.data["snapshot"]["total_assets"]))

        self.assertNotEqual(before_assets, after_assets)

    def test_base_currency_change_recomputes_per_acc_type_snapshot_fields(self):
        """EWALLET/CASH/etc. must be recomputed in the new base (not left stale)."""
        before = self.client.get(self.snapshot_url)
        self.assertEqual(before.status_code, 200)
        before_ewallet = Decimal(str(before.data["snapshot"]["total_ewallet"]))

        patch = self.client.patch(self.profile_url, {"base_currency": "EUR"}, format="json")
        self.assertEqual(patch.status_code, 200)
        after = self.client.get(self.snapshot_url)
        after_ewallet = Decimal(str(after.data["snapshot"]["total_ewallet"]))

        self.assertNotEqual(
            before_ewallet,
            after_ewallet,
            "total_ewallet should change when base_currency changes (100 EUR ewallet in setUp)",
        )

    def test_snapshot_transactions_expose_source_display_name(self):
        """transactions_for_month[].source must be display name, not stored source_id."""
        response = self.client.get(self.snapshot_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = response.data["transactions_for_month"]
        match = next((row for row in rows if row["tx_id"] == self.hydrate_tx_id), None)
        self.assertIsNotNone(match, "expected hydrate fixture transaction in snapshot")
        self.assertEqual(match["source"], "Cash Display")
        self.assertNotEqual(match["source"], self.named_source.source_id)

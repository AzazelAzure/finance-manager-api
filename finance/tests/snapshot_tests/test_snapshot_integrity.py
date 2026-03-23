from decimal import Decimal

from django.urls import reverse
from rest_framework import status

import finance.services.expense_services as exp_svc
from finance.models import Category, FinancialSnapshot, PaymentSource, Tag
from finance.tests.basetest import BaseTestCase


class FinancialSnapshotIntegrityTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.sources_url = reverse("sources")
        self.tx_url = reverse("transactions_list_create")
        self.snapshot_url = reverse("appprofile_snapshot")
        self.uid = str(self.profile.user_id)

    def test_snapshot_changes_after_source_transaction_and_expense_mutations(self):
        baseline = FinancialSnapshot.objects.for_user(self.uid).first()
        baseline_assets = Decimal(str(baseline.total_assets))

        source_payload = {
            "source": "snapshot-source",
            "acc_type": "CASH",
            "amount": "33.00",
            "currency": "USD",
        }
        source_resp = self.client.post(self.sources_url, source_payload, format="json")
        self.assertEqual(source_resp.status_code, status.HTTP_201_CREATED)

        tx_payload = {
            "date": "2025-01-01",
            "description": "snapshot tx",
            "amount": "10.00",
            "source": "snapshot-source",
            "currency": "USD",
            "tx_type": "INCOME",
            "tags": [],
            "category": self.categories[0].name,
        }
        tx_resp = self.client.post(self.tx_url, tx_payload, format="json")
        self.assertEqual(tx_resp.status_code, status.HTTP_201_CREATED)

        exp_svc.add_expense(
            self.uid,
            {
                "name": "snapshot-bill",
                "amount": "5.00",
                "currency": "USD",
                "start_date": "2025-01-01",
                "due_date": "2025-01-01",
                "is_recurring": False,
            },
        )

        after = FinancialSnapshot.objects.for_user(self.uid).first()
        self.assertNotEqual(Decimal(str(after.total_assets)), baseline_assets)

    def test_category_and_tag_operations_do_not_change_snapshot_totals(self):
        PaymentSource.objects.create(
            uid=self.uid,
            source="stable-source",
            acc_type="CASH",
            amount=Decimal("20.00"),
            currency="USD",
        )
        before = FinancialSnapshot.objects.for_user(self.uid).first()
        before_totals = (
            Decimal(str(before.total_assets)),
            Decimal(str(before.safe_to_spend)),
            Decimal(str(before.total_leaks)),
        )

        Category.objects.create(uid=self.uid, name="stable-category")
        Tag.objects.create(uid=self.uid, tags=["stable-tag"])

        after = FinancialSnapshot.objects.for_user(self.uid).first()
        after_totals = (
            Decimal(str(after.total_assets)),
            Decimal(str(after.safe_to_spend)),
            Decimal(str(after.total_leaks)),
        )
        self.assertEqual(before_totals, after_totals)

    def test_snapshot_endpoint_values_align_with_db_snapshot(self):
        response = self.client.get(self.snapshot_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        db_snapshot = FinancialSnapshot.objects.for_user(self.uid).first()
        self.assertEqual(
            Decimal(str(response.data["snapshot"]["total_assets"])).quantize(Decimal("0.01")),
            Decimal(str(db_snapshot.total_assets)).quantize(Decimal("0.01")),
        )

"""Migration 0019 — BalanceSnapshot collision dedup during source_id backfill."""

import uuid
from datetime import date
from decimal import Decimal

from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from finance.models import BalanceSnapshot, PaymentSource


class Migration0019BalanceSnapshotDedupTests(TransactionTestCase):
    def test_colliding_display_names_deduped_on_backfill(self):
        call_command("flush", interactive=False, verbosity=0)
        call_command("migrate", "finance", "0018_revoke_export_share_tokens", verbosity=0)

        executor = MigrationExecutor(connection)
        apps_0018 = executor.loader.project_state(
            [("finance", "0018_revoke_export_share_tokens")]
        ).apps

        PaymentSourceH = apps_0018.get_model("finance", "PaymentSource")
        BalanceSnapshotH = apps_0018.get_model("finance", "BalanceSnapshot")

        uid = str(uuid.uuid4())
        PaymentSourceH.objects.create(
            uid=uid,
            source="Checking",
            acc_type="CHECKING",
            amount=Decimal("100.00"),
            currency="USD",
        )
        snap_date = date(2026, 3, 1)
        BalanceSnapshotH.objects.create(
            uid=uid,
            source="Checking",
            snapshot_date=snap_date,
            closing_balance=Decimal("10.00"),
            currency="USD",
        )
        BalanceSnapshotH.objects.create(
            uid=uid,
            source="checking",
            snapshot_date=snap_date,
            closing_balance=Decimal("20.00"),
            currency="USD",
        )

        call_command("migrate", "finance", "0019_payment_source_source_id", verbosity=0)

        source_id = PaymentSource.objects.get(uid=uid).source_id
        rows = list(BalanceSnapshot.objects.filter(uid=uid, snapshot_date=snap_date))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].source, source_id)

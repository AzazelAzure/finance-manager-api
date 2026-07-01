from datetime import date, timedelta
from decimal import Decimal

from django.core.management import call_command
from django.utils import timezone

from finance.logic.balance_snapshots import closing_balances_as_of, persist_snapshots_for_date
from finance.models import BalanceSnapshot, PaymentSource
from finance.tasks.balance_snapshots import capture_balance_snapshots
from finance.tests.basetest import BaseTestCase
from finance.tests.test_celery_task_registration import CeleryBeatTaskRegistrationTests


class BalanceSnapshotPopulationTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.uid = str(self.profile.user_id)
        self.tx_url = "/finance/transactions/"

    def test_closing_balance_from_transactions(self):
        source = PaymentSource.objects.for_user(self.uid).first()
        source.amount = Decimal("0.00")
        source.save(update_fields=["amount"])
        payload = {
            "date": "2026-01-10",
            "description": "paycheck",
            "amount": "100.00",
            "source": source.source,
            "currency": source.currency,
            "tx_type": "INCOME",
            "tags": [],
            "category": self.categories[0].name,
        }
        resp = self.client.post(self.tx_url, payload, format="json")
        self.assertEqual(resp.status_code, 201)

        balances, _ = closing_balances_as_of(self.uid, date(2026, 1, 10))
        self.assertEqual(balances[source.source_id], Decimal("100.00"))

    def test_persist_snapshots_idempotent(self):
        source = PaymentSource.objects.for_user(self.uid).first()
        snapshot_date = date(2026, 1, 15)
        BalanceSnapshot.objects.create(
            uid=self.uid,
            source=source.source_id,
            snapshot_date=snapshot_date,
            closing_balance=Decimal("10.00"),
            currency=source.currency,
        )
        written = persist_snapshots_for_date(self.uid, snapshot_date)
        self.assertGreaterEqual(written, 1)
        self.assertEqual(
            BalanceSnapshot.objects.for_user(self.uid).filter(snapshot_date=snapshot_date).count(),
            PaymentSource.objects.for_user(self.uid).count(),
        )

    def test_backfill_command_writes_rows(self):
        source = PaymentSource.objects.for_user(self.uid).first()
        today = timezone.now().date()
        payload = {
            "date": today.isoformat(),
            "description": "seed",
            "amount": "25.00",
            "source": source.source,
            "currency": source.currency,
            "tx_type": "INCOME",
            "tags": [],
            "category": self.categories[0].name,
        }
        self.client.post(self.tx_url, payload, format="json")
        call_command("backfill_balance_snapshots", uid=self.uid, days=1)
        self.assertTrue(
            BalanceSnapshot.objects.for_user(self.uid).filter(snapshot_date=today).exists(),
        )

    def test_capture_balance_snapshots_task_runs(self):
        result = capture_balance_snapshots()
        self.assertTrue(str(result).startswith("snapshots:"))

    def test_capture_balance_snapshots_registered_in_beat(self):
        CeleryBeatTaskRegistrationTests().test_all_beat_scheduled_tasks_are_registered()

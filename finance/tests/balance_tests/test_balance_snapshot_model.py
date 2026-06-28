from datetime import date
from decimal import Decimal

from django.db import IntegrityError

from finance.models import BalanceSnapshot
from finance.tests.basetest import BaseTestCase


class BalanceSnapshotModelTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.uid = str(self.profile.user_id)

    def test_create_balance_snapshot(self):
        row = BalanceSnapshot.objects.create(
            uid=self.uid,
            source="checking",
            snapshot_date=date(2026, 1, 15),
            closing_balance=Decimal("1500.00"),
            currency="PHP",
        )
        self.assertEqual(row.closing_balance, Decimal("1500.00"))
        self.assertEqual(row.currency, "PHP")

    def test_unique_constraint_per_user_source_day(self):
        BalanceSnapshot.objects.create(
            uid=self.uid,
            source="checking",
            snapshot_date=date(2026, 1, 15),
            closing_balance=Decimal("100.00"),
            currency="USD",
        )
        with self.assertRaises(IntegrityError):
            BalanceSnapshot.objects.create(
                uid=self.uid,
                source="checking",
                snapshot_date=date(2026, 1, 15),
                closing_balance=Decimal("200.00"),
                currency="USD",
            )

    def test_for_user_and_date_range_filters(self):
        BalanceSnapshot.objects.create(
            uid=self.uid,
            source="cash",
            snapshot_date=date(2026, 1, 10),
            closing_balance=Decimal("50.00"),
            currency="USD",
        )
        BalanceSnapshot.objects.create(
            uid=self.uid,
            source="cash",
            snapshot_date=date(2026, 1, 20),
            closing_balance=Decimal("75.00"),
            currency="USD",
        )
        BalanceSnapshot.objects.create(
            uid="other-user",
            source="cash",
            snapshot_date=date(2026, 1, 15),
            closing_balance=Decimal("999.00"),
            currency="USD",
        )

        rows = list(
            BalanceSnapshot.objects.for_user(self.uid).in_date_range(
                date(2026, 1, 1),
                date(2026, 1, 15),
            )
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].closing_balance, Decimal("50.00"))

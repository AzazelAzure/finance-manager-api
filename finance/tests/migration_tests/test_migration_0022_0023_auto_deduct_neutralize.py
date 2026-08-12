"""Migration 0022/0023 — neutralize auto-deduct unique gate (HFM-AD-1 amend)."""

import uuid
from datetime import date
from decimal import Decimal

from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


INDEX_NAME = "unique_auto_deduct_bill_date_per_user"


def _index_names(table: str = "finance_transaction") -> set[str]:
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, table)
    return set(constraints.keys())


def _create_partial_unique_index(table: str = "finance_transaction") -> None:
    """Recreate the physical index the *original* 0022 AddConstraint produced."""
    if connection.vendor == "sqlite":
        sql = (
            f'CREATE UNIQUE INDEX "{INDEX_NAME}" ON "{table}" '
            f'("uid", "bill", "date") '
            f"WHERE \"auto_deducted\" AND \"bill\" IS NOT NULL AND \"bill\" != ''"
        )
    else:
        # Postgres: Django emits a partial unique index for conditional UniqueConstraint.
        sql = (
            f'CREATE UNIQUE INDEX "{INDEX_NAME}" ON "{table}" '
            f'("uid", "bill", "date") '
            f"WHERE (auto_deducted AND NOT ((bill = NULL OR bill = '')))"
        )
    with connection.cursor() as cursor:
        cursor.execute(sql)


class Migration00220023AutoDeductNeutralizeTests(TransactionTestCase):
    def test_fresh_migrate_allows_historical_auto_deduct_dups(self):
        """Edited 0022 has no audit/AddConstraint; historical dups survive through 0023."""
        call_command("flush", interactive=False, verbosity=0)
        call_command("migrate", "finance", "0021_dashboard_layout", verbosity=0)

        executor = MigrationExecutor(connection)
        apps_0021 = executor.loader.project_state(
            [("finance", "0021_dashboard_layout")]
        ).apps
        TransactionH = apps_0021.get_model("finance", "Transaction")

        uid = str(uuid.uuid4())
        tx_date = date(2026, 8, 1)
        shared = {
            "uid": uid,
            "date": tx_date,
            "created_on": tx_date,
            "description": "hist-dup",
            "amount": Decimal("-10.00"),
            "source": "src-mig",
            "currency": "USD",
            "tx_type": "EXPENSE",
            "category": "Bills",
            "tags": [],
            "bill": "mig-dup-bill",
            "auto_deducted": True,
        }
        TransactionH.objects.create(tx_id=f"{tx_date.isoformat()}-MIG1", **shared)
        TransactionH.objects.create(tx_id=f"{tx_date.isoformat()}-MIG2", **shared)

        call_command(
            "migrate",
            "finance",
            "0023_remove_auto_deduct_business_key_unique",
            verbosity=0,
        )

        from finance.models import Transaction

        rows = list(
            Transaction.objects.filter(
                uid=uid, bill="mig-dup-bill", date=tx_date, auto_deducted=True
            )
        )
        self.assertEqual(len(rows), 2)
        self.assertNotIn(INDEX_NAME, _index_names())

    def test_old_0022_cohort_drops_physical_index_preserves_rows(self):
        """Simulate old-0022 physical index via raw SQL, then apply 0023."""
        call_command("flush", interactive=False, verbosity=0)
        call_command(
            "migrate",
            "finance",
            "0023_remove_auto_deduct_business_key_unique",
            verbosity=0,
        )

        from finance.models import Transaction

        uid = str(uuid.uuid4())
        tx_date = date(2026, 8, 2)
        Transaction.objects.create(
            uid=uid,
            tx_id=f"{tx_date.isoformat()}-OLD1",
            date=tx_date,
            created_on=tx_date,
            description="old-cohort",
            amount=Decimal("-5.00"),
            source="src-old",
            currency="USD",
            tx_type="EXPENSE",
            category="Bills",
            tags=[],
            bill="old-cohort-bill",
            auto_deducted=True,
        )

        _create_partial_unique_index()
        self.assertIn(INDEX_NAME, _index_names())

        # Fake "0023 pending": remove migration record, keep physical index, re-apply.
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM django_migrations WHERE app = %s AND name = %s",
                ["finance", "0023_remove_auto_deduct_business_key_unique"],
            )
        MigrationExecutor(connection).loader.build_graph()

        call_command(
            "migrate",
            "finance",
            "0023_remove_auto_deduct_business_key_unique",
            verbosity=0,
        )

        self.assertNotIn(INDEX_NAME, _index_names())
        self.assertEqual(
            Transaction.objects.filter(uid=uid, bill="old-cohort-bill").count(),
            1,
        )

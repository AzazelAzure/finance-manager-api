from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db import connection
from django.test import TransactionTestCase
from django.urls import reverse
from rest_framework.test import APIClient

from finance.models import Category, PaymentSource, Tag, Transaction, UpcomingExpense


class ConcurrencyIntegrityTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        if connection.vendor == "sqlite":
            self.skipTest("Concurrency integrity stress checks require PostgreSQL")
        self.user = User.objects.create_user(
            username="stress_integrity_user",
            email="stress_integrity_user@example.com",
            password="StressPass123!",
        )
        self.uid = str(self.user.appprofile.user_id)
        self.source = PaymentSource.objects.create(
            uid=self.uid,
            source="integrity-cash",
            acc_type="CASH",
            amount=Decimal("1000.00"),
            currency="USD",
        )
        self.category = Category.objects.create(uid=self.uid, name="integrity-cat")
        self.tag = Tag.objects.create(uid=self.uid, tags=["integrity-tag"])
        self.expense = UpcomingExpense.objects.create(
            uid=self.uid,
            name="integrity-bill",
            amount=Decimal("35.00"),
            due_date=date.today(),
            start_date=date.today(),
            currency="USD",
            paid_flag=False,
            is_recurring=True,
        )
        self.tx = Transaction.objects.create(
            uid=self.uid,
            tx_id=f"{date.today().isoformat()}-integrity-1",
            date=date.today(),
            created_on=date.today(),
            description="integrity seed tx",
            amount=Decimal("10.00"),
            source=self.source.source,
            currency="USD",
            tx_type="EXPENSE",
            category=self.category.name,
            tags=["integrity-tag"],
            bill=self.expense.name,
        )
        self.tx_detail_url = reverse("transaction_detail_update_delete", kwargs={"tx_id": self.tx.tx_id})

    def _client(self) -> APIClient:
        client = APIClient()
        client.force_authenticate(user=self.user)
        return client

    def test_concurrent_source_create_has_single_row(self):
        source_name = "integrity-contention-source"

        def create_same_source():
            try:
                PaymentSource.objects.create(
                    uid=self.uid,
                    source=source_name,
                    acc_type="CASH",
                    amount=Decimal("1.00"),
                    currency="USD",
                )
                return "created"
            except IntegrityError:
                return "integrity_error"

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda _: create_same_source(), range(16)))

        self.assertEqual(PaymentSource.objects.filter(uid=self.uid, source=source_name).count(), 1)

    def test_concurrent_transaction_updates_keep_single_transaction(self):
        def patch_tx(i: int):
            payload = {
                "date": str(date.today()),
                "description": f"patched-{i}",
                "amount": "11.00",
                "source": self.source.source,
                "currency": "USD",
                "tx_type": "EXPENSE",
                "category": self.category.name,
                "tags": ["integrity-tag"],
            }
            response = self._client().patch(self.tx_detail_url, payload, format="json")
            return response.status_code

        with ThreadPoolExecutor(max_workers=10) as pool:
            statuses = list(pool.map(patch_tx, range(20)))

        self.assertTrue(any(code == 200 for code in statuses))
        self.assertEqual(Transaction.objects.filter(uid=self.uid, tx_id=self.tx.tx_id).count(), 1)

    def test_delete_source_during_transaction_writes_has_no_orphan_sources(self):
        contender = PaymentSource.objects.create(
            uid=self.uid,
            source="integrity-contention-src",
            acc_type="CASH",
            amount=Decimal("150.00"),
            currency="USD",
        )

        def create_tx(i: int):
            payload = {
                "date": str(date.today()),
                "description": f"concurrent-create-{i}",
                "amount": "3.50",
                "source": contender.source,
                "currency": "USD",
                "tx_type": "EXPENSE",
                "category": self.category.name,
                "tags": ["integrity-tag"],
            }
            return self._client().post(reverse("transactions_list_create"), payload, format="json").status_code

        def delete_source():
            return self._client().delete(reverse("sources"), {"source": contender.source}, format="json").status_code

        with ThreadPoolExecutor(max_workers=8) as pool:
            statuses = list(pool.map(create_tx, range(12)))
            statuses.append(delete_source())

        valid_sources = set(PaymentSource.objects.filter(uid=self.uid).values_list("source", flat=True))
        for tx_source in Transaction.objects.filter(uid=self.uid).values_list("source", flat=True):
            self.assertIn(tx_source, valid_sources)
        self.assertTrue(any(code in {200, 201} for code in statuses))

    def test_snapshot_endpoint_stable_after_burst_contention(self):
        category_url = reverse("category_detail_update_delete", kwargs={"cat_name": self.category.name})
        expense_url = reverse("upcoming_expense_detail_update_delete", kwargs={"name": self.expense.name})

        def mutate_category(i: int):
            return self._client().patch(category_url, {"name": f"integrity-cat-{i}"}, format="json").status_code

        def mutate_expense(i: int):
            return self._client().patch(expense_url, {"paid_flag": bool(i % 2)}, format="json").status_code

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(mutate_category, range(6)))
            list(pool.map(mutate_expense, range(6)))

        snapshot_response = self._client().get(reverse("appprofile_snapshot"))
        self.assertEqual(snapshot_response.status_code, 200)
        self.assertIn("snapshot", snapshot_response.data)

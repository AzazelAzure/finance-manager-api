from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.contrib.auth.models import User
from django.db import connection, connections
from django.test import TransactionTestCase
from django.urls import reverse
from rest_framework.test import APIClient

from finance.logic.fincalc import Calculator
from finance.models import AppProfile, Category, PaymentSource, Transaction, UpcomingExpense


def _require_postgres(test_case) -> None:
    if connection.vendor == "postgresql":
        return
    if os.environ.get("REQUIRE_POSTGRES") == "1":
        test_case.fail(
            f"REQUIRE_POSTGRES=1 but Django vendor is {connection.vendor}, not postgresql"
        )
    test_case.skipTest("Source-amount integrity checks require PostgreSQL")


class SourceAmountIntegrityTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        _require_postgres(self)
        self.user = User.objects.create_user(
            username="src_amt_integrity_user",
            email="src_amt_integrity_user@example.com",
            password="StressPass123!",
        )
        self.uid = str(self.user.appprofile.user_id)
        self.source = PaymentSource.objects.create(
            uid=self.uid,
            source="integrity-cash",
            acc_type="CASH",
            amount=Decimal("1000.00"),
            opening_amount=Decimal("1000.00"),
            currency="USD",
        )
        self.category = Category.objects.create(uid=self.uid, name="integrity-cat")
        self.tx_url = reverse("transactions_list_create")
        self.snapshot_url = reverse("appprofile_snapshot")
        self.rebuild_url = reverse("sources_balance_rebuild")

    def _client(self) -> APIClient:
        client = APIClient()
        client.force_authenticate(user=self.user)
        return client

    def _expense_payload(self, description: str, amount: str, **extra) -> dict:
        payload = {
            "date": str(date.today()),
            "description": description,
            "amount": amount,
            "source": self.source.source,
            "currency": "USD",
            "tx_type": "EXPENSE",
            "category": self.category.name,
        }
        payload.update(extra)
        return payload

    def _ledger_invariant(self, source: PaymentSource) -> tuple[Decimal, Decimal]:
        profile = AppProfile.objects.for_user(self.uid)
        fc = Calculator(profile=profile)
        ledger = fc.ledger_sum_for_source(source)
        expected = (Decimal(source.opening_amount or 0) + ledger).quantize(Decimal("0.01"))
        return expected, ledger

    def test_concurrent_dual_pwa_expenses_keep_both_in_amount(self):
        def post_one(item):
            desc, amount, key = item
            try:
                response = self._client().post(
                    self.tx_url,
                    self._expense_payload(desc, amount),
                    format="json",
                    HTTP_IDEMPOTENCY_KEY=key,
                )
                return response.status_code
            finally:
                connections.close_all()

        jobs = [
            ("dual-a", "10.00", "key-dual-a"),
            ("dual-b", "20.00", "key-dual-b"),
        ]
        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(post_one, jobs))

        self.assertTrue(all(code == 201 for code in statuses), statuses)
        self.assertEqual(
            Transaction.objects.filter(uid=self.uid, description__in=["dual-a", "dual-b"]).count(),
            2,
        )
        self.source.refresh_from_db()
        expected, _ = self._ledger_invariant(self.source)
        self.assertEqual(self.source.amount, expected)
        self.assertEqual(self.source.amount, Decimal("970.00"))

    def test_same_idempotency_key_twice_is_one_updater_effect(self):
        payload = self._expense_payload("same-key", "15.00")
        first = self._client().post(
            self.tx_url, payload, format="json", HTTP_IDEMPOTENCY_KEY="same-key-once"
        )
        second = self._client().post(
            self.tx_url, payload, format="json", HTTP_IDEMPOTENCY_KEY="same-key-once"
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(Transaction.objects.filter(uid=self.uid, description="same-key").count(), 1)
        self.source.refresh_from_db()
        expected, _ = self._ledger_invariant(self.source)
        self.assertEqual(self.source.amount, expected)
        self.assertEqual(self.source.amount, Decimal("985.00"))

    def test_patch_and_delete_match_full_ledger_recompute(self):
        created = self._client().post(
            self.tx_url,
            self._expense_payload("patch-me", "40.00"),
            format="json",
            HTTP_IDEMPOTENCY_KEY="patch-me-key",
        )
        self.assertEqual(created.status_code, 201)
        tx_id = created.data["accepted"][0]["tx_id"]
        detail = reverse("transaction_detail", kwargs={"tx_id": tx_id})
        patched = self._client().patch(
            detail,
            {"amount": "25.00", "source": self.source.source, "tx_type": "EXPENSE"},
            format="json",
        )
        self.assertEqual(patched.status_code, 200)
        self.source.refresh_from_db()
        expected, _ = self._ledger_invariant(self.source)
        self.assertEqual(self.source.amount, expected)
        deleted = self._client().delete(detail)
        self.assertEqual(deleted.status_code, 200)
        self.source.refresh_from_db()
        expected, _ = self._ledger_invariant(self.source)
        self.assertEqual(self.source.amount, expected)
        self.assertEqual(self.source.amount, Decimal("1000.00"))

    def test_snapshot_get_repairs_drifted_amount_opening_unchanged(self):
        created = self._client().post(
            self.tx_url,
            self._expense_payload("drift-seed", "30.00"),
            format="json",
            HTTP_IDEMPOTENCY_KEY="drift-seed-key",
        )
        self.assertEqual(created.status_code, 201)
        self.source.refresh_from_db()
        opening_before = self.source.opening_amount
        self.source.amount = Decimal("4054.00")
        self.source.save(update_fields=["amount"])
        response = self._client().get(self.snapshot_url)
        self.assertEqual(response.status_code, 200)
        self.source.refresh_from_db()
        self.assertEqual(self.source.opening_amount, opening_before)
        expected, ledger = self._ledger_invariant(self.source)
        self.assertEqual(self.source.amount, expected)
        cash_row = next(
            row for row in response.data["source_balances"] if row["source"] == self.source.source
        )
        self.assertEqual(Decimal(cash_row["amount"]), expected)
        self.assertEqual(Decimal(cash_row["opening_amount"]), opening_before)
        self.assertEqual(Decimal(cash_row["transaction_sum"]), ledger)

    def test_source_amount_patch_vs_concurrent_tx_post_keeps_invariant(self):
        source_url = reverse("source_detail_update_delete", kwargs={"source": self.source.source})

        def patch_amount():
            try:
                return self._client().patch(
                    source_url, {"amount": "2000.00"}, format="json"
                ).status_code
            finally:
                connections.close_all()

        def post_tx():
            try:
                return self._client().post(
                    self.tx_url,
                    self._expense_payload("race-tx", "10.00"),
                    format="json",
                    HTTP_IDEMPOTENCY_KEY="race-tx-key",
                ).status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(lambda fn: fn(), [patch_amount, post_tx]))
        self.assertTrue(all(code in {200, 201} for code in statuses), statuses)
        self.source.refresh_from_db()
        expected, _ = self._ledger_invariant(self.source)
        self.assertEqual(self.source.amount, expected)

    def test_same_bill_two_non_ad_txs_advance_due_date_once(self):
        due = date.today()
        bill = UpcomingExpense.objects.create(
            uid=self.uid,
            name="integrity-bill",
            amount=Decimal("35.00"),
            due_date=due,
            start_date=due,
            currency="USD",
            paid_flag=False,
            is_recurring=True,
        )

        def post_bill_tx(item):
            desc, key = item
            try:
                return self._client().post(
                    self.tx_url,
                    self._expense_payload(desc, "35.00", bill=bill.name),
                    format="json",
                    HTTP_IDEMPOTENCY_KEY=key,
                ).status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(post_bill_tx, [("bill-a", "bill-a-key"), ("bill-b", "bill-b-key")]))
        self.assertTrue(all(code == 201 for code in statuses), statuses)
        bill.refresh_from_db()
        self.assertEqual(bill.due_date, due + relativedelta(months=1))

    def test_rebuild_get_is_read_only_and_flags_unexplained(self):
        created = self._client().post(
            self.tx_url,
            self._expense_payload("rebuild-seed", "50.00"),
            format="json",
            HTTP_IDEMPOTENCY_KEY="rebuild-seed-key",
        )
        self.assertEqual(created.status_code, 201)
        self.source.refresh_from_db()
        amount_before = self.source.amount
        opening_before = self.source.opening_amount
        self.source.amount = Decimal("4054.00")
        self.source.save(update_fields=["amount"])
        response = self._client().get(self.rebuild_url)
        self.assertEqual(response.status_code, 200)
        self.source.refresh_from_db()
        self.assertEqual(self.source.amount, Decimal("4054.00"))
        self.assertEqual(self.source.opening_amount, opening_before)
        row = next(r for r in response.data["sources"] if r["source"] == self.source.source)
        unexplained = abs(Decimal(row["unexplained"]))
        self.assertGreater(unexplained, Decimal("0.01"))
        current_vs_sum = abs(Decimal(row["current_amount"]) - Decimal(row["transaction_sum"]))
        self.assertGreater(current_vs_sum, Decimal("0.01"))
        self.assertEqual(Decimal(row["proposed_amount"]), Decimal(row["transaction_sum"]))
        self.assertNotEqual(amount_before, Decimal("4054.00"))

    def test_rebuild_post_applies_proposed_and_second_get_is_clean(self):
        created = self._client().post(
            self.tx_url,
            self._expense_payload("rebuild-apply", "50.00"),
            format="json",
            HTTP_IDEMPOTENCY_KEY="rebuild-apply-key",
        )
        self.assertEqual(created.status_code, 201)
        self.source.amount = Decimal("4054.00")
        self.source.save(update_fields=["amount"])
        preview = self._client().get(self.rebuild_url)
        row = next(r for r in preview.data["sources"] if r["source"] == self.source.source)
        leftover = Decimal("100.00")
        proposed = Decimal(row["transaction_sum"]) + leftover
        applied = self._client().post(
            self.rebuild_url,
            {"sources": [{"source": self.source.source, "proposed_amount": str(proposed)}]},
            format="json",
        )
        self.assertEqual(applied.status_code, 200, applied.data)
        self.source.refresh_from_db()
        self.assertEqual(self.source.amount, proposed)
        expected, ledger = self._ledger_invariant(self.source)
        self.assertEqual(self.source.amount, expected)
        self.assertEqual(self.source.opening_amount, leftover)
        self.assertEqual(ledger, Decimal(row["transaction_sum"]))
        second = self._client().get(self.rebuild_url)
        clean = next(r for r in second.data["sources"] if r["source"] == self.source.source)
        self.assertEqual(abs(Decimal(clean["unexplained"])), Decimal("0.00"))

    def test_rebuild_post_refuses_unknown_source_name(self):
        response = self._client().post(
            self.rebuild_url,
            {"sources": [{"source": "not-a-real-source", "proposed_amount": "10.00"}]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

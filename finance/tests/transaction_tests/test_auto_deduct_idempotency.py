"""HFM-AD-1 amend: auto-deduct accepted|replace + soft first-wins (no unique constraint)."""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.db import IntegrityError
from rest_framework import status

from finance.models import PaymentSource, Transaction, UpcomingExpense
from finance.services import transaction_services
from finance.tests.transaction_tests.transaction_base import TransactionBase


class AutoDeductIdempotencyTests(TransactionBase):
    def _create_bill(self, name: str) -> UpcomingExpense:
        return UpcomingExpense.objects.create(
            uid=str(self.profile.user_id),
            name=name,
            amount=Decimal("50.00"),
            due_date=date.today(),
            start_date=date.today(),
            currency=self.profile.base_currency,
            is_recurring=True,
            auto_deduct=True,
            paid_flag=False,
        )

    def _auto_deduct_payload(self, bill_name: str, *, amount: str = "25.00", description: str = "ad") -> dict:
        source = PaymentSource.objects.for_user(self.profile.user_id).first()
        return {
            "date": str(date.today()),
            "description": description,
            "amount": amount,
            "source": source.source,
            "currency": source.currency,
            "tags": [self.tag_list[0]],
            "tx_type": "EXPENSE",
            "category": self.categories[0].name,
            "bill": bill_name,
            "auto_deducted": True,
        }

    def test_auto_deduct_duplicate_create_converges_to_winner(self):
        """Service/API convergence: second create returns same winner (no second row)."""
        bill_name = "ad1-constraint-bill"
        self._create_bill(bill_name)
        first = self.client.post(
            self.url,
            self._auto_deduct_payload(bill_name, amount="25.00", description="winner"),
            format="json",
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED, msg=first.data)
        winner_id = first.data["accepted"][0]["tx_id"]
        self.assertEqual(first.data["accepted"][0]["auto_deduct_resolution"], "accepted")

        second = self.client.post(
            self.url,
            self._auto_deduct_payload(bill_name, amount="99.00", description="later"),
            format="json",
        )
        self.assertEqual(second.status_code, status.HTTP_201_CREATED, msg=second.data)
        self.assertEqual(second.data["accepted"][0]["tx_id"], winner_id)
        self.assertEqual(second.data["accepted"][0]["auto_deduct_resolution"], "replace")
        self.assertEqual(
            Transaction.objects.for_user(self.profile.user_id)
            .filter(bill=bill_name, date=date.today(), auto_deducted=True)
            .count(),
            1,
        )

    def test_bulk_duplicate_keys_first_wins_stable_order(self):
        bill_name = "ad1-bulk-dup-bill"
        self._create_bill(bill_name)
        item_a = self._auto_deduct_payload(bill_name, amount="25.00", description="first")
        item_b = self._auto_deduct_payload(bill_name, amount="99.00", description="dup")
        response = self.client.post(self.url, [item_a, item_b], format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, msg=response.data)
        accepted = response.data["accepted"]
        self.assertEqual(len(accepted), 2)
        self.assertEqual(accepted[0]["tx_id"], accepted[1]["tx_id"])
        self.assertEqual(accepted[0]["description"], "first")
        self.assertEqual(accepted[1]["description"], "first")
        self.assertEqual(accepted[0]["auto_deduct_resolution"], "accepted")
        self.assertEqual(accepted[1]["auto_deduct_resolution"], "replace")
        self.assertEqual(
            Transaction.objects.for_user(self.profile.user_id)
            .filter(bill=bill_name, date=date.today(), auto_deducted=True)
            .count(),
            1,
        )

    def test_mixed_bulk_new_and_duplicate_updater_once(self):
        bill_dup = "ad1-mixed-dup"
        bill_new = "ad1-mixed-new"
        self._create_bill(bill_dup)
        self._create_bill(bill_new)

        source = PaymentSource.objects.for_user(self.profile.user_id).first()
        source.refresh_from_db()
        balance_before = Decimal(str(source.amount))

        # Seed an existing winner for bill_dup via API (updater runs once).
        seed = self.client.post(
            self.url,
            self._auto_deduct_payload(bill_dup, amount="10.00", description="seed"),
            format="json",
        )
        self.assertEqual(seed.status_code, status.HTTP_201_CREATED, msg=seed.data)
        seed_tx_id = seed.data["accepted"][0]["tx_id"]
        self.assertEqual(seed.data["accepted"][0]["auto_deduct_resolution"], "accepted")
        source.refresh_from_db()
        balance_after_seed = Decimal(str(source.amount))
        self.assertNotEqual(balance_before, balance_after_seed)

        # Bulk: [new key, duplicate of seed key] — updater only for the new key.
        bulk = [
            self._auto_deduct_payload(bill_new, amount="10.00", description="brand-new"),
            self._auto_deduct_payload(bill_dup, amount="10.00", description="should-reuse"),
        ]
        response = self.client.post(self.url, bulk, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, msg=response.data)
        accepted = response.data["accepted"]
        self.assertEqual(len(accepted), 2)
        self.assertEqual(accepted[0]["description"], "brand-new")
        self.assertEqual(accepted[0]["auto_deduct_resolution"], "accepted")
        self.assertEqual(accepted[1]["tx_id"], seed_tx_id)
        self.assertEqual(accepted[1]["auto_deduct_resolution"], "replace")
        self.assertNotEqual(accepted[0]["tx_id"], accepted[1]["tx_id"])

        source.refresh_from_db()
        # Exactly one additional 10.00 expense applied (the new key), not two.
        delta = balance_after_seed - Decimal(str(source.amount))
        # Expense amounts are stored negative; source balance drops by converted amount.
        # Same currency as source → expect exactly 10.00 debit for the new key only.
        self.assertEqual(delta, Decimal("10.00"))

        self.assertEqual(
            Transaction.objects.for_user(self.profile.user_id)
            .filter(bill=bill_dup, date=date.today(), auto_deducted=True)
            .count(),
            1,
        )
        self.assertEqual(
            Transaction.objects.for_user(self.profile.user_id)
            .filter(bill=bill_new, date=date.today(), auto_deducted=True)
            .count(),
            1,
        )

    def test_integrity_error_recovery_path_returns_winner(self):
        """Simulate race: fast-path miss, then IntegrityError → re-fetch winner + replace."""
        bill_name = "ad1-ie-recovery"
        self._create_bill(bill_name)
        first = self.client.post(
            self.url,
            self._auto_deduct_payload(bill_name, amount="12.00", description="winner"),
            format="json",
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED, msg=first.data)
        winner_id = first.data["accepted"][0]["tx_id"]

        source = PaymentSource.objects.for_user(self.profile.user_id).first()
        source.refresh_from_db()
        balance_after_first = Decimal(str(source.amount))

        real_resolve = transaction_services._resolve_auto_deduct_row
        call_count = {"n": 0}

        def resolve_miss_then_hit(uid, bill, tx_date):
            call_count["n"] += 1
            # First call in _create_transaction_row: pretend no row exists yet.
            if call_count["n"] == 1:
                return None
            return real_resolve(uid, bill, tx_date)

        def create_raise_ie(**kwargs):
            raise IntegrityError("simulated unique_auto_deduct race")

        with patch.object(
            transaction_services,
            "_resolve_auto_deduct_row",
            side_effect=resolve_miss_then_hit,
        ), patch.object(Transaction.objects, "create", side_effect=create_raise_ie):
            second = self.client.post(
                self.url,
                self._auto_deduct_payload(bill_name, amount="12.00", description="racer"),
                format="json",
            )
        self.assertEqual(second.status_code, status.HTTP_201_CREATED, msg=second.data)
        self.assertEqual(second.data["accepted"][0]["tx_id"], winner_id)
        self.assertEqual(second.data["accepted"][0]["auto_deduct_resolution"], "replace")
        self.assertGreaterEqual(call_count["n"], 2)

        self.assertEqual(
            Transaction.objects.for_user(self.profile.user_id)
            .filter(bill=bill_name, date=date.today(), auto_deducted=True)
            .count(),
            1,
        )
        source.refresh_from_db()
        self.assertEqual(Decimal(str(source.amount)), balance_after_first)

    def test_non_auto_deduct_omits_resolution_field(self):
        source = PaymentSource.objects.for_user(self.profile.user_id).first()
        payload = {
            "date": str(date.today()),
            "description": "plain",
            "amount": "5.00",
            "source": source.source,
            "currency": source.currency,
            "tags": [self.tag_list[0]],
            "tx_type": "EXPENSE",
            "category": self.categories[0].name,
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, msg=response.data)
        self.assertNotIn("auto_deduct_resolution", response.data["accepted"][0])

    def test_blank_bill_auto_deducted_not_constrained(self):
        """Blank-bill auto_deducted rows omit resolution and may coexist."""
        source = PaymentSource.objects.for_user(self.profile.user_id).first()
        today = date.today()
        kwargs = {
            "uid": str(self.profile.user_id),
            "date": today,
            "created_on": today,
            "description": "no-bill",
            "amount": Decimal("-1.00"),
            "source": source.source_id,
            "currency": source.currency,
            "tx_type": "EXPENSE",
            "category": self.categories[0].name,
            "tags": [],
            "bill": "",
            "auto_deducted": True,
        }
        Transaction.objects.create(tx_id=f"{today.isoformat()}-BLANK1", **kwargs)
        # Second row with blank bill must not raise (outside soft-key predicate).
        Transaction.objects.create(tx_id=f"{today.isoformat()}-BLANK2", **kwargs)

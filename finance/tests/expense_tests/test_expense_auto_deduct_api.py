from datetime import date
from decimal import Decimal
from django.urls import reverse
from rest_framework import status

from finance.logic.source_linkage import load_source_maps, resolve_name_to_id
from finance.models import PaymentSource, Transaction, UpcomingExpense
from finance.tests.expense_tests.expense_base import ExpenseBase
from finance.tests.transaction_tests.transaction_base import TransactionBase


class UpcomingExpenseAutoDeductApiTests(ExpenseBase):
    def _source_display_name(self) -> str:
        source = PaymentSource.objects.for_user(self.profile.user_id).first()
        return source.source

    def test_create_defaults_auto_deduct_false_and_null_source(self):
        payload = dict(self.expense_payload)
        payload["name"] = "defaults-bill"
        response = self.create_expense(payload)
        accepted = response.data["accepted"][0]
        self.assertFalse(accepted.get("auto_deduct", False))
        self.assertIsNone(accepted.get("source"))

        row = UpcomingExpense.objects.for_user(self.profile.user_id).get(name="defaults-bill")
        self.assertFalse(row.auto_deduct)
        self.assertIsNone(row.source)

    def test_create_round_trips_auto_deduct_and_source(self):
        source_name = self._source_display_name()
        payload = dict(self.expense_payload)
        payload["name"] = "auto-deduct-bill"
        payload["auto_deduct"] = True
        payload["source"] = source_name
        response = self.create_expense(payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, msg=response.data)
        accepted = response.data["accepted"][0]
        self.assertTrue(accepted["auto_deduct"])
        self.assertEqual(accepted["source"], source_name)

        maps = load_source_maps(self.profile.user_id)
        row = UpcomingExpense.objects.for_user(self.profile.user_id).get(name="auto-deduct-bill")
        self.assertTrue(row.auto_deduct)
        self.assertEqual(row.source, resolve_name_to_id(source_name.lower(), maps))

    def test_get_list_round_trips_auto_deduct_and_source(self):
        source_name = self._source_display_name()
        payload = dict(self.expense_payload)
        payload["name"] = "list-round-trip"
        payload["auto_deduct"] = True
        payload["source"] = source_name
        self.create_expense(payload)

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        match = next(e for e in response.data["expenses"] if e["name"] == "list-round-trip")
        self.assertTrue(match["auto_deduct"])
        self.assertEqual(match["source"], source_name)

    def test_patch_round_trips_auto_deduct_and_source(self):
        self.create_expense()
        source_name = self._source_display_name()
        response = self.client.patch(
            self.detail_url("rent"),
            {"auto_deduct": True, "source": source_name},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.data)
        updated = response.data["updated"][0]
        self.assertTrue(updated["auto_deduct"])
        self.assertEqual(updated["source"], source_name)

        get_response = self.client.get(self.detail_url("rent"))
        expense = get_response.data["expense"]
        self.assertTrue(expense["auto_deduct"])
        self.assertEqual(expense["source"], source_name)

    def test_patch_clears_source_with_null(self):
        source_name = self._source_display_name()
        payload = dict(self.expense_payload)
        payload["name"] = "clear-source-bill"
        payload["source"] = source_name
        self.create_expense(payload)

        response = self.client.patch(
            self.detail_url("clear-source-bill"),
            {"source": None},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.data)
        row = UpcomingExpense.objects.for_user(self.profile.user_id).get(name="clear-source-bill")
        self.assertIsNone(row.source)

    def test_create_rejects_unknown_source(self):
        payload = dict(self.expense_payload)
        payload["name"] = "bad-source-bill"
        payload["source"] = "nonexistent-account"
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_allows_source_without_auto_deduct(self):
        source_name = self._source_display_name()
        payload = dict(self.expense_payload)
        payload["name"] = "source-only-bill"
        payload["source"] = source_name
        response = self.create_expense(payload)
        accepted = response.data["accepted"][0]
        self.assertFalse(accepted["auto_deduct"])
        self.assertEqual(accepted["source"], source_name)


class TransactionAutoDeductedTests(TransactionBase):
    def test_transaction_defaults_auto_deducted_false(self):
        response = self.client.post(self.url, self.expense_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, msg=response.data)
        accepted = response.data["accepted"][0]
        self.assertFalse(accepted.get("auto_deducted", False))

        tx = Transaction.objects.for_user(self.profile.user_id).get(tx_id=accepted["tx_id"])
        self.assertFalse(tx.auto_deducted)

    def test_transaction_create_sets_auto_deducted_true(self):
        payload = dict(self.expense_data)
        payload["auto_deducted"] = True
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, msg=response.data)
        accepted = response.data["accepted"][0]
        self.assertTrue(accepted["auto_deducted"])

        tx = Transaction.objects.for_user(self.profile.user_id).get(tx_id=accepted["tx_id"])
        self.assertTrue(tx.auto_deducted)

    def test_transaction_get_includes_auto_deducted(self):
        payload = dict(self.expense_data)
        payload["auto_deducted"] = True
        create_response = self.client.post(self.url, payload, format="json")
        tx_id = create_response.data["accepted"][0]["tx_id"]

        detail_response = self.client.get(
            reverse("transaction_detail", kwargs={"tx_id": tx_id})
        )
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertTrue(detail_response.data["transaction"]["auto_deducted"])

    def _create_auto_deduct_bill(self, name: str) -> None:
        UpcomingExpense.objects.create(
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

    def test_sequential_dual_key_auto_deduct_returns_same_winner(self):
        """HFM-AD-1: different Idempotency-Keys, same bill+date+auto_deducted → one row."""
        import uuid

        bill_name = "ad1-dual-key-bill"
        self._create_auto_deduct_bill(bill_name)
        source = PaymentSource.objects.for_user(self.profile.user_id).first()
        payment_date = str(date.today())
        payload = {
            "date": payment_date,
            "description": "auto-deduct payment",
            "amount": "25.00",
            "source": source.source,
            "currency": source.currency,
            "tags": [self.tag_list[0]],
            "tx_type": "EXPENSE",
            "category": self.categories[0].name,
            "bill": bill_name,
            "auto_deducted": True,
        }

        source.refresh_from_db()
        balance_before_first = Decimal(str(source.amount))

        r1 = self.client.post(
            self.url,
            payload,
            format="json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED, msg=r1.data)
        winner_id = r1.data["accepted"][0]["tx_id"]
        self.assertEqual(r1.data["accepted"][0]["auto_deduct_resolution"], "accepted")

        source.refresh_from_db()
        balance_after_first = Decimal(str(source.amount))
        self.assertNotEqual(balance_before_first, balance_after_first)

        bill = UpcomingExpense.objects.for_user(self.profile.user_id).get(name=bill_name)
        due_after_first = bill.due_date

        r2 = self.client.post(
            self.url,
            payload,
            format="json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        self.assertEqual(r2.status_code, status.HTTP_201_CREATED, msg=r2.data)
        self.assertEqual(r2.data["accepted"][0]["tx_id"], winner_id)
        self.assertEqual(r2.data["accepted"][0]["auto_deduct_resolution"], "replace")

        matching = Transaction.objects.for_user(self.profile.user_id).filter(
            bill=bill_name,
            date=date.today(),
            auto_deducted=True,
        )
        self.assertEqual(matching.count(), 1)

        source.refresh_from_db()
        self.assertEqual(Decimal(str(source.amount)), balance_after_first)

        bill.refresh_from_db()
        self.assertEqual(bill.due_date, due_after_first)
from django.urls import reverse
from rest_framework import status

from finance.models import BalanceSnapshot, PaymentSource, SavingsGoal, Transaction
from finance.tests.source_tests.source_base import SourceBase
from datetime import date
from decimal import Decimal


class SourcePatchTestCase(SourceBase):
    def test_patch_rename_source_to_new_unique_name(self):
        expected = self.seed_source("patch-rename")
        url = reverse("source_detail_update_delete", kwargs={"source": expected["source"]})
        response = self.client.patch(url, {"source": "patch-rename-updated"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["updated"]["source"], "patch-rename-updated")

    def test_patch_rename_source_to_existing_name_rejected(self):
        original = self.seed_source("patch-rename-original")
        self.seed_source("patch-rename-existing")
        url = reverse("source_detail_update_delete", kwargs={"source": original["source"]})
        response = self.client.patch(url, {"source": "patch-rename-existing"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_partial_single_field(self):
        expected = self.seed_source("patch-source")
        url = reverse("source_detail_update_delete", kwargs={"source": expected["source"]})
        response = self.client.patch(url, {"acc_type": "savings"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["updated"]["acc_type"], "SAVINGS")

    def test_patch_partial_multiple_fields(self):
        expected = self.seed_source("patch-multi")
        url = reverse("source_detail_update_delete", kwargs={"source": expected["source"]})
        payload = {"acc_type": "checking", "currency": "eur"}
        response = self.client.patch(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["updated"]["acc_type"], "CHECKING")
        self.assertEqual(response.data["updated"]["currency"], "EUR")

    def test_patch_invalid_payload_rejected(self):
        expected = self.seed_source("patch-invalid")
        url = reverse("source_detail_update_delete", kwargs={"source": expected["source"]})
        response = self.client.patch(url, {"amount": "oops"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_unknown_forbidden(self):
        url = reverse("source_detail_update_delete", kwargs={"source": "unknown"})
        response = self.client.patch(url, {"acc_type": "cash"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_nonexistent_source_rejected(self):
        url = reverse("source_detail_update_delete", kwargs={"source": "does-not-exist"})
        response = self.client.patch(url, {"acc_type": "cash"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_rename_transaction_linkage_survives(self):
        expected = self.seed_source("link-tx")
        ps = PaymentSource.objects.for_user(self.profile.user_id).get_by_source(expected["source"]).first()
        tx_payload = {
            "date": "2024-01-01",
            "description": "linkage tx",
            "amount": "10.00",
            "source": expected["source"],
            "currency": expected["currency"],
            "tx_type": "EXPENSE",
            "tags": [],
            "category": self.categories[0].name,
        }
        tx_resp = self.client.post(reverse("transactions_list_create"), tx_payload, format="json")
        self.assertEqual(tx_resp.status_code, status.HTTP_201_CREATED)
        tx_id = tx_resp.data["accepted"][0]["tx_id"]

        patch_url = reverse("source_detail_update_delete", kwargs={"source": expected["source"]})
        self.assertEqual(
            self.client.patch(patch_url, {"source": "link-tx-renamed"}, format="json").status_code,
            status.HTTP_200_OK,
        )

        tx = Transaction.objects.for_user(self.profile.user_id).get(tx_id=tx_id)
        self.assertEqual(tx.source, ps.source_id)
        get_resp = self.client.get(reverse("transaction_detail", kwargs={"tx_id": tx_id}))
        self.assertEqual(get_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(get_resp.data["transaction"]["source"], "link-tx-renamed")

    def test_patch_rename_balance_snapshot_linkage_survives(self):
        expected = self.seed_source("link-balance")
        ps = PaymentSource.objects.for_user(self.profile.user_id).get_by_source(expected["source"]).first()
        BalanceSnapshot.objects.create(
            uid=str(self.profile.user_id),
            source=ps.source_id,
            snapshot_date=date(2026, 3, 1),
            closing_balance=Decimal("42.00"),
            currency=expected["currency"],
        )

        patch_url = reverse("source_detail_update_delete", kwargs={"source": expected["source"]})
        self.assertEqual(
            self.client.patch(patch_url, {"source": "link-balance-renamed"}, format="json").status_code,
            status.HTTP_200_OK,
        )

        resp = self.client.get(
            reverse("balance_history"),
            {"source": "link-balance-renamed", "start_date": "2026-01-01", "end_date": "2026-12-31"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["series"]), 1)
        self.assertEqual(resp.data["series"][0]["source"], "link-balance-renamed")

    def test_patch_rename_savings_goal_linkage_survives(self):
        expected = self.seed_source("link-goal")
        goal_resp = self.client.post(
            reverse("savings_goals"),
            {
                "name": "Rename goal",
                "target_amount": "500.00",
                "target_date": "2027-01-01",
                "source": expected["source"],
            },
            format="json",
        )
        self.assertEqual(goal_resp.status_code, status.HTTP_201_CREATED)
        goal_id = goal_resp.data["id"]

        patch_url = reverse("source_detail_update_delete", kwargs={"source": expected["source"]})
        self.assertEqual(
            self.client.patch(patch_url, {"source": "link-goal-renamed"}, format="json").status_code,
            status.HTTP_200_OK,
        )

        detail = self.client.get(reverse("savings_goal_detail", kwargs={"pk": goal_id}))
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(detail.data["source"], "link-goal-renamed")
        goal = SavingsGoal.objects.get(pk=goal_id)
        ps = PaymentSource.objects.for_user(self.profile.user_id).get_by_source("link-goal-renamed").first()
        self.assertEqual(goal.source, ps.source_id)

    def test_patch_rename_spend_accounts_linkage_survives(self):
        expected = self.seed_source("link-spend")
        ps = PaymentSource.objects.for_user(self.profile.user_id).get_by_source(expected["source"]).first()
        cash = PaymentSource.objects.for_user(self.profile.user_id).get_by_source("cash").first()
        patch_profile = self.client.patch(
            reverse("appprofile"),
            {"spend_accounts": ["cash", expected["source"]]},
            format="json",
        )
        self.assertEqual(patch_profile.status_code, status.HTTP_200_OK)

        patch_url = reverse("source_detail_update_delete", kwargs={"source": expected["source"]})
        self.assertEqual(
            self.client.patch(patch_url, {"source": "link-spend-renamed"}, format="json").status_code,
            status.HTTP_200_OK,
        )

        info = self.client.get(reverse("appprofile"))
        self.assertEqual(info.status_code, status.HTTP_200_OK)
        self.assertIn("link-spend-renamed", info.data["spend_accounts"])
        self.profile.refresh_from_db()
        self.assertIn(ps.source_id, self.profile.spend_accounts)
        self.assertIn(cash.source_id, self.profile.spend_accounts)

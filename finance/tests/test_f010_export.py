import json

from datetime import date
from decimal import Decimal

from django.urls import reverse
from rest_framework import status

from finance.factories import TransactionFactory
from finance.models import PaymentSource, Transaction
from finance.tests.user_tests.user_base import UserBase


class TransactionCsvExportTests(UserBase):
    def setUp(self):
        super().setUp()
        self.url = reverse("export_tx_csv")
        PaymentSource.objects.filter(uid=str(self.profile.user_id), source="cash").update(
            source=f"cash-{self.profile.user_id}"
        )
        PaymentSource.objects.filter(uid=str(self.profile.user_id), source="unknown").update(
            source=f"unknown-{self.profile.user_id}"
        )
        self.own_source = PaymentSource.objects.filter(uid=str(self.profile.user_id)).first()
        self.own_tx = TransactionFactory.create(
            uid=str(self.profile.user_id),
            date=date(2025, 6, 15),
            created_on=date(2025, 6, 15),
            tx_id="2025-06-15-OWNCSV01",
            source=self.own_source.source if self.own_source else "wallet",
            currency="USD",
            tx_type="EXPENSE",
            amount=Decimal("42.50"),
            category="groceries",
            tags=["food", "weekly"],
            description="Weekly shop",
            bill="rent",
        )

    def test_csv_download_own_data(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("text/csv", resp["Content-Type"])
        self.assertIn("attachment", resp["Content-Disposition"])
        body = b"".join(resp.streaming_content).decode("utf-8")
        lines = body.strip().splitlines()
        self.assertEqual(
            lines[0],
            "Date,Amount,Currency,Source,Category,Tags,Notes,Linked Bill",
        )
        self.assertIn("2025-06-15", body)
        self.assertIn("42.50", body)
        self.assertIn("food|weekly", body)
        self.assertIn("Weekly shop", body)
        self.assertIn("rent", body)

    def test_csv_cross_user_isolation(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        body = b"".join(resp.streaming_content).decode("utf-8")
        self.assertNotIn("OTHERTX1", body)
        self.assertNotIn("other-wallet", body)

    def test_csv_date_filter(self):
        TransactionFactory.create(
            uid=str(self.profile.user_id),
            date=date(2024, 1, 1),
            created_on=date(2024, 1, 1),
            tx_id="2024-01-01-OLDCV001",
            source=self.own_source.source if self.own_source else "wallet",
            currency="USD",
            tx_type="EXPENSE",
            amount=Decimal("1.00"),
            tags=[],
        )
        resp = self.client.get(
            self.url,
            {"date_from": "2025-01-01", "date_to": "2025-12-31"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        body = b"".join(resp.streaming_content).decode("utf-8")
        self.assertIn("2025-06-15", body)
        self.assertNotIn("2024-01-01", body)

    def test_csv_unauthenticated(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_csv_empty(self):
        Transaction.objects.filter(uid=str(self.profile.user_id)).delete()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        body = b"".join(resp.streaming_content).decode("utf-8").strip()
        self.assertEqual(
            body,
            "Date,Amount,Currency,Source,Category,Tags,Notes,Linked Bill",
        )

    def test_csv_invalid_date_from(self):
        resp = self.client.get(self.url, {"date_from": "not-a-date"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class FullBackupExportTests(UserBase):
    def setUp(self):
        super().setUp()
        self.url = reverse("export_full_backup")

    def test_full_backup_structure(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("application/json", resp["Content-Type"])
        self.assertIn("attachment", resp["Content-Disposition"])
        payload = json.loads(resp.content)
        self.assertEqual(payload["export_version"], "1")
        self.assertIn("exported_at", payload)
        for key in ("profile", "sources", "categories", "tags", "transactions", "upcoming_expenses"):
            self.assertIn(key, payload)
        self.assertEqual(str(self.profile.user_id), payload["profile"]["user_id"])
        self.assertNotIn("password", payload["profile"])
        self.assertNotIn("email", payload["profile"])

    def test_full_backup_cross_user_isolation(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        payload = json.loads(resp.content)
        body = json.dumps(payload)
        self.assertNotIn(self.other_uid, body.replace(str(self.profile.user_id), ""))
        self.assertNotIn("OTHERTX1", body)
        self.assertNotIn("other-bill", body)
        self.assertNotIn("other-cat", body)
        self.assertNotIn("other-tag", body)
        self.assertNotIn("other-wallet", body)

    def test_full_backup_unauthenticated(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class ShareTokenExportTests(UserBase):
    def setUp(self):
        super().setUp()
        self.create_url = reverse("share_token_create")
        PaymentSource.objects.filter(uid=str(self.profile.user_id), source="cash").update(
            source=f"cash-{self.profile.user_id}"
        )
        PaymentSource.objects.filter(uid=str(self.profile.user_id), source="unknown").update(
            source=f"unknown-{self.profile.user_id}"
        )
        own_source = PaymentSource.objects.filter(uid=str(self.profile.user_id)).first()
        TransactionFactory.create(
            uid=str(self.profile.user_id),
            date=date(2025, 6, 15),
            created_on=date(2025, 6, 15),
            tx_id="2025-06-15-SHARETX1",
            source=own_source.source if own_source else "wallet",
            currency="USD",
            tx_type="EXPENSE",
            amount=Decimal("12.00"),
            tags=[],
        )

    def _create_token(self, expires_in_days=7):
        resp = self.client.post(self.create_url, {"expires_in_days": expires_in_days}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        return resp.data

    def test_share_token_create(self):
        data = self._create_token()
        self.assertIn("token", data)
        self.assertIn("expires_at", data)

    def test_share_token_access_valid(self):
        token = self._create_token()["token"]
        self.client.force_authenticate(user=None)
        access_url = reverse("share_token_access", kwargs={"token": token})
        resp = self.client.get(access_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsNone(resp.data["shared_by"])
        tx_ids = [row["tx_id"] for row in resp.data["transactions"]]
        self.assertIn("2025-06-15-SHARETX1", tx_ids)
        self.assertNotIn("OTHERTX1", tx_ids)

    def test_share_token_access_expired(self):
        from django.utils import timezone

        from finance.models import ExportShareToken

        share = ExportShareToken.objects.create(
            uid=self.profile,
            expires_at=timezone.now() - timezone.timedelta(days=1),
        )
        self.client.force_authenticate(user=None)
        access_url = reverse("share_token_access", kwargs={"token": str(share.token)})
        resp = self.client.get(access_url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_share_token_access_revoked(self):
        token = self._create_token()["token"]
        revoke_url = reverse("share_token_revoke", kwargs={"token": token})
        revoke_resp = self.client.delete(revoke_url)
        self.assertEqual(revoke_resp.status_code, status.HTTP_204_NO_CONTENT)
        self.client.force_authenticate(user=None)
        access_url = reverse("share_token_access", kwargs={"token": token})
        resp = self.client.get(access_url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_share_token_cross_user(self):
        token = self._create_token()["token"]
        self.client.force_authenticate(user=None)
        access_url = reverse("share_token_access", kwargs={"token": token})
        resp = self.client.get(access_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        tx_ids = [row["tx_id"] for row in resp.data["transactions"]]
        self.assertNotIn("OTHERTX1", tx_ids)

    def test_share_token_revoke_wrong_owner(self):
        token = self._create_token()["token"]
        self.client.force_authenticate(user=self.other_user)
        revoke_url = reverse("share_token_revoke", kwargs={"token": token})
        resp = self.client.delete(revoke_url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

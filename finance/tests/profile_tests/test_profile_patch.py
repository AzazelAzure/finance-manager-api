from decimal import Decimal

from finance.models import PaymentSource
from finance.tests.profile_tests.profile_base import ProfileBase


class AppProfilePatchTests(ProfileBase):
    def test_patch_updates_spend_accounts_and_base_currency(self):
        src = PaymentSource.objects.create(
            uid=str(self.profile.user_id),
            source="wallet-main",
            acc_type="EWALLET",
            amount=Decimal("50.00"),
            currency="USD",
        )
        payload = {
            "spend_accounts": ["cash", src.source],
            "base_currency": "EUR",
            "timezone": "UTC",
            "start_week": 0,
        }
        response = self.client.patch(self.profile_url, payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("message", response.data)
        self.assertIn("snapshot", response.data)

        self.profile.refresh_from_db()
        self.assertEqual(sorted(self.profile.spend_accounts), sorted(["cash", "wallet-main"]))
        self.assertEqual(self.profile.base_currency, "EUR")
        self.assertEqual(self.profile.timezone, "UTC")
        self.assertEqual(self.profile.start_of_week, 0)

    def test_patch_rejects_unknown_spend_account(self):
        response = self.client.patch(
            self.profile_url,
            {"spend_accounts": ["does-not-exist"]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_patch_rejects_unknown_default_source(self):
        response = self.client.patch(
            self.profile_url,
            {"spend_accounts": ["unknown"]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

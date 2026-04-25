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

    def test_patch_timezone_asia_manila_preserves_iana_casing(self):
        """Regression: timezone must not be .upper()'d (breaks zoneinfo, e.g. ASIA/MANILA)."""
        response = self.client.patch(
            self.profile_url,
            {"timezone": "Asia/Manila"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, msg=response.data)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.timezone, "Asia/Manila")

    def test_patch_timezone_case_insensitive_normalizes(self):
        response = self.client.patch(
            self.profile_url,
            {"timezone": "asia/manila"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, msg=response.data)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.timezone, "Asia/Manila")

    def test_patch_rejects_non_iana_timezone_abbreviation(self):
        response = self.client.patch(
            self.profile_url,
            {"timezone": "PHT"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

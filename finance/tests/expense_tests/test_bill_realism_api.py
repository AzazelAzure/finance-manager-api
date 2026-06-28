from datetime import date
from decimal import Decimal

from finance.tests.expense_tests.expense_base import ExpenseBase
from finance.tests.profile_tests.profile_base import ProfileBase


class AppProfilePayCycleApiTests(ProfileBase):
    def test_get_includes_pay_cycle_defaults(self):
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["sts_window_mode"], "calendar_month")
        self.assertIsNone(response.data["pay_cycle_frequency"])
        self.assertIsNone(response.data["pay_cycle_anchor_date"])

    def test_patch_pay_cycle_requires_frequency_and_anchor(self):
        response = self.client.patch(
            self.profile_url,
            {"sts_window_mode": "pay_cycle"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_patch_pay_cycle_round_trip(self):
        payload = {
            "sts_window_mode": "pay_cycle",
            "pay_cycle_frequency": "biweekly",
            "pay_cycle_anchor_date": "2026-07-15",
        }
        response = self.client.patch(self.profile_url, payload, format="json")
        self.assertEqual(response.status_code, 200, msg=response.data)
        get_resp = self.client.get(self.profile_url)
        self.assertEqual(get_resp.data["sts_window_mode"], "pay_cycle")
        self.assertEqual(get_resp.data["pay_cycle_frequency"], "biweekly")
        self.assertEqual(get_resp.data["pay_cycle_anchor_date"], "2026-07-15")


class ExpenseBillRealismApiTests(ExpenseBase):
    def test_post_expense_with_partial_pay_fields(self):
        payload = {
            "name": "electric-partial",
            "amount": "2000.00",
            "currency": self.currency,
            "due_date": str(date.today()),
            "bill_class": "volatile",
            "planned_partial_amount": "1200.00",
            "cycle_residual_amount": "800.00",
            "remainder_due_date": "2026-08-01",
        }
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, 201, msg=response.data)
        accepted = response.data["accepted"][0]
        self.assertEqual(accepted["bill_class"], "volatile")
        self.assertEqual(Decimal(str(accepted["planned_partial_amount"])), Decimal("1200.00"))

    def test_post_rejects_partial_above_amount(self):
        payload = {
            "name": "bad-partial",
            "amount": "500.00",
            "currency": self.currency,
            "due_date": str(date.today()),
            "planned_partial_amount": "600.00",
        }
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, 400)

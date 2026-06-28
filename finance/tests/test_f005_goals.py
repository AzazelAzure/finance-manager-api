from datetime import date, timedelta
from decimal import Decimal

from django.urls import reverse
from rest_framework import status

from finance.factories import PaymentSourceFactory
from finance.models import PaymentSource, SavingsGoal
from finance.tests.user_tests.user_base import UserBase
from finance.views.goal_views import compute_per_cycle_required


class SavingsGoalApiTests(UserBase):
    def setUp(self):
        super().setUp()
        self.list_url = reverse("savings_goals")
        self.profile.pay_cycle_frequency = "monthly"
        self.profile.save(update_fields=["pay_cycle_frequency"])
        PaymentSource.objects.filter(uid=str(self.profile.user_id), source="cash").update(
            source=f"cash-{self.profile.user_id}"
        )
        PaymentSource.objects.filter(uid=str(self.profile.user_id), source="unknown").update(
            source=f"unknown-{self.profile.user_id}"
        )
        self.own_source = PaymentSource.objects.filter(uid=str(self.profile.user_id)).first()

    def _create_goal(self, **overrides):
        payload = {
            "name": "Emergency fund",
            "target_amount": "1200.00",
            "target_date": (date.today() + timedelta(days=365)).isoformat(),
        }
        payload.update(overrides)
        return self.client.post(self.list_url, payload, format="json")

    def test_goal_create_defaults_currency(self):
        resp = self._create_goal()
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["currency"], self.profile.base_currency)

    def test_goal_list_includes_per_cycle(self):
        self._create_goal()
        resp = self.client.get(self.list_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertIn("per_cycle_required", resp.data[0])
        Decimal(resp.data[0]["per_cycle_required"])

    def test_per_cycle_math_monthly(self):
        goal = SavingsGoal.objects.create(
            uid=self.profile,
            name="Monthly save",
            target_amount=Decimal("1200.00"),
            currency="USD",
            target_date=date.today() + timedelta(days=365),
            current_amount=Decimal("0"),
        )
        per_cycle = compute_per_cycle_required(goal, self.profile)
        self.assertEqual(per_cycle, Decimal("100.00"))

    def test_per_cycle_past_due(self):
        goal = SavingsGoal.objects.create(
            uid=self.profile,
            name="Past due",
            target_amount=Decimal("500.00"),
            currency="USD",
            target_date=date.today() - timedelta(days=1),
            current_amount=Decimal("100.00"),
        )
        per_cycle = compute_per_cycle_required(goal, self.profile)
        self.assertEqual(per_cycle, Decimal("400.00"))

    def test_per_cycle_already_met(self):
        goal = SavingsGoal.objects.create(
            uid=self.profile,
            name="Done",
            target_amount=Decimal("500.00"),
            currency="USD",
            target_date=date.today() + timedelta(days=30),
            current_amount=Decimal("500.00"),
        )
        per_cycle = compute_per_cycle_required(goal, self.profile)
        self.assertEqual(per_cycle, Decimal("0"))

    def test_cross_user_isolation(self):
        create_resp = self._create_goal()
        goal_id = create_resp.data["id"]
        detail_url = reverse("savings_goal_detail", kwargs={"pk": goal_id})

        self.client.force_authenticate(user=self.other_user)
        self.assertEqual(self.client.get(detail_url).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            self.client.patch(detail_url, {"name": "Hacked"}, format="json").status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(self.client.delete(detail_url).status_code, status.HTTP_404_NOT_FOUND)

        self.client.force_authenticate(user=self.user)
        self.assertEqual(SavingsGoal.objects.filter(pk=goal_id).count(), 1)

    def test_partial_update(self):
        create_resp = self._create_goal()
        goal_id = create_resp.data["id"]
        detail_url = reverse("savings_goal_detail", kwargs={"pk": goal_id})
        before = Decimal(create_resp.data["per_cycle_required"])

        patch_resp = self.client.patch(
            detail_url,
            {"current_amount": "600.00"},
            format="json",
        )
        self.assertEqual(patch_resp.status_code, status.HTTP_200_OK)
        after = Decimal(patch_resp.data["per_cycle_required"])
        self.assertLess(after, before)

    def test_create_rejects_foreign_source(self):
        PaymentSourceFactory.create(
            uid=self.other_uid,
            source="other-savings",
            acc_type="SAVINGS",
            amount=Decimal("50.00"),
            currency="USD",
        )
        resp = self._create_goal(source="other-savings")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_rejects_negative_amounts(self):
        neg_target = self._create_goal(target_amount="-100.00")
        self.assertEqual(neg_target.status_code, status.HTTP_400_BAD_REQUEST)
        neg_current = self._create_goal(current_amount="-5.00")
        self.assertEqual(neg_current.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_rejects_null_or_blank_name(self):
        null_name = self.client.post(
            self.list_url,
            {"name": None, "target_amount": "100.00", "target_date": (date.today() + timedelta(days=30)).isoformat()},
            format="json",
        )
        self.assertEqual(null_name.status_code, status.HTTP_400_BAD_REQUEST)
        blank_name = self._create_goal(name="   ")
        self.assertEqual(blank_name.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_rejects_negative_amount(self):
        goal_id = self._create_goal().data["id"]
        detail_url = reverse("savings_goal_detail", kwargs={"pk": goal_id})
        resp = self.client.patch(detail_url, {"current_amount": "-1.00"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_per_cycle_rounds_up_small_remainder(self):
        goal = SavingsGoal.objects.create(
            uid=self.profile,
            name="Tiny remainder",
            target_amount=Decimal("100.001"),
            currency="USD",
            target_date=date.today() + timedelta(days=3650),
            current_amount=Decimal("100.00"),
        )
        per_cycle = compute_per_cycle_required(goal, self.profile)
        self.assertEqual(per_cycle, Decimal("0.01"))

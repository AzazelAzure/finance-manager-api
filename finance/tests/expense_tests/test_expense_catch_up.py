from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from django.urls import reverse
from rest_framework import status

from finance.models import UpcomingExpense
from finance.tests.expense_tests.expense_base import ExpenseBase


class ExpenseCatchUpTestCase(ExpenseBase):
    def catch_up_url(self, name: str):
        return reverse("upcoming_expense_catch_up", kwargs={"name": name})

    def test_one_time_bill_marked_paid_on_linked_transaction(self):
        payload = dict(self.expense_payload)
        payload["name"] = "utilities"
        payload["is_recurring"] = False
        self.create_expense(payload)
        self.create_linked_expense_transaction("utilities")
        row = UpcomingExpense.objects.for_user(self.profile.user_id).get(name="utilities")
        self.assertTrue(row.paid_flag)

    def test_catch_up_advances_recurring_overdue_bill(self):
        payload = dict(self.expense_payload)
        payload["name"] = "internet-overdue"
        payload["due_date"] = str(date.today() - timedelta(days=45))
        payload["start_date"] = str(date.today() - timedelta(days=75))
        payload["is_recurring"] = True
        self.create_expense(payload)

        response = self.client.post(self.catch_up_url("internet-overdue"), {"periods": 1}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.data)

        row = UpcomingExpense.objects.for_user(self.profile.user_id).get(name="internet-overdue")
        self.assertFalse(row.paid_flag)
        self.assertGreaterEqual(row.due_date, date.today() - timedelta(days=30))

    def test_catch_up_caps_at_24_periods(self):
        payload = dict(self.expense_payload)
        payload["name"] = "ancient-bill"
        payload["due_date"] = str(date.today() - relativedelta(years=3))
        payload["start_date"] = str(date.today() - relativedelta(years=3, months=1))
        payload["is_recurring"] = True
        self.create_expense(payload)

        response = self.client.post(self.catch_up_url("ancient-bill"), {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.data)
        self.assertLessEqual(response.data["periods_advanced"], 24)

from datetime import date
from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase

from finance.factories import UserFactory
from finance.models import UpcomingExpense


class UpcomingExpenseBillRealismFieldTests(TestCase):
    def setUp(self):
        self.uid = str(UserFactory().appprofile.user_id)

    def test_new_expense_defaults_to_rigid_without_partial(self):
        expense = UpcomingExpense.objects.create(
            uid=self.uid,
            name="rent",
            amount=Decimal("15000.00"),
            currency="PHP",
        )
        expense.refresh_from_db()
        self.assertEqual(expense.bill_class, UpcomingExpense.BillClass.RIGID)
        self.assertIsNone(expense.planned_partial_amount)
        self.assertIsNone(expense.cycle_residual_amount)
        self.assertIsNone(expense.remainder_due_date)

    def test_partial_pay_fields_persist(self):
        expense = UpcomingExpense.objects.create(
            uid=self.uid,
            name="electric",
            amount=Decimal("2000.00"),
            currency="PHP",
            bill_class=UpcomingExpense.BillClass.VOLATILE,
            planned_partial_amount=Decimal("1200.00"),
            cycle_residual_amount=Decimal("800.00"),
            remainder_due_date=date(2026, 8, 1),
        )
        expense.refresh_from_db()
        self.assertEqual(expense.bill_class, UpcomingExpense.BillClass.VOLATILE)
        self.assertEqual(expense.planned_partial_amount, Decimal("1200.00"))
        self.assertEqual(expense.cycle_residual_amount, Decimal("800.00"))
        self.assertEqual(expense.remainder_due_date, date(2026, 8, 1))

    def test_planned_partial_amount_cannot_exceed_bill_total(self):
        with self.assertRaises(IntegrityError):
            UpcomingExpense.objects.create(
                uid=self.uid,
                name="water",
                amount=Decimal("500.00"),
                currency="PHP",
                planned_partial_amount=Decimal("600.00"),
            )

from decimal import Decimal

from django.urls import reverse
from rest_framework import status

from finance.models import UpcomingExpense
from finance.tests.transaction_tests.transaction_base import TransactionBase


class TransactionVisualizationTestCase(TransactionBase):
    def setUp(self):
        super().setUp()
        self.visualization_url = reverse("transactions_visualization")

    def _create_tx(self, *, tx_date: str, amount: str, tx_type: str, source: str, currency: str, category: str) -> None:
        payload = {
            "date": tx_date,
            "description": f"viz-{tx_type.lower()}",
            "amount": amount,
            "source": source,
            "currency": currency,
            "tx_type": tx_type,
            "category": category,
            "tags": [],
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, msg=response.data)

    def test_visualization_packets_include_transaction_and_expense_aggregates(self):
        source = self.sources[0].source
        currency = self.sources[0].currency
        category = self.categories[0].name

        self._create_tx(
            tx_date="2026-04-01",
            amount="100.00",
            tx_type="INCOME",
            source=source,
            currency=currency,
            category=category,
        )
        self._create_tx(
            tx_date="2026-04-01",
            amount="25.00",
            tx_type="EXPENSE",
            source=source,
            currency=currency,
            category=category,
        )
        self._create_tx(
            tx_date="2026-04-02",
            amount="10.00",
            tx_type="XFER_OUT",
            source=source,
            currency=currency,
            category=category,
        )

        UpcomingExpense.objects.create(
            uid=str(self.profile.user_id),
            name="Rent",
            amount=Decimal("900.00"),
            due_date="2026-04-05",
            currency="USD",
            paid_flag=False,
            is_recurring=True,
        )
        UpcomingExpense.objects.create(
            uid=str(self.profile.user_id),
            name="Gym",
            amount=Decimal("35.00"),
            due_date="2026-04-10",
            currency="USD",
            paid_flag=True,
            is_recurring=True,
        )

        response = self.client.get(
            self.visualization_url,
            {"start_date": "2026-04-01", "end_date": "2026-04-30"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.data)
        payload = response.data

        flow_by_day = {row["date"]: row for row in payload["flow_daily"]}
        self.assertEqual(Decimal(str(flow_by_day["2026-04-01"]["income"])), Decimal("100.00"))
        self.assertEqual(Decimal(str(flow_by_day["2026-04-01"]["expense"])), Decimal("25.00"))
        self.assertEqual(Decimal(str(flow_by_day["2026-04-01"]["net"])), Decimal("75.00"))
        self.assertEqual(flow_by_day["2026-04-01"]["tx_count"], 2)
        self.assertEqual(Decimal(str(flow_by_day["2026-04-02"]["expense"])), Decimal("10.00"))

        tx_totals = {row["tx_type"]: Decimal(str(row["amount"])) for row in payload["tx_type_totals"]}
        self.assertEqual(tx_totals["INCOME"], Decimal("100.00"))
        self.assertEqual(tx_totals["EXPENSE"], Decimal("25.00"))
        self.assertEqual(tx_totals["XFER_OUT"], Decimal("10.00"))

        top_categories = {row["category"]: Decimal(str(row["amount"])) for row in payload["top_expense_categories"]}
        self.assertEqual(top_categories[category], Decimal("25.00"))

        status_packet = payload["upcoming_expenses_status"]
        self.assertEqual(status_packet["paid_count"], 1)
        self.assertEqual(status_packet["unpaid_count"], 1)
        self.assertEqual(Decimal(str(status_packet["paid_amount"])), Decimal("35.00"))
        self.assertEqual(Decimal(str(status_packet["unpaid_amount"])), Decimal("900.00"))

        monthly = {row["period"]: row for row in payload["upcoming_expenses_monthly"]}
        self.assertEqual(Decimal(str(monthly["2026-04-01"]["amount"])), Decimal("935.00"))
        self.assertEqual(monthly["2026-04-01"]["expense_count"], 2)

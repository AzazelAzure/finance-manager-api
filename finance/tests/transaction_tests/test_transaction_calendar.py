from datetime import date
from decimal import Decimal

from django.urls import reverse
from rest_framework import status

from finance.tests.transaction_tests.transaction_base import TransactionBase


class TransactionCalendarTestCase(TransactionBase):
    def setUp(self):
        super().setUp()
        self.calendar_url = reverse("transactions_calendar")

    def _create_tx(self, *, tx_date: str, amount: str, tx_type: str, source: str, currency: str, category: str) -> None:
        payload = {
            "date": tx_date,
            "description": f"calendar-{tx_type.lower()}",
            "amount": amount,
            "source": source,
            "currency": currency,
            "tx_type": tx_type,
            "category": category,
            "tags": [],
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, msg=response.data)

    def test_calendar_aggregates_include_month_boundaries(self):
        source = self.sources[0].source
        currency = self.sources[0].currency
        category = self.categories[0].name
        self._create_tx(
            tx_date="2026-03-31",
            amount="100.00",
            tx_type="EXPENSE",
            source=source,
            currency=currency,
            category=category,
        )
        self._create_tx(
            tx_date="2026-04-01",
            amount="75.00",
            tx_type="INCOME",
            source=source,
            currency=currency,
            category=category,
        )
        self._create_tx(
            tx_date="2026-04-01",
            amount="20.00",
            tx_type="EXPENSE",
            source=source,
            currency=currency,
            category=category,
        )

        response = self.client.get(
            self.calendar_url,
            {"start_date": "2026-03-31", "end_date": "2026-04-30"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.data)

        payload = response.data
        self.assertEqual(payload["start_date"], "2026-03-31")
        self.assertEqual(payload["end_date"], "2026-04-30")

        monthly = {row["period"]: Decimal(str(row["amount"])) for row in payload["monthly"]}
        self.assertEqual(monthly["2026-03-01"], Decimal("-100.00"))
        self.assertEqual(monthly["2026-04-01"], Decimal("55.00"))

        daily = {row["date"]: row for row in payload["daily"]}
        self.assertEqual(Decimal(str(daily["2026-03-31"]["amount"])), Decimal("-100.00"))
        self.assertEqual(daily["2026-03-31"]["tx_count"], 1)
        self.assertEqual(Decimal(str(daily["2026-04-01"]["amount"])), Decimal("55.00"))
        self.assertEqual(daily["2026-04-01"]["tx_count"], 2)

    def test_calendar_day_drill_defaults_to_start_date(self):
        source = self.sources[1].source
        currency = self.sources[1].currency
        category = self.categories[1].name
        self._create_tx(
            tx_date="2026-04-15",
            amount="33.00",
            tx_type="EXPENSE",
            source=source,
            currency=currency,
            category=category,
        )
        self._create_tx(
            tx_date="2026-04-16",
            amount="11.00",
            tx_type="INCOME",
            source=source,
            currency=currency,
            category=category,
        )

        response = self.client.get(
            self.calendar_url,
            {"start_date": "2026-04-15", "end_date": "2026-04-30"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.data)

        day_drill = response.data["day_drill"]
        self.assertEqual(len(day_drill), 1)
        self.assertEqual(day_drill[0]["date"], "2026-04-15")


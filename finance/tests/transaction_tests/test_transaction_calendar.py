from datetime import date
from decimal import Decimal

from django.urls import reverse
from rest_framework import status

from finance.tests.transaction_tests.transaction_base import TransactionBase
from finance.models import UpcomingExpense


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
        # Force the source onto the profile base currency so the calendar's
        # display-currency conversion is an identity. Otherwise a randomly
        # assigned weak currency can round a -100 expense to 0.00 and flake the
        # `assertLess(..., 0)` below.
        src_obj = self.sources[0]
        src_obj.currency = str(self.profile.base_currency).upper()
        src_obj.save(update_fields=["currency"])
        source = src_obj.source
        currency = src_obj.currency
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
        self.assertIn("2026-03-01", monthly)
        self.assertIn("2026-04-01", monthly)
        self.assertLess(monthly["2026-03-01"], Decimal("0"))
        self.assertGreater(monthly["2026-04-01"], Decimal("0"))

        daily = {row["date"]: row for row in payload["daily"]}
        self.assertEqual(daily["2026-03-31"]["tx_count"], 1)
        self.assertEqual(daily["2026-04-01"]["tx_count"], 2)
        april_sum = Decimal(str(daily["2026-04-01"]["amount"]))
        self.assertEqual(april_sum, monthly["2026-04-01"])

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

    def test_calendar_contract_includes_heatmap_and_due_events(self):
        source = self.sources[0].source
        currency = self.sources[0].currency
        category = self.categories[0].name
        self._create_tx(
            tx_date="2026-04-20",
            amount="42.00",
            tx_type="EXPENSE",
            source=source,
            currency=currency,
            category=category,
        )
        UpcomingExpense.objects.create(
            uid=str(self.profile.user_id),
            name="rent",
            amount=Decimal("650.00"),
            due_date=date(2026, 4, 20),
            currency=currency,
            paid_flag=False,
            is_recurring=True,
        )

        response = self.client.get(
            self.calendar_url,
            {
                "start_date": "2026-04-01",
                "end_date": "2026-04-30",
                "display_currency_mode": "original",
                "heat_metric_mode": "expense_only",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.data)
        payload = response.data
        self.assertEqual(payload["display_currency_mode"], "original")
        self.assertEqual(payload["heat_metric_mode"], "expense_only")
        self.assertIn("base_currency", payload)
        self.assertIn("heat_max", payload)
        self.assertEqual(len(payload["due_events"]), 1)
        self.assertEqual(payload["due_events"][0]["expense_name"], "rent")
        daily_row = payload["daily"][0]
        self.assertIn("heat_value", daily_row)
        self.assertIn("heat_intensity", daily_row)


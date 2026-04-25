"""
Tests for GET /finance/transactions/ (list + filters) and GET /finance/transactions/<tx_id>/ (single).
"""

from decimal import Decimal

from django.urls import reverse
from freezegun import freeze_time
from rest_framework import status

from finance.tests.transaction_tests.transaction_base import TransactionGetBase


class TransactionGetSingleTestCase(TransactionGetBase):
    """GET single transaction by path param tx_id."""

    def test_get_by_tx_id_returns_transaction_and_amount(self):
        """
        Detail GET returns transaction payload and amount (transaction_services.get_transaction).

        Passes if:
            - 200, body has transaction matching seeded id and amount matches stored tx.

        Fails if:
            - Wrong status, shape, or values.
        """
        url = reverse(
            "transaction_detail_update_delete",
            kwargs={"tx_id": self.income_tx_id},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("transaction", response.data)
        self.assertIn("amount", response.data)
        self.assertEqual(response.data["transaction"]["tx_id"], self.income_tx_id)
        self.assertEqual(response.data["transaction"]["tx_type"], "INCOME")
        self.assertEqual(
            Decimal(str(response.data["amount"])).quantize(Decimal("0.01")),
            Decimal(str(self.get_tx["income1"]["amount"])).quantize(Decimal("0.01")),
        )

    def test_get_by_nonexistent_tx_id_returns_400(self):
        url = reverse(
            "transaction_detail_update_delete",
            kwargs={"tx_id": "2099-01-01-NOSUCHTX"},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TransactionGetListDefaultTestCase(TransactionGetBase):
    """Default list behavior when no query params are sent."""

    def test_get_no_query_params_returns_latest_transaction_only(self):
        """
        With no filters, get_transactions uses get_latest (most recent by entry_id).

        Passes if:
            - One transaction returned and it is the last POST from seeding (exp_latest).

        Fails if:
            - Wrong count or wrong tx_id.
        """
        response = self.client.get(self.list_url)
        self.assert_get_list_shape(response, code=200)
        self.assertEqual(len(response.data["transactions"]), 1)
        self.assertEqual(response.data["transactions"][0]["tx_id"], self.latest_tx_id)


class TransactionGetFiltersTestCase(TransactionGetBase):
    """Each list filter query param is exercised against seeded data."""

    def test_filter_tx_type_expense(self):
        response = self.client.get(self.list_url, {"tx_type": "EXPENSE"})
        self.assert_get_list_shape(response)
        self.assert_all_tx_have_type(response, "EXPENSE")
        self.assertIn(self.latest_tx_id, {r["tx_id"] for r in response.data["transactions"]})

    def test_filter_tx_type_income(self):
        response = self.client.get(self.list_url, {"tx_type": "INCOME"})
        self.assert_get_list_shape(response)
        self.assert_all_tx_have_type(response, "INCOME")
        self.assertEqual(len(response.data["transactions"]), 1)
        self.assertEqual(response.data["transactions"][0]["tx_id"], self.income_tx_id)

    def test_filter_tag_name(self):
        response = self.client.get(self.list_url, {"tag_name": self.tag_list[1]})
        self.assert_get_list_shape(response)
        self.assertEqual(len(response.data["transactions"]), 1)
        self.assertEqual(response.data["transactions"][0]["tx_id"], self.tagged_expense_tx_id)

    def test_filter_category(self):
        response = self.client.get(self.list_url, {"category": self.reference_category})
        self.assert_get_list_shape(response)
        for row in response.data["transactions"]:
            self.assertEqual(row["category"], self.reference_category)

    def test_filter_source(self):
        response = self.client.get(self.list_url, {"source": self.reference_source})
        self.assert_get_list_shape(response)
        for row in response.data["transactions"]:
            self.assertEqual(row["source"], self.reference_source)

    def test_filter_currency_code(self):
        response = self.client.get(
            self.list_url,
            {"currency_code": self.reference_currency},
        )
        self.assert_get_list_shape(response)
        for row in response.data["transactions"]:
            self.assertEqual(row["currency"], self.reference_currency)

    def test_filter_by_date(self):
        response = self.client.get(self.list_url, {"by_date": "2021-02-02"})
        self.assert_get_list_shape(response)
        self.assertEqual(len(response.data["transactions"]), 1)
        self.assertEqual(response.data["transactions"][0]["tx_id"], self.exp_small_tx_id)

    def test_filter_date_alias(self):
        response = self.client.get(self.list_url, {"date": "2021-02-02"})
        self.assert_get_list_shape(response)
        self.assertEqual(len(response.data["transactions"]), 1)
        self.assertEqual(response.data["transactions"][0]["tx_id"], self.exp_small_tx_id)

    def test_filter_by_year_param(self):
        response = self.client.get(self.list_url, {"by_year": "2018"})
        self.assert_get_list_shape(response)
        self.assertEqual(len(response.data["transactions"]), 1)
        self.assertEqual(response.data["transactions"][0]["tx_id"], self.income_tx_id)

    def test_filter_year_without_month(self):
        response = self.client.get(self.list_url, {"year": "2024"})
        self.assert_get_list_shape(response)
        ids = {r["tx_id"] for r in response.data["transactions"]}
        self.assertIn(self.get_tx["exp_big"]["tx_id"], ids)
        self.assertIn(self.latest_tx_id, ids)

    def test_filter_month_and_year(self):
        response = self.client.get(self.list_url, {"month": "6", "year": "2024"})
        self.assert_get_list_shape(response)
        self.assertEqual(len(response.data["transactions"]), 1)
        self.assertEqual(response.data["transactions"][0]["tx_id"], self.latest_tx_id)

    def test_filter_start_date_only(self):
        response = self.client.get(self.list_url, {"start_date": "2024-05-15"})
        self.assert_get_list_shape(response)
        ids = {r["tx_id"] for r in response.data["transactions"]}
        self.assertIn(self.latest_tx_id, ids)
        self.assertNotIn(self.income_tx_id, ids)

    def test_filter_end_date_only(self):
        response = self.client.get(self.list_url, {"end_date": "2018-12-31"})
        self.assert_get_list_shape(response)
        self.assertEqual(len(response.data["transactions"]), 1)
        self.assertEqual(response.data["transactions"][0]["tx_id"], self.income_tx_id)

    def test_filter_start_and_end_date(self):
        response = self.client.get(
            self.list_url,
            {"start_date": "2019-01-01", "end_date": "2021-12-31"},
        )
        self.assert_get_list_shape(response)
        ids = {r["tx_id"] for r in response.data["transactions"]}
        self.assertIn(self.tagged_expense_tx_id, ids)
        self.assertIn(self.get_tx["xfer_out"]["tx_id"], ids)
        self.assertIn(self.exp_small_tx_id, ids)

    def test_filter_gte_amount(self):
        response = self.client.get(self.list_url, {"gte": "400"})
        self.assert_get_list_shape(response)
        ids = {r["tx_id"] for r in response.data["transactions"]}
        self.assertIn(self.income_tx_id, ids)
        for row in response.data["transactions"]:
            self.assertGreaterEqual(Decimal(str(row["amount"])), Decimal("400"))

    def test_filter_lte_amount(self):
        response = self.client.get(self.list_url, {"lte": "-50"})
        self.assert_get_list_shape(response)
        for row in response.data["transactions"]:
            self.assertLessEqual(Decimal(str(row["amount"])), Decimal("-50"))


@freeze_time("2024-06-15 12:00:00")
class TransactionGetCalendarFiltersTestCase(TransactionGetBase):
    """
    current_month / last_month depend on "today"; freeze time so seeded dates are stable.
    """

    def test_filter_current_month(self):
        response = self.client.get(self.list_url, {"current_month": "true"})
        self.assert_get_list_shape(response)
        ids = {r["tx_id"] for r in response.data["transactions"]}
        self.assertEqual(ids, {self.latest_tx_id})

    def test_filter_last_month(self):
        """last_month applies get_last_month() filtering; response matches list serializer."""
        response = self.client.get(self.list_url, {"last_month": "true"})
        self.assert_get_list_shape(response)
        self.assertIsInstance(response.data["transactions"], list)

    def test_filter_previous_week(self):
        response = self.client.get(self.list_url, {"previous_week": "true"})
        self.assert_get_list_shape(response)
        self.assertIsInstance(response.data["transactions"], list)

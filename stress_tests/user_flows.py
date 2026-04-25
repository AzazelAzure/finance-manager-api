"""Weighted Locust user flows for finance API stress testing."""

from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

from locust import HttpUser, between, task

from stress_tests.config import DEFAULT_REQUEST_TIMEOUT


class FinanceStressUser(HttpUser):
    """Simulated authenticated user executing mixed CRUD and read flows."""

    wait_time = between(0.2, 2.0)

    def on_start(self) -> None:
        self.headers: Dict[str, str] = {}
        self.uid: Optional[str] = None
        self.user_slot = random.randint(0, max(self.environment.parsed_options.seeded_users - 1, 0))
        self.sources: List[str] = []
        self.categories: List[str] = []
        self.tags: List[str] = []
        self.expenses: List[str] = []
        self.tx_ids: List[str] = []
        self.contention_tx_id: Optional[str] = None
        self.contention_source: Optional[str] = None
        self.contention_category: Optional[str] = None
        self.contention_expense: Optional[str] = None
        self._authenticate()
        self._prime_state()

    def _username(self) -> str:
        return self.environment.parsed_options.username_template.format(user_id=self.user_slot)

    def _password(self) -> str:
        return self.environment.parsed_options.password

    def _authenticate(self) -> None:
        username = self._username()
        payload = {"username": username, "password": self._password()}
        with self.client.post(
            "/api/token/",
            json=payload,
            name="auth.token.obtain",
            catch_response=True,
            timeout=DEFAULT_REQUEST_TIMEOUT,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Auth failed for {username}: {response.status_code}")
                return
            token = response.json().get("access")
            if not token:
                response.failure("Missing access token")
                return
            self.headers = {"Authorization": f"Bearer {token}"}
            response.success()

    def _prime_state(self) -> None:
        self._refresh_sources()
        self._refresh_categories()
        self._refresh_tags()
        self._refresh_expenses()
        self._refresh_transactions()

    def _refresh_sources(self) -> None:
        response = self.client.get("/finance/sources/", headers=self.headers, name="sources.list")
        if response.status_code == 200:
            self.sources = [item["source"] for item in response.json() if item.get("source")]
            if self.sources:
                self.contention_source = self.sources[0]

    def _refresh_categories(self) -> None:
        response = self.client.get("/finance/categories/", headers=self.headers, name="categories.list")
        if response.status_code == 200:
            self.categories = [item["name"] for item in response.json() if item.get("name")]
            if self.categories:
                self.contention_category = self.categories[0]

    def _refresh_tags(self) -> None:
        response = self.client.get("/finance/tags/", headers=self.headers, name="tags.list")
        if response.status_code == 200:
            self.tags = list(response.json().get("tags", []))

    def _refresh_expenses(self) -> None:
        response = self.client.get("/finance/upcoming_expenses/", headers=self.headers, name="expenses.list")
        if response.status_code == 200:
            self.expenses = [item["name"] for item in response.json().get("expenses", []) if item.get("name")]
            if self.expenses:
                self.contention_expense = self.expenses[0]

    def _refresh_transactions(self) -> None:
        response = self.client.get("/finance/transactions/", headers=self.headers, name="transactions.list")
        if response.status_code == 200:
            tx_rows = response.json().get("transactions", [])
            self.tx_ids = [row["tx_id"] for row in tx_rows if row.get("tx_id")]
            if self.tx_ids:
                self.contention_tx_id = self.tx_ids[0]

    def _random_date(self) -> str:
        return str(date.today() - timedelta(days=random.randint(0, 45)))

    def _ensure_dependencies(self) -> None:
        if not self.sources:
            self.create_source()
        if not self.categories:
            self.create_category()
        if not self.tags:
            self.create_tag()

    @task(20)
    def read_mixed_endpoints(self) -> None:
        self.client.get("/finance/transactions/", headers=self.headers, name="read.transactions")
        self.client.get("/finance/sources/", headers=self.headers, name="read.sources")
        self.client.get("/finance/categories/", headers=self.headers, name="read.categories")
        self.client.get("/finance/tags/", headers=self.headers, name="read.tags")
        self.client.get("/finance/upcoming_expenses/", headers=self.headers, name="read.expenses")
        self.client.get("/finance/appprofile/", headers=self.headers, name="read.profile")
        self.client.get("/finance/appprofile/snapshot/", headers=self.headers, name="read.snapshot")

    @task(14)
    def create_transaction(self) -> None:
        self._ensure_dependencies()
        payload = {
            "date": self._random_date(),
            "description": f"stress-tx-{random.randint(1, 100000)}",
            "amount": str(Decimal(random.randint(100, 5000)) / 100),
            "source": random.choice(self.sources),
            "currency": "USD",
            "tx_type": random.choice(["EXPENSE", "INCOME"]),
            "category": random.choice(self.categories),
            "tags": [random.choice(self.tags)],
        }
        with self.client.post(
            "/finance/transactions/",
            json=payload,
            headers=self.headers,
            name="transactions.create",
            catch_response=True,
        ) as response:
            if response.status_code != 201:
                response.failure(f"Unexpected status: {response.status_code}")
                return
            accepted = response.json().get("accepted", [])
            if accepted and accepted[0].get("tx_id"):
                tx_id = accepted[0]["tx_id"]
                self.tx_ids.append(tx_id)
                if not self.contention_tx_id:
                    self.contention_tx_id = tx_id
            response.success()

    @task(8)
    def update_transaction(self) -> None:
        if not self.tx_ids:
            self.create_transaction()
            return
        tx_id = random.choice(self.tx_ids)
        payload = {
            "date": self._random_date(),
            "description": f"updated-{random.randint(1, 100000)}",
            "amount": "12.34",
            "source": random.choice(self.sources),
            "currency": "USD",
            "tx_type": "EXPENSE",
            "category": random.choice(self.categories),
            "tags": [random.choice(self.tags)],
        }
        self.client.patch(
            f"/finance/transactions/{tx_id}/",
            json=payload,
            headers=self.headers,
            name="transactions.patch",
        )

    @task(5)
    def delete_transaction(self) -> None:
        if not self.tx_ids:
            return
        tx_id = self.tx_ids.pop()
        self.client.delete(
            f"/finance/transactions/{tx_id}/",
            headers=self.headers,
            name="transactions.delete",
        )

    @task(7)
    def create_source(self) -> None:
        source_name = f"s-{random.randint(1000, 999999)}"
        payload = {"source": source_name, "acc_type": "CASH", "amount": "100.00", "currency": "USD"}
        with self.client.post("/finance/sources/", json=payload, headers=self.headers, name="sources.create") as response:
            if response.status_code == 201:
                self.sources.append(source_name)
                if not self.contention_source:
                    self.contention_source = source_name

    @task(5)
    def update_source(self) -> None:
        if not self.sources:
            self.create_source()
            return
        source_name = random.choice(self.sources)
        payload = {"source": source_name, "acc_type": "CASH", "amount": "125.00", "currency": "USD"}
        self.client.put(
            f"/finance/sources/{source_name}/",
            json=payload,
            headers=self.headers,
            name="sources.put",
        )

    @task(3)
    def delete_source(self) -> None:
        if len(self.sources) < 2:
            return
        source_name = self.sources.pop()
        self.client.delete("/finance/sources/", json={"source": source_name}, headers=self.headers, name="sources.delete")

    @task(6)
    def create_category(self) -> None:
        category_name = f"cat-{random.randint(1000, 999999)}"
        with self.client.post(
            "/finance/categories/",
            json={"name": category_name},
            headers=self.headers,
            name="categories.create",
        ) as response:
            if response.status_code == 201:
                self.categories.append(category_name)
                if not self.contention_category:
                    self.contention_category = category_name

    @task(4)
    def update_category(self) -> None:
        if not self.categories:
            self.create_category()
            return
        original = random.choice(self.categories)
        updated = f"{original}-u{random.randint(1, 9999)}"
        with self.client.patch(
            f"/finance/categories/{original}/",
            json={"name": updated},
            headers=self.headers,
            name="categories.patch",
        ) as response:
            if response.status_code == 200:
                self.categories = [updated if item == original else item for item in self.categories]

    @task(3)
    def delete_category(self) -> None:
        if len(self.categories) < 2:
            return
        category = self.categories.pop()
        self.client.delete(
            f"/finance/categories/{category}/",
            headers=self.headers,
            name="categories.delete",
        )

    @task(6)
    def create_tag(self) -> None:
        tag_name = f"tag-{random.randint(1000, 999999)}"
        with self.client.post("/finance/tags/", json={"tags": [tag_name]}, headers=self.headers, name="tags.create") as response:
            if response.status_code == 201:
                self.tags.append(tag_name)

    @task(4)
    def update_tag(self) -> None:
        if not self.tags:
            self.create_tag()
            return
        original = random.choice(self.tags)
        updated = f"{original}-u{random.randint(1, 9999)}"
        payload = {"tags": {original: updated}}
        with self.client.patch("/finance/tags/", json=payload, headers=self.headers, name="tags.patch") as response:
            if response.status_code == 200:
                self.tags = [updated if item == original else item for item in self.tags]

    @task(2)
    def delete_tag(self) -> None:
        if len(self.tags) < 2:
            return
        tag = self.tags.pop()
        self.client.delete("/finance/tags/", json={"tags": {tag: ""}}, headers=self.headers, name="tags.delete")

    @task(5)
    def create_expense(self) -> None:
        expense_name = f"bill-{random.randint(1000, 999999)}"
        payload = {
            "name": expense_name,
            "amount": "49.99",
            "due_date": str(date.today() + timedelta(days=7)),
            "start_date": str(date.today()),
            "end_date": None,
            "paid_flag": False,
            "currency": "USD",
            "is_recurring": True,
        }
        with self.client.post(
            "/finance/upcoming_expenses/",
            json=payload,
            headers=self.headers,
            name="expenses.create",
        ) as response:
            if response.status_code == 201:
                self.expenses.append(expense_name)
                if not self.contention_expense:
                    self.contention_expense = expense_name

    @task(3)
    def update_expense(self) -> None:
        if not self.expenses:
            self.create_expense()
            return
        expense_name = random.choice(self.expenses)
        payload = {"paid_flag": bool(random.getrandbits(1))}
        self.client.patch(
            f"/finance/upcoming_expenses/{expense_name}/",
            json=payload,
            headers=self.headers,
            name="expenses.patch",
        )

    @task(2)
    def delete_expense(self) -> None:
        if len(self.expenses) < 2:
            return
        expense_name = self.expenses.pop()
        self.client.delete(
            f"/finance/upcoming_expenses/{expense_name}/",
            headers=self.headers,
            name="expenses.delete",
        )

    @task(4)
    def update_profile(self) -> None:
        if not self.sources:
            self._refresh_sources()
        payload = {"base_currency": "USD", "spend_accounts": self.sources[:2] or ["cash"]}
        self.client.patch("/finance/appprofile/", json=payload, headers=self.headers, name="profile.patch")

    @task(3)
    def contention_same_transaction(self) -> None:
        if not self.contention_tx_id:
            self.create_transaction()
            return
        payload = {
            "date": self._random_date(),
            "description": f"contention-update-{random.randint(1, 99999)}",
            "amount": "5.00",
            "source": random.choice(self.sources),
            "currency": "USD",
            "tx_type": "EXPENSE",
            "category": random.choice(self.categories),
            "tags": [random.choice(self.tags)],
        }
        self.client.patch(
            f"/finance/transactions/{self.contention_tx_id}/",
            json=payload,
            headers=self.headers,
            name="contention.transactions.patch",
        )

    @task(2)
    def contention_same_source(self) -> None:
        if not self.contention_source:
            return
        payload = {
            "source": self.contention_source,
            "acc_type": random.choice(["CASH", "CHECKING", "SAVINGS"]),
            "amount": str(Decimal(random.randint(1000, 4000)) / 100),
            "currency": "USD",
        }
        self.client.put(
            f"/finance/sources/{self.contention_source}/",
            json=payload,
            headers=self.headers,
            name="contention.sources.put",
        )

    @task(2)
    def contention_same_category(self) -> None:
        if not self.contention_category:
            return
        updated = f"{self.contention_category}-c{random.randint(1, 999)}"
        self.client.patch(
            f"/finance/categories/{self.contention_category}/",
            json={"name": updated},
            headers=self.headers,
            name="contention.categories.patch",
        )

    @task(2)
    def contention_same_expense(self) -> None:
        if not self.contention_expense:
            return
        payload = {"paid_flag": bool(random.getrandbits(1))}
        self.client.patch(
            f"/finance/upcoming_expenses/{self.contention_expense}/",
            json=payload,
            headers=self.headers,
            name="contention.expenses.patch",
        )

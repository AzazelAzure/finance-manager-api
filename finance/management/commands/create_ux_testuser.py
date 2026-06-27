from __future__ import annotations

import os
import random
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Sum
from django.utils import timezone

from finance.logic.fincalc import Calculator
from finance.models import (
    AppProfile,
    Category,
    FinancialSnapshot,
    PaymentSource,
    Tag,
    Transaction,
    UpcomingExpense,
)


PAYMENT_SOURCES = [
    ("Cash", "CASH", Decimal("5000.00")),
    ("GCash", "EWALLET", Decimal("8500.00")),
    ("BDO Checking", "CHECKING", Decimal("45000.00")),
    ("Maya", "EWALLET", Decimal("2300.00")),
    ("Savings Account", "SAVINGS", Decimal("120000.00")),
    ("Credit Card", "CHECKING", Decimal("0.00")),
]

CATEGORIES = [
    "Food & Groceries",
    "Transport",
    "Utilities",
    "Rent / Housing",
    "Health",
    "Entertainment",
    "Savings Transfer",
    "Income",
]

TAGS = ["recurring", "essential", "discretionary", "reimbursable"]


class Command(BaseCommand):
    help = "Create or reset the ux_demo test user with realistic seeded data."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="ux_demo")
        parser.add_argument("--email", default="ux_demo@internal.test")
        parser.add_argument("--password", default=os.getenv("UX_DEMO_PASSWORD", "UxDemo2026!"))
        parser.add_argument("--reset", action="store_true", help="Delete and reseed domain data if user exists")
        parser.add_argument(
            "--confirm-not-prod",
            action="store_true",
            help="Required when DEBUG is False to acknowledge this creates test data",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("WARNING: This command creates test data. Do not run on production."))
        if not settings.DEBUG and not options["confirm_not_prod"]:
            raise CommandError("Refusing to run with DEBUG=False unless --confirm-not-prod is passed.")

        username = options["username"]
        email = options["email"]
        password = options["password"]
        reset = options["reset"]

        user = User.objects.filter(username=username).first()
        if user and reset:
            if username != "ux_demo" and not str(email).endswith("@internal.test"):
                raise CommandError(
                    "Refusing --reset for non-test accounts. Use default ux_demo or an @internal.test email."
                )
        if user and not reset:
            self.stdout.write(
                self.style.WARNING(
                    f"User '{username}' already exists. Pass --reset to delete domain data and reseed."
                )
            )
            return

        if user and reset:
            uid = str(user.appprofile.user_id)
            self._clear_domain_data(uid)
            self.stdout.write(f"Reset domain data for user '{username}'.")
        elif not user:
            user = User.objects.create_user(username=username, email=email, password=password)
            self.stdout.write(f"Created user '{username}'.")

        uid = str(user.appprofile.user_id)
        profile = user.appprofile
        profile.base_currency = "PHP"
        profile.save(update_fields=["base_currency"])

        self._seed_sources(uid)
        self._seed_categories(uid)
        self._seed_tags(uid)
        tx_count = self._seed_transactions(uid)
        self._seed_upcoming(uid)
        self._recompute_balances(uid, profile)

        self.stdout.write(
            self.style.SUCCESS(
                f"UX test user ready: username={username}, transactions={tx_count}, uid={uid}"
            )
        )

    def _clear_domain_data(self, uid: str) -> None:
        Transaction.objects.filter(uid=uid).delete()
        UpcomingExpense.objects.filter(uid=uid).delete()
        Category.objects.filter(uid=uid).delete()
        Tag.objects.filter(uid=uid).delete()
        PaymentSource.objects.filter(uid=uid).exclude(source="unknown").delete()

    def _seed_sources(self, uid: str) -> None:
        spend = []
        for source_name, acc_type, amount in PAYMENT_SOURCES:
            obj, _ = PaymentSource.objects.get_or_create(
                uid=uid,
                source=source_name,
                defaults={
                    "acc_type": acc_type,
                    "currency": "PHP",
                    "amount": amount,
                },
            )
            if obj.amount != amount:
                obj.amount = amount
                obj.acc_type = acc_type
                obj.currency = "PHP"
                obj.save(update_fields=["amount", "acc_type", "currency"])
            spend.append(source_name)
        profile = AppProfile.objects.get(user_id=uid)
        profile.spend_accounts = spend[:3]
        profile.save(update_fields=["spend_accounts"])

    def _seed_categories(self, uid: str) -> None:
        for name in CATEGORIES:
            Category.objects.get_or_create(uid=uid, name=name)

    def _seed_tags(self, uid: str) -> None:
        tag_row, _ = Tag.objects.get_or_create(uid=uid, defaults={"tags": TAGS})
        if tag_row.tags != TAGS:
            tag_row.tags = TAGS
            tag_row.save(update_fields=["tags"])

    def _seed_transactions(self, uid: str) -> int:
        today = date.today()
        rng = random.Random(42)
        tx_rows: list[Transaction] = []
        tx_index = 0

        def add_tx(
            *,
            tx_date: date,
            description: str,
            amount: Decimal,
            category: str,
            source: str,
            tx_type: str,
            tags: list[str] | None = None,
        ) -> None:
            nonlocal tx_index
            tx_rows.append(
                Transaction(
                    uid=uid,
                    tx_id=f"uxdemo-{tx_index:06d}",
                    date=tx_date,
                    created_on=today,
                    description=description,
                    amount=amount,
                    category=category,
                    source=source,
                    currency="PHP",
                    tags=tags or [],
                    bill="",
                    tx_type=tx_type,
                )
            )
            tx_index += 1

        for month_offset in range(11, -1, -1):
            ref = today.replace(day=1) - timedelta(days=month_offset * 28)
            year, month = ref.year, ref.month
            last_day = monthrange(year, month)[1]
            month_end = date(year, month, last_day)
            if month_end > today:
                month_end = today

            # Fixed expenses (days 1-5)
            add_tx(
                tx_date=min(date(year, month, min(5, last_day)), month_end),
                description="Rent payment",
                amount=Decimal("-18000.00"),
                category="Rent / Housing",
                source="BDO Checking",
                tx_type=Transaction.TxType.EXPENSE,
                tags=["recurring", "essential"],
            )
            add_tx(
                tx_date=min(date(year, month, min(3, last_day)), month_end),
                description="Electric bill",
                amount=Decimal("-1800.00"),
                category="Utilities",
                source="BDO Checking",
                tx_type=Transaction.TxType.EXPENSE,
                tags=["recurring", "essential"],
            )
            add_tx(
                tx_date=min(date(year, month, min(4, last_day)), month_end),
                description="Internet",
                amount=Decimal("-1200.00"),
                category="Utilities",
                source="BDO Checking",
                tx_type=Transaction.TxType.EXPENSE,
                tags=["recurring", "essential"],
            )
            add_tx(
                tx_date=min(date(year, month, min(2, last_day)), month_end),
                description="Savings transfer",
                amount=Decimal("-5000.00"),
                category="Savings Transfer",
                source="BDO Checking",
                tx_type=Transaction.TxType.TRANSFER_OUT,
                tags=["recurring"],
            )

            salary_day = min(date(year, month, min(15, last_day)), month_end)
            add_tx(
                tx_date=salary_day,
                description="Salary",
                amount=Decimal("65000.00"),
                category="Income",
                source="BDO Checking",
                tx_type=Transaction.TxType.INCOME,
                tags=["recurring", "essential"],
            )

            if rng.randint(0, 11) < 8:
                freelance = Decimal(str(rng.randint(8000, 20000)))
                freelance_day = min(date(year, month, min(rng.randint(10, 25), last_day)), month_end)
                add_tx(
                    tx_date=freelance_day,
                    description="Freelance income",
                    amount=freelance,
                    category="Income",
                    source="Maya",
                    tx_type=Transaction.TxType.INCOME,
                    tags=["discretionary"],
                )

            variable_specs = [
                ("Food & Groceries", 8000, 0.2, ["GCash", "Cash"]),
                ("Transport", 2500, 0.3, ["GCash", "Cash"]),
                ("Health", 800, 0.5, ["Cash", "Maya"]),
                ("Entertainment", 1500, 0.4, ["GCash"]),
            ]
            for cat, avg, variance, sources in variable_specs:
                count = rng.randint(4, 8)
                for _ in range(count):
                    day = rng.randint(1, min(last_day, month_end.day if month_end.month == month else last_day))
                    tx_date = date(year, month, day)
                    if tx_date > today:
                        continue
                    spread = avg * variance
                    amount = Decimal(str(max(50, rng.gauss(avg / count, spread / count))))
                    amount = Decimal(str(round(-float(amount), 2)))
                    add_tx(
                        tx_date=tx_date,
                        description=f"{cat} purchase",
                        amount=amount,
                        category=cat,
                        source=rng.choice(sources),
                        tx_type=Transaction.TxType.EXPENSE,
                        tags=[rng.choice(["essential", "discretionary", "recurring"])],
                    )

        Transaction.objects.bulk_create(tx_rows, batch_size=500)
        return len(tx_rows)

    def _seed_upcoming(self, uid: str) -> None:
        today = date.today()
        next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
        UpcomingExpense.objects.filter(uid=uid).delete()
        UpcomingExpense.objects.bulk_create(
            [
                UpcomingExpense(
                    uid=uid,
                    name="Rent — July",
                    amount=Decimal("18000.00"),
                    due_date=next_month,
                    start_date=today,
                    end_date=next_month + timedelta(days=30),
                    paid_flag=False,
                    currency="PHP",
                    is_recurring=True,
                ),
                UpcomingExpense(
                    uid=uid,
                    name="Electric Bill",
                    amount=Decimal("1800.00"),
                    due_date=today + timedelta(days=10),
                    start_date=today,
                    end_date=today + timedelta(days=30),
                    paid_flag=False,
                    currency="PHP",
                    is_recurring=False,
                ),
                UpcomingExpense(
                    uid=uid,
                    name="Internet",
                    amount=Decimal("1200.00"),
                    due_date=today + timedelta(days=15),
                    start_date=today,
                    end_date=today + timedelta(days=30),
                    paid_flag=False,
                    currency="PHP",
                    is_recurring=True,
                ),
            ]
        )

    def _recompute_balances(self, uid: str, profile: AppProfile) -> None:
        source_totals = {
            row["source"]: (row["total"] or Decimal("0.00"))
            for row in Transaction.objects.filter(uid=uid).values("source").annotate(total=Sum("amount"))
        }
        sources = list(PaymentSource.objects.filter(uid=uid))
        for source in sources:
            if source.source == "unknown":
                continue
            source.amount = Decimal(source_totals.get(source.source, Decimal("0.00"))).quantize(Decimal("0.01"))
        if sources:
            PaymentSource.objects.bulk_update(sources, ["amount"])

        snapshot, _ = FinancialSnapshot.objects.get_or_create(uid=uid)
        calculator = Calculator(profile)
        spend_accounts = set(profile.spend_accounts or [])
        spend_sources = [s for s in sources if s.source in spend_accounts]
        debts = list(UpcomingExpense.objects.for_user(uid).get_current_month().filter(paid_flag=False))
        type_totals = calculator.calc_acc_types(sources)
        snapshot.total_assets = calculator.calc_total_assets(sources)
        snapshot.safe_to_spend = calculator.calc_sts(spend_sources, debts)
        for total_name, value in type_totals.items():
            if hasattr(snapshot, total_name):
                setattr(snapshot, total_name, value)
        transfers = list(Transaction.objects.filter(uid=uid, tx_type__in=["XFER_IN", "XFER_OUT"]))
        snapshot.total_leaks = calculator.calc_leaks(transfers) if transfers else Decimal("0.00")
        snapshot.total_monthly_spending = calculator.calc_current_month_expense_spending()
        snapshot.total_remaining_expenses = calculator.calc_upcoming_bills_base_total(debts)
        snapshot.save()

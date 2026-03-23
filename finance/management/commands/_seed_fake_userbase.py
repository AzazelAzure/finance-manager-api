from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
import random
from contextlib import contextmanager

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Sum
from django.db.models.signals import post_save
from django.utils import timezone

from finance.logic.fincalc import Calculator
from finance.models import AppProfile, Category, FinancialSnapshot, PaymentSource, Tag, Transaction, UpcomingExpense
from finance.api_tools.signals import create_user


def _to_list_spend_accounts(value) -> list[str]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [value]
    return []


def _seed_user(
    *,
    user_index: int,
    user: User,
    transactions_per_user: int,
    categories_per_user: int,
    tags_per_user: int,
    sources_per_user: int,
    upcoming_expenses_per_user: int,
    batch_size: int,
    currencies: list[str],
) -> None:
    uid = str(user.appprofile.user_id)
    today = timezone.now().date()
    rng = random.Random(user_index)
    profile = user.appprofile

    categories = [f"seed-category-{i}" for i in range(categories_per_user)]
    existing_categories = set(
        Category.objects.filter(uid=uid, name__in=categories).values_list("name", flat=True)
    )
    missing_categories = [Category(uid=uid, name=name) for name in categories if name not in existing_categories]
    if missing_categories:
        Category.objects.bulk_create(missing_categories, batch_size=batch_size)

    tag_payload = [f"seed-tag-{i}" for i in range(tags_per_user)]
    tag_row, _ = Tag.objects.get_or_create(uid=uid, defaults={"tags": tag_payload})
    if tag_row.tags != tag_payload:
        tag_row.tags = tag_payload
        tag_row.save(update_fields=["tags"])

    source_names = [f"seed-u{user_index:05d}-source-{i:02d}" for i in range(sources_per_user)]
    existing_sources = set(
        PaymentSource.objects.filter(source__in=source_names).values_list("source", flat=True)
    )
    source_rows = []
    acc_types = ["CHECKING", "SAVINGS", "CASH", "EWALLET", "INVESTMENT"]
    for i, source_name in enumerate(source_names):
        if source_name in existing_sources:
            continue
        source_rows.append(
            PaymentSource(
                uid=uid,
                source=source_name,
                acc_type=acc_types[i % len(acc_types)],
                currency=currencies[i % len(currencies)],
                amount=Decimal("0.00"),
            )
        )
    if source_rows:
        PaymentSource.objects.bulk_create(source_rows, batch_size=batch_size, ignore_conflicts=True)
    if source_names:
        profile.spend_accounts = source_names[: min(2, len(source_names))]
        profile.save(update_fields=["spend_accounts"])

    expense_names = [f"seed-expense-{i}" for i in range(upcoming_expenses_per_user)]
    existing_expenses = set(
        UpcomingExpense.objects.filter(uid=uid, name__in=expense_names).values_list("name", flat=True)
    )
    expense_rows = []
    for i, expense_name in enumerate(expense_names):
        if expense_name in existing_expenses:
            continue
        expense_rows.append(
            UpcomingExpense(
                uid=uid,
                name=expense_name,
                amount=Decimal(f"{(i + 1) * 10}.00"),
                due_date=today + timedelta(days=(i % 28) + 1),
                start_date=today - timedelta(days=14),
                end_date=today + timedelta(days=365),
                paid_flag=False,
                currency=currencies[i % len(currencies)],
                is_recurring=True,
            )
        )
    if expense_rows:
        UpcomingExpense.objects.bulk_create(expense_rows, batch_size=batch_size)

    existing_tx_count = Transaction.objects.filter(uid=uid, tx_id__startswith=f"seed-{user_index:05d}-").count()
    missing_tx = max(0, transactions_per_user - existing_tx_count)
    if missing_tx:
        sources_for_tx = [s.source for s in PaymentSource.objects.filter(uid=uid).exclude(source="unknown")]
        if not sources_for_tx:
            sources_for_tx = ["cash"]
        bill_names = expense_names or [""]
        tx_rows = []
        tx_types = ["EXPENSE", "INCOME", "XFER_OUT", "XFER_IN"]
        start_idx = existing_tx_count
        for i in range(start_idx, start_idx + missing_tx):
            tx_type = tx_types[i % len(tx_types)]
            amount = Decimal(f"{(i % 300) + 1}.00")
            if tx_type in {"EXPENSE", "XFER_OUT"}:
                amount *= Decimal("-1")
            tx_rows.append(
                Transaction(
                    uid=uid,
                    tx_id=f"seed-{user_index:05d}-{i:07d}",
                    date=today - timedelta(days=(i % 30)),
                    created_on=today,
                    description=f"seed tx {i}",
                    amount=amount,
                    category=categories[i % len(categories)] if categories else "expense",
                    source=sources_for_tx[i % len(sources_for_tx)],
                    currency=currencies[i % len(currencies)],
                    tags=[tag_payload[i % len(tag_payload)]] if tag_payload else [],
                    bill=bill_names[i % len(bill_names)],
                    tx_type=tx_type,
                )
            )
            if len(tx_rows) >= batch_size:
                Transaction.objects.bulk_create(tx_rows, batch_size=batch_size)
                tx_rows = []
        if tx_rows:
            Transaction.objects.bulk_create(tx_rows, batch_size=batch_size)

    _recompute_balances_and_snapshot(uid=uid, profile=profile)


def _recompute_balances_and_snapshot(*, uid: str, profile) -> None:
    source_totals = {
        row["source"]: (row["total"] or Decimal("0.00"))
        for row in Transaction.objects.filter(uid=uid).values("source").annotate(total=Sum("amount"))
    }
    sources = list(PaymentSource.objects.filter(uid=uid))
    for source in sources:
        source.amount = Decimal(source_totals.get(source.source, Decimal("0.00"))).quantize(Decimal("0.01"))
    if sources:
        PaymentSource.objects.bulk_update(sources, ["amount"])

    snapshot, _ = FinancialSnapshot.objects.get_or_create(uid=uid)
    calculator = Calculator(profile)
    spend_accounts = set(_to_list_spend_accounts(profile.spend_accounts))
    spend_sources = [source for source in sources if source.source in spend_accounts]
    debts = list(UpcomingExpense.objects.for_user(uid).get_current_month().filter(paid_flag=False))
    type_totals = calculator.calc_acc_types(sources)

    snapshot.total_assets = calculator.calc_total_assets(sources)
    snapshot.safe_to_spend = calculator.calc_sts(spend_sources, debts)
    snapshot.total_savings = Decimal("0.00")
    snapshot.total_checking = Decimal("0.00")
    snapshot.total_investment = Decimal("0.00")
    snapshot.total_cash = Decimal("0.00")
    snapshot.total_ewallet = Decimal("0.00")
    for total_name, value in type_totals.items():
        if hasattr(snapshot, total_name):
            setattr(snapshot, total_name, value)

    transfers = list(Transaction.objects.filter(uid=uid, tx_type__in=["XFER_IN", "XFER_OUT"]))
    snapshot.total_leaks = calculator.calc_leaks(transfers) if transfers else Decimal("0.00")
    snapshot.save()


def seed_fake_userbase(
    *,
    users: int,
    transactions_per_user: int,
    categories_per_user: int,
    tags_per_user: int,
    sources_per_user: int,
    upcoming_expenses_per_user: int,
    dry_run: bool,
    batch_size: int,
    currencies: list[str],
    stdout,
) -> dict:
    summary = {
        "users": users,
        "transactions_per_user": transactions_per_user,
        "estimated_transactions": users * transactions_per_user,
        "categories_per_user": categories_per_user,
        "tags_per_user": tags_per_user,
        "sources_per_user": sources_per_user,
        "upcoming_expenses_per_user": upcoming_expenses_per_user,
    }
    if dry_run:
        return summary

    created_users = 0

    @contextmanager
    def _without_default_user_signal():
        post_save.disconnect(create_user, sender=User)
        try:
            yield
        finally:
            post_save.connect(create_user, sender=User)

    with _without_default_user_signal():
        for user_index in range(users):
            username = f"demo_user_{user_index:05d}"
            email = f"{username}@example.com"
            with transaction.atomic():
                user, was_created = User.objects.get_or_create(
                    username=username,
                    defaults={"email": email},
                )
                if was_created:
                    user.set_password("seed-password")
                    user.save(update_fields=["password"])
                    created_users += 1

                profile, _ = AppProfile.objects.get_or_create(username=user)
                FinancialSnapshot.objects.get_or_create(uid=str(profile.user_id))

                _seed_user(
                    user_index=user_index,
                    user=user,
                    transactions_per_user=transactions_per_user,
                    categories_per_user=categories_per_user,
                    tags_per_user=tags_per_user,
                    sources_per_user=sources_per_user,
                    upcoming_expenses_per_user=upcoming_expenses_per_user,
                    batch_size=batch_size,
                    currencies=currencies,
                )
            if (user_index + 1) % 50 == 0:
                stdout.write(f"Seeded {user_index + 1}/{users} users...")

    summary["created_users"] = created_users
    return summary

"""Seed and reset utilities for stress test user data."""

from __future__ import annotations

import argparse
import os
from contextlib import contextmanager
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "finance_api.settings")
django.setup()

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models.signals import post_save

from finance.api_tools.signals import create_user
from finance.models import AppProfile, Category, FinancialSnapshot, PaymentSource, Tag, Transaction, UpcomingExpense
from stress_tests.config import (
    DEFAULT_EMAIL_DOMAIN,
    DEFAULT_PASSWORD,
    DEFAULT_USER_PREFIX,
    SEED_DEFAULTS,
)


def _username(prefix: str, idx: int) -> str:
    return f"{prefix}_{idx}"


def reset_seeded_data(prefix: str) -> int:
    users = User.objects.filter(username__startswith=f"{prefix}_")
    count = users.count()
    users.delete()
    return count


def _seed_user_domain_data(user: User, idx: int) -> None:
    uid = str(user.appprofile.user_id)
    for source_idx in range(SEED_DEFAULTS.sources_per_user):
        source_name = f"{user.username}_src_{source_idx}"
        PaymentSource.objects.get_or_create(
            uid=uid,
            source=source_name,
            defaults={
                "acc_type": "CASH" if source_idx % 2 == 0 else "CHECKING",
                "currency": "USD",
                "amount": Decimal("1000.00"),
            },
        )
    for category_idx in range(SEED_DEFAULTS.categories_per_user):
        Category.objects.get_or_create(uid=uid, name=f"{user.username}_cat_{category_idx}")
    for tag_idx in range(SEED_DEFAULTS.tags_per_user):
        Tag.objects.get_or_create(uid=uid, tags=[f"{user.username}_tag_{tag_idx}"])
    for expense_idx in range(SEED_DEFAULTS.expenses_per_user):
        expense_name = f"{user.username}_bill_{expense_idx}"
        UpcomingExpense.objects.get_or_create(
            uid=uid,
            name=expense_name,
            defaults={
                "amount": Decimal("49.99"),
                "due_date": date.today() + timedelta(days=expense_idx + 1),
                "start_date": date.today(),
                "currency": "USD",
                "paid_flag": False,
                "is_recurring": True,
            },
        )

    sources = list(PaymentSource.objects.filter(uid=uid).exclude(source="unknown")[:2])
    if sources:
        user.appprofile.spend_accounts = [source.source for source in sources]
        user.appprofile.base_currency = "USD"
        user.appprofile.save(update_fields=["spend_accounts", "base_currency"])

    default_source = sources[0].source if sources else "cash"
    default_category = f"{user.username}_cat_0"
    default_tag = f"{user.username}_tag_0"
    tx_date = date.today()
    for tx_idx in range(2):
        tx_type = "EXPENSE" if tx_idx % 2 == 0 else "INCOME"
        amount = Decimal("10.00") if tx_type == "EXPENSE" else Decimal("25.00")
        tx_id = f"{tx_date.isoformat()}-seed-{idx}-{tx_idx}"
        Transaction.objects.get_or_create(
            uid=uid,
            tx_id=tx_id,
            defaults={
                "date": tx_date,
                "created_on": tx_date,
                "description": f"seeded transaction {tx_idx}",
                "amount": amount,
                "source": default_source,
                "currency": "USD",
                "tags": [default_tag],
                "category": default_category,
                "tx_type": tx_type,
            },
        )


def seed_users(prefix: str, password: str, email_domain: str, count: int) -> None:
    @contextmanager
    def _without_default_user_signal():
        post_save.disconnect(create_user, sender=User)
        try:
            yield
        finally:
            post_save.connect(create_user, sender=User)

    with transaction.atomic():
        with _without_default_user_signal():
            for idx in range(count):
                username = _username(prefix, idx)
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={"email": f"{username}@{email_domain}"},
                )
                if created:
                    user.set_password(password)
                    user.save(update_fields=["password"])
                profile, _ = AppProfile.objects.get_or_create(username=user)
                FinancialSnapshot.objects.get_or_create(uid=str(profile.user_id))
                _seed_user_domain_data(user, idx)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed and reset users for stress tests")
    parser.add_argument("--count", type=int, default=1000, help="Number of users to seed")
    parser.add_argument("--prefix", type=str, default=DEFAULT_USER_PREFIX, help="Username prefix")
    parser.add_argument("--password", type=str, default=DEFAULT_PASSWORD, help="Stress user password")
    parser.add_argument("--email-domain", type=str, default=DEFAULT_EMAIL_DOMAIN, help="Email domain for stress users")
    parser.add_argument("--reset", action="store_true", help="Delete existing stress users first")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.reset:
        deleted = reset_seeded_data(args.prefix)
        print(f"Deleted {deleted} users for prefix {args.prefix}")
    seed_users(
        prefix=args.prefix,
        password=args.password,
        email_domain=args.email_domain,
        count=args.count,
    )
    print(f"Seeded users: {args.count} (prefix={args.prefix})")


if __name__ == "__main__":
    main()

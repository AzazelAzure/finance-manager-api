from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from finance.logic.balance_snapshots import closing_balances_as_of, persist_snapshots_for_date
from finance.models import AppProfile, Transaction


class Command(BaseCommand):
    help = "Backfill BalanceSnapshot rows from transaction history."

    def add_arguments(self, parser):
        parser.add_argument("--uid", type=str, help="Limit to a single AppProfile user_id")
        parser.add_argument(
            "--days",
            type=int,
            default=None,
            help="Backfill only the last N calendar days (default: full history)",
        )

    def handle(self, *args, **options):
        uid_filter = options.get("uid")
        days = options.get("days")
        profiles = AppProfile.objects.all()
        if uid_filter:
            profiles = profiles.filter(user_id=uid_filter)

        today = timezone.now().date()
        total_rows = 0
        for profile in profiles.iterator():
            uid = str(profile.user_id)
            if days is not None:
                start = today - timedelta(days=days - 1)
            else:
                first_tx = (
                    Transaction.objects.for_user(uid).order_by("date").values_list("date", flat=True).first()
                )
                start = first_tx or today
            current = start
            while current <= today:
                total_rows += persist_snapshots_for_date(uid, current)
                current += timedelta(days=1)

        self.stdout.write(self.style.SUCCESS(f"Backfill complete: {total_rows} snapshot rows upserted"))

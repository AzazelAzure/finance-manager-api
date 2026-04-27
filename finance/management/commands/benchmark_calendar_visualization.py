from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from datetime import timedelta
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils import timezone

from finance.management.commands._seed_fake_userbase import seed_fake_userbase
from finance.models import AppProfile
from finance.services.transaction_services import (
    get_transaction_calendar,
    get_transaction_visualization,
)


@dataclass(slots=True)
class BenchmarkResult:
    scenario: str
    users: int
    transactions_per_user: int
    iterations: int
    calendar_avg_ms: float
    calendar_p95_ms: float
    visualization_avg_ms: float
    visualization_p95_ms: float
    measured_at_utc: str


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = max(0, int(len(ordered) * 0.95) - 1)
    return ordered[idx]


class Command(BaseCommand):
    help = (
        "Seed a reproducible high-volume dataset and measure "
        "get_transaction_calendar/get_transaction_visualization latency."
    )

    def add_arguments(self, parser):
        parser.add_argument("--users", type=int, default=1)
        parser.add_argument("--transactions-per-user", type=int, default=10000)
        parser.add_argument("--iterations", type=int, default=5)
        parser.add_argument("--window-days", type=int, default=30)
        parser.add_argument("--seed", action="store_true", help="Seed/expand demo dataset before measuring.")
        parser.add_argument(
            "--output",
            type=str,
            default="stress_tests/results/calendar_visualization_benchmark.json",
            help="Path to write benchmark artifact JSON.",
        )

    def handle(self, *args, **options):
        users = int(options["users"])
        tx_per_user = int(options["transactions_per_user"])
        iterations = int(options["iterations"])
        window_days = int(options["window_days"])

        if options["seed"]:
            self.stdout.write("Seeding benchmark dataset...")
            seed_fake_userbase(
                users=users,
                transactions_per_user=tx_per_user,
                categories_per_user=8,
                tags_per_user=8,
                sources_per_user=4,
                upcoming_expenses_per_user=24,
                dry_run=False,
                batch_size=500,
                currencies=["USD", "EUR", "JPY", "GBP"],
                stdout=self.stdout,
            )

        # Use first demo user deterministically.
        profile = AppProfile.objects.filter(username__username__startswith="demo_user_").order_by("username__username").first()
        if profile is None:
            self.stderr.write("No demo_user_* profile found. Re-run with --seed.")
            return
        uid = str(profile.user_id)

        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=window_days)

        calendar_samples: list[float] = []
        visualization_samples: list[float] = []

        for _ in range(iterations):
            t0 = time.perf_counter()
            get_transaction_calendar(uid, start_date=start_date, end_date=end_date)
            calendar_samples.append((time.perf_counter() - t0) * 1000.0)

            t1 = time.perf_counter()
            get_transaction_visualization(uid, start_date=start_date, end_date=end_date)
            visualization_samples.append((time.perf_counter() - t1) * 1000.0)

        result = BenchmarkResult(
            scenario="calendar_and_visualization_aggregate",
            users=users,
            transactions_per_user=tx_per_user,
            iterations=iterations,
            calendar_avg_ms=round(_avg(calendar_samples), 2),
            calendar_p95_ms=round(_p95(calendar_samples), 2),
            visualization_avg_ms=round(_avg(visualization_samples), 2),
            visualization_p95_ms=round(_p95(visualization_samples), 2),
            measured_at_utc=timezone.now().isoformat(),
        )

        output_path = Path(options["output"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("Benchmark completed."))
        self.stdout.write(json.dumps(asdict(result), indent=2))
        self.stdout.write(f"Artifact written to: {output_path}")

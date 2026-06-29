"""Add first-class cadence fields to UpcomingExpense and backfill from date deltas."""

from collections import Counter
from datetime import date

from django.db import migrations, models
from loguru import logger


def _near(days: int, target: int, tolerance: int = 2) -> bool:
    return abs(days - target) <= tolerance


def _is_semimonthly_anchor_pattern(start: date, due: date) -> bool:
    return start.day in (1, 15) and due.day in (1, 15)


def infer_cadence_from_dates(start_date: date | None, due_date: date | None) -> str:
    """Map start/due delta to a named cadence (one-time backfill heuristic)."""
    if not start_date or not due_date:
        return "monthly"
    days = (due_date - start_date).days
    if days <= 0:
        return "monthly"
    if _near(days, 7):
        return "weekly"
    if _near(days, 14):
        return "biweekly"
    if _near(days, 15) or _near(days, 16) or _is_semimonthly_anchor_pattern(start_date, due_date):
        return "semimonthly"
    if 26 <= days <= 31:
        return "monthly"
    if _near(days, 90, tolerance=3):
        return "quarterly"
    if _near(days, 365, tolerance=3) or _near(days, 366, tolerance=3):
        return "annual"
    return "monthly"


def backfill_cadence(apps, schema_editor):
    UpcomingExpense = apps.get_model("finance", "UpcomingExpense")
    counts: Counter[str] = Counter()
    for bill in UpcomingExpense.objects.iterator():
        cadence = infer_cadence_from_dates(bill.start_date, bill.due_date)
        counts[cadence] += 1
        if bill.cadence != cadence:
            bill.cadence = cadence
            bill.save(update_fields=["cadence"])
    summary = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
    logger.info("UpcomingExpense cadence backfill complete: {}", summary)
    print(f"UpcomingExpense cadence backfill complete: {summary}")


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0016_savings_goal"),
    ]

    operations = [
        migrations.AddField(
            model_name="upcomingexpense",
            name="cadence",
            field=models.CharField(
                choices=[
                    ("weekly", "Weekly"),
                    ("biweekly", "Biweekly"),
                    ("semimonthly", "Semi-monthly"),
                    ("monthly", "Monthly"),
                    ("quarterly", "Quarterly"),
                    ("annual", "Annual"),
                    ("custom", "Custom interval"),
                ],
                default="monthly",
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name="upcomingexpense",
            name="custom_interval_days",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.RunPython(backfill_cadence, noop_reverse),
        migrations.AddConstraint(
            model_name="upcomingexpense",
            constraint=models.CheckConstraint(
                condition=~models.Q(cadence="custom") | models.Q(custom_interval_days__gt=0),
                name="upcoming_custom_requires_interval_days",
            ),
        ),
    ]

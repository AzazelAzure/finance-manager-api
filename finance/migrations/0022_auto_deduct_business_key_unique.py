"""HFM-AD-1: partial unique business key for auto-deducted bill+date per user.

Fail-loud audit before AddConstraint: existing duplicate groups must be
dispositioned out-of-band (no survivor merge/delete in this migration).
"""

from django.db import migrations, models
from django.db.models import Count


class MigrationError(Exception):
    """Abort migrate when duplicate auto-deduct business keys already exist."""


def audit_auto_deduct_duplicates(apps, schema_editor):
    Transaction = apps.get_model("finance", "Transaction")
    duplicate_groups = list(
        Transaction.objects.filter(auto_deducted=True)
        .exclude(bill__isnull=True)
        .exclude(bill="")
        .values("uid", "bill", "date")
        .annotate(row_count=Count("id"))
        .filter(row_count__gt=1)
    )
    if duplicate_groups:
        sample = duplicate_groups[:10]
        raise MigrationError(
            "Cannot add unique_auto_deduct_bill_date_per_user: found "
            f"{len(duplicate_groups)} duplicate auto-deduct group(s) matching "
            "(uid, bill, date) with auto_deducted=True and non-empty bill. "
            f"Sample keys: {sample}. Disposition duplicates before migrating; "
            "this migration does not delete or merge rows."
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0021_dashboard_layout"),
    ]

    operations = [
        migrations.RunPython(audit_auto_deduct_duplicates, noop_reverse),
        migrations.AddConstraint(
            model_name="transaction",
            constraint=models.UniqueConstraint(
                condition=models.Q(auto_deducted=True)
                & ~models.Q(bill__in=[None, ""]),
                fields=("uid", "bill", "date"),
                name="unique_auto_deduct_bill_date_per_user",
            ),
        ),
    ]

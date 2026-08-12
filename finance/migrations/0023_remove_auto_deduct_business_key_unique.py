"""HFM-AD-1 amend: drop partial unique index if present; keep ORM state clean.

Uses SeparateDatabaseAndState so greenfield (edited noop 0022 never added the
constraint to state or DB) and old-0022 cohort (physical index still present)
both migrate cleanly. Postgres/SQLite store conditional UniqueConstraint as a
partial unique index named like the constraint.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0022_auto_deduct_business_key_unique"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveConstraint(
                    model_name="transaction",
                    name="unique_auto_deduct_bill_date_per_user",
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql='DROP INDEX IF EXISTS "unique_auto_deduct_bill_date_per_user";',
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
        ),
    ]

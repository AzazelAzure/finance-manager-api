# F-001 balance history — day-end balance snapshots

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0013_upcomingexpense_bill_realism_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="BalanceSnapshot",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("uid", models.CharField(db_index=True, max_length=200)),
                ("source", models.CharField(max_length=50)),
                ("snapshot_date", models.DateField()),
                ("closing_balance", models.DecimalField(decimal_places=2, max_digits=15)),
                ("currency", models.CharField(default="USD", max_length=3)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-snapshot_date", "source"],
            },
        ),
        migrations.AddIndex(
            model_name="balancesnapshot",
            index=models.Index(
                fields=["uid", "snapshot_date"],
                name="balance_snap_uid_date_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="balancesnapshot",
            constraint=models.UniqueConstraint(
                fields=("uid", "source", "snapshot_date"),
                name="unique_balance_snapshot_per_source_day",
            ),
        ),
    ]

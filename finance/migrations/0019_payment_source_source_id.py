# Payment source linkage standardization (T01)

import uuid
from datetime import date

from django.db import migrations, models


def _generate_source_id(snapshot_date: date) -> str:
    return f"{snapshot_date}-{str(uuid.uuid4())[:8].upper()}"


def backfill_payment_source_ids(apps, schema_editor):
    PaymentSource = apps.get_model("finance", "PaymentSource")
    today = date.today()
    for ps in PaymentSource.objects.filter(source_id__isnull=True).iterator():
        ps.source_id = _generate_source_id(today)
        ps.save(update_fields=["source_id"])


def backfill_name_linkage_surfaces(apps, schema_editor):
    PaymentSource = apps.get_model("finance", "PaymentSource")
    Transaction = apps.get_model("finance", "Transaction")
    BalanceSnapshot = apps.get_model("finance", "BalanceSnapshot")
    AppProfile = apps.get_model("finance", "AppProfile")

    for uid in PaymentSource.objects.values_list("uid", flat=True).distinct():
        name_to_id = {
            str(row.source).lower(): row.source_id
            for row in PaymentSource.objects.filter(uid=uid)
        }

        for tx in Transaction.objects.filter(uid=uid).iterator():
            key = str(tx.source).lower()
            if key in name_to_id:
                tx.source = name_to_id[key]
                tx.save(update_fields=["source"])

        for snap in BalanceSnapshot.objects.filter(uid=uid).iterator():
            key = str(snap.source).lower()
            if key in name_to_id:
                snap.source = name_to_id[key]
                snap.save(update_fields=["source"])

        profile = AppProfile.objects.filter(user_id=uid).first()
        if profile and profile.spend_accounts:
            spend = profile.spend_accounts
            if isinstance(spend, list):
                converted = []
                for item in spend:
                    sid = name_to_id.get(str(item).lower())
                    converted.append(sid if sid else item)
                profile.spend_accounts = converted
                profile.save(update_fields=["spend_accounts"])


def backfill_savings_goal_source_char(apps, schema_editor):
    PaymentSource = apps.get_model("finance", "PaymentSource")
    SavingsGoal = apps.get_model("finance", "SavingsGoal")

    for goal in SavingsGoal.objects.select_related("source").iterator():
        fk = goal.source
        if fk is not None:
            goal.source_char = fk.source_id
            goal.save(update_fields=["source_char"])


def reverse_name_linkage_surfaces(apps, schema_editor):
    PaymentSource = apps.get_model("finance", "PaymentSource")
    Transaction = apps.get_model("finance", "Transaction")
    BalanceSnapshot = apps.get_model("finance", "BalanceSnapshot")
    AppProfile = apps.get_model("finance", "AppProfile")

    for uid in PaymentSource.objects.values_list("uid", flat=True).distinct():
        id_to_name = {
            row.source_id: row.source
            for row in PaymentSource.objects.filter(uid=uid)
        }

        for tx in Transaction.objects.filter(uid=uid).iterator():
            name = id_to_name.get(tx.source)
            if name is not None:
                tx.source = name
                tx.save(update_fields=["source"])

        for snap in BalanceSnapshot.objects.filter(uid=uid).iterator():
            name = id_to_name.get(snap.source)
            if name is not None:
                snap.source = name
                snap.save(update_fields=["source"])

        profile = AppProfile.objects.filter(user_id=uid).first()
        if profile and profile.spend_accounts:
            spend = profile.spend_accounts
            if isinstance(spend, list):
                converted = []
                for item in spend:
                    name = id_to_name.get(item)
                    converted.append(name if name else item)
                profile.spend_accounts = converted
                profile.save(update_fields=["spend_accounts"])


def reverse_savings_goal_fk(apps, schema_editor):
    PaymentSource = apps.get_model("finance", "PaymentSource")
    SavingsGoal = apps.get_model("finance", "SavingsGoal")

    for goal in SavingsGoal.objects.iterator():
        if goal.source:
            ps = PaymentSource.objects.filter(
                uid=str(goal.uid_id), source_id=goal.source
            ).first()
            if ps:
                goal.source_id = ps.pk
                goal.save(update_fields=["source_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0018_revoke_export_share_tokens"),
    ]

    operations = [
        migrations.AddField(
            model_name="paymentsource",
            name="source_id",
            field=models.CharField(
                blank=True, db_index=True, editable=False, max_length=20, null=True
            ),
        ),
        migrations.RunPython(backfill_payment_source_ids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="paymentsource",
            name="source_id",
            field=models.CharField(db_index=True, editable=False, max_length=20),
        ),
        migrations.AddConstraint(
            model_name="paymentsource",
            constraint=models.UniqueConstraint(
                fields=("source_id", "uid"),
                name="unique_source_id_per_user",
            ),
        ),
        migrations.RunPython(backfill_name_linkage_surfaces, reverse_name_linkage_surfaces),
        migrations.AlterField(
            model_name="transaction",
            name="source",
            field=models.CharField(max_length=20),
        ),
        migrations.AlterField(
            model_name="balancesnapshot",
            name="source",
            field=models.CharField(max_length=20),
        ),
        migrations.AddField(
            model_name="savingsgoal",
            name="source_char",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.RunPython(backfill_savings_goal_source_char, reverse_savings_goal_fk),
        migrations.RemoveField(
            model_name="savingsgoal",
            name="source",
        ),
        migrations.RenameField(
            model_name="savingsgoal",
            old_name="source_char",
            new_name="source",
        ),
    ]

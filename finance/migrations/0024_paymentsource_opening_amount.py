"""Add PaymentSource.opening_amount and backfill leftover so deploy does not jump balances."""

from decimal import Decimal

from django.db import migrations, models


def backfill_opening_amount(apps, schema_editor):
    PaymentSource = apps.get_model("finance", "PaymentSource")
    Transaction = apps.get_model("finance", "Transaction")
    from finance.logic.convert_currency import convert_currency

    for source in PaymentSource.objects.all().iterator():
        total = Decimal("0.00")
        for tx in Transaction.objects.filter(uid=source.uid, source=source.source_id):
            amount = Decimal(tx.amount or 0).quantize(Decimal("0.01"))
            if tx.currency != source.currency:
                amount = convert_currency(amount, tx.currency, source.currency).quantize(Decimal("0.01"))
            total += amount
        opening = (Decimal(source.amount or 0) - total).quantize(Decimal("0.01"))
        source.opening_amount = opening
        source.save(update_fields=["opening_amount"])


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0023_remove_auto_deduct_business_key_unique"),
    ]

    operations = [
        migrations.AddField(
            model_name="paymentsource",
            name="opening_amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=15),
        ),
        migrations.RunPython(backfill_opening_amount, noop_reverse),
    ]

"""F-009 T01: auto_deduct on UpcomingExpense, source link, auto_deducted on Transaction."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0019_payment_source_source_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="upcomingexpense",
            name="auto_deduct",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="upcomingexpense",
            name="source",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name="transaction",
            name="auto_deducted",
            field=models.BooleanField(default=False),
        ),
    ]

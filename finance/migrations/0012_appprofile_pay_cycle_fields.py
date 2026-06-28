from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0011_tos_acceptance_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="appprofile",
            name="pay_cycle_anchor_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="appprofile",
            name="pay_cycle_frequency",
            field=models.CharField(
                blank=True,
                choices=[
                    ("weekly", "Weekly"),
                    ("biweekly", "Biweekly"),
                    ("semimonthly", "Semi-monthly"),
                    ("monthly", "Monthly"),
                ],
                max_length=20,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="appprofile",
            name="sts_window_mode",
            field=models.CharField(
                choices=[
                    ("calendar_month", "Calendar month"),
                    ("pay_cycle", "Pay cycle"),
                ],
                default="calendar_month",
                max_length=20,
            ),
        ),
    ]

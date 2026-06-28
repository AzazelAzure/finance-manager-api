from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0012_appprofile_pay_cycle_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="upcomingexpense",
            name="bill_class",
            field=models.CharField(
                choices=[("rigid", "Rigid"), ("volatile", "Volatile")],
                default="rigid",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="upcomingexpense",
            name="cycle_residual_amount",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name="upcomingexpense",
            name="planned_partial_amount",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name="upcomingexpense",
            name="remainder_due_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddConstraint(
            model_name="upcomingexpense",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("planned_partial_amount__isnull", True),
                    ("planned_partial_amount__lte", models.F("amount")),
                    _connector="OR",
                ),
                name="upcoming_partial_lte_amount",
            ),
        ),
    ]

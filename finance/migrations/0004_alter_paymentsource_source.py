from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0003_alter_transaction_created_on"),
    ]

    operations = [
        migrations.AlterField(
            model_name="paymentsource",
            name="source",
            field=models.CharField(max_length=50),
        ),
    ]

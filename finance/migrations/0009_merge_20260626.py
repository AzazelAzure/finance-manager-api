# Merge parallel finance branches: 0004 (paymentsource) and 0005→0008 (F-012/F-013 chain)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0004_alter_paymentsource_source"),
        ("finance", "0008_supportticket"),
    ]

    operations = []

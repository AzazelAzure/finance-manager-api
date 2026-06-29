"""Clear outstanding F-010 export share tokens (feature disabled 2026-06-29)."""

from django.db import migrations


def clear_all_share_tokens(apps, schema_editor):
    ExportShareToken = apps.get_model("finance", "ExportShareToken")
    ExportShareToken.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0017_upcomingexpense_bill_cadence"),
    ]

    operations = [
        migrations.RunPython(clear_all_share_tokens, migrations.RunPython.noop),
    ]

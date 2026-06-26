# Compatibility migration for historical tag uniqueness cleanup.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0001_initial"),
    ]

    # 0001_initial in the committed migration graph no longer creates
    # unique_uuid_per_user. Keep this node as a no-op so later migration
    # dependencies can replay on fresh test and deploy databases.
    operations = []

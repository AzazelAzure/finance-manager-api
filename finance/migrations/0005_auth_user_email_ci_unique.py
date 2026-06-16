from django.db import migrations


def create_ci_email_unique_index(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        'CREATE UNIQUE INDEX IF NOT EXISTS "auth_user_email_lower_unique" '
        'ON "auth_user" ((LOWER("email")));'
    )


def drop_ci_email_unique_index(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute('DROP INDEX IF EXISTS "auth_user_email_lower_unique";')


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(create_ci_email_unique_index, drop_ci_email_unique_index),
    ]

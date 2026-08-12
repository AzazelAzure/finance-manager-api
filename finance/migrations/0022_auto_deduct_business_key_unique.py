"""HFM-AD-1 amend: neutralized fresh-apply path.

Supersedes the fail-loud duplicate audit and AddConstraint from the original
0022. Fresh installs must not fleet-block on historical auto-deduct duplicates.
Physical constraint removal for envs that applied the old 0022 is owned by 0023.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0021_dashboard_layout"),
    ]

    operations = []

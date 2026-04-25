import os

from django.core.management import call_command
from django.core.management.base import BaseCommand

from finance.management.commands._seed_fake_userbase import seed_fake_userbase
from finance.management.commands._setup_helpers import ensure_conversion_setup

class Command(BaseCommand):
    help = "Sets up schema/demo data by reusing prod setup and seeding fake users."

    def add_arguments(self, parser):
        parser.add_argument("--users", type=int, default=1000)
        parser.add_argument("--transactions-per-user", type=int, default=1000)
        parser.add_argument("--categories-per-user", type=int, default=10)
        parser.add_argument("--tags-per-user", type=int, default=10)
        parser.add_argument("--sources-per-user", type=int, default=10)
        parser.add_argument("--upcoming-expenses-per-user", type=int, default=10)
        parser.add_argument("--batch-size", type=int, default=2000)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--skip-conversion-download", action="store_true")
        parser.add_argument("--no-migrate", action="store_true")
        parser.add_argument("--no-static", action="store_true")
        parser.add_argument("--create-superuser", action="store_true")
        parser.add_argument("--superuser-username", default=os.getenv("DJANGO_SUPERUSER_USERNAME"))
        parser.add_argument("--superuser-email", default=os.getenv("DJANGO_SUPERUSER_EMAIL"))
        parser.add_argument("--superuser-password", default=os.getenv("DJANGO_SUPERUSER_PASSWORD"))

    def handle(self, *args, **options):
        self.stdout.write("Running prod_setup prerequisites...")
        call_command(
            "prod_setup",
            skip_conversion_download=options["skip_conversion_download"],
            no_migrate=options["no_migrate"],
            no_static=options["no_static"],
            create_superuser=options["create_superuser"],
            superuser_username=options.get("superuser_username"),
            superuser_email=options.get("superuser_email"),
            superuser_password=options.get("superuser_password"),
            verbosity=options.get("verbosity", 1),
        )

        supported_currencies = ensure_conversion_setup(
            skip_download=True,
            verbosity=options.get("verbosity", 1),
        )

        summary = seed_fake_userbase(
            users=options["users"],
            transactions_per_user=options["transactions_per_user"],
            categories_per_user=options["categories_per_user"],
            tags_per_user=options["tags_per_user"],
            sources_per_user=options["sources_per_user"],
            upcoming_expenses_per_user=options["upcoming_expenses_per_user"],
            dry_run=options["dry_run"],
            batch_size=max(1, options["batch_size"]),
            currencies=supported_currencies,
            stdout=self.stdout,
        )

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("Dry-run only. No data written."))
        self.stdout.write(
            self.style.SUCCESS(
                "schema_setup finished. "
                f"Users: {summary['users']}, tx/user: {summary['transactions_per_user']}, "
                f"estimated tx: {summary['estimated_transactions']}."
            )
        )
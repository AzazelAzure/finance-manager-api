import os

from django.core.management import call_command
from django.core.management.base import BaseCommand

from finance.management.commands._setup_helpers import ensure_conversion_setup, maybe_create_superuser

class Command(BaseCommand):
    help = "Sets up project runtime for production use."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-conversion-download",
            action="store_true",
            help="Skip update_conversion_file and validate existing archive only.",
        )
        parser.add_argument(
            "--no-migrate",
            action="store_true",
            help="Skip migrate step.",
        )
        parser.add_argument(
            "--no-static",
            action="store_true",
            help="Skip collectstatic step.",
        )
        parser.add_argument(
            "--create-superuser",
            action="store_true",
            help="Create a superuser from provided args/env vars.",
        )
        parser.add_argument("--superuser-username", default=os.getenv("DJANGO_SUPERUSER_USERNAME"))
        parser.add_argument("--superuser-email", default=os.getenv("DJANGO_SUPERUSER_EMAIL"))
        parser.add_argument("--superuser-password", default=os.getenv("DJANGO_SUPERUSER_PASSWORD"))

    def handle(self, *args, **options):
        supported_currencies = ensure_conversion_setup(
            skip_download=options["skip_conversion_download"],
            verbosity=options.get("verbosity", 1),
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Conversion setup validated ({len(supported_currencies)} currencies loaded)."
            )
        )

        if not options["no_migrate"]:
            self.stdout.write("Applying migrations...")
            call_command("migrate", verbosity=options.get("verbosity", 1))
            self.stdout.write(self.style.SUCCESS("Migrations complete."))
        else:
            self.stdout.write("Skipped migrations.")

        _, superuser_message = maybe_create_superuser(
            create_superuser=options["create_superuser"],
            username=options.get("superuser_username"),
            email=options.get("superuser_email"),
            password=options.get("superuser_password"),
        )
        self.stdout.write(superuser_message)

        if not options["no_static"]:
            self.stdout.write("Collecting static files...")
            call_command("collectstatic", interactive=False, verbosity=options.get("verbosity", 1))
            self.stdout.write(self.style.SUCCESS("Static files collected."))
        else:
            self.stdout.write("Skipped collectstatic.")

        self.stdout.write(self.style.SUCCESS("prod_setup completed successfully."))
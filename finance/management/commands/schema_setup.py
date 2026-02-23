# TODO: Actually make this work
import subprocess 
from django.core.management.base import BaseCommand

# This command will set up the project for schema views/documentation
# It will create a new virtual environment, install dependencies, and run migrations

class Command(BaseCommand):
    help = 'Sets up the project for schema views/documentation'

    def handle(self, *args, **options):
        # TODO: Flesh this out
            # Needs to use factories to generate dummy data.
        return
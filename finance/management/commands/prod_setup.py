# TODO: Actually make this work
import subprocess 
from django.core.management.base import BaseCommand
# This command will set up the project for production
# It will create a new virtual environment, install dependencies, and run migrations

class Command(BaseCommand):
    help = 'Sets up the project for production'

    def handle(self, *args, **options):
        # TODO: Flesh this out
        return
from django.apps import AppConfig
from django.core.management import call_command
from loguru import logger

class FinanceConfig(AppConfig):
    name = "finance"

    def ready(self):
        import finance.signals
        from .models import Currency
        from finance.management.commands.populate_currencies import Command
        if not Currency.objects.exists():
            logger.info("Currencies not found.  Populating...")
            try:
                call_command('populate_currencies')
                logger.info("Currencies populated")
            except Exception as e:
                logger.error(f"Error populating currencies: {e}")

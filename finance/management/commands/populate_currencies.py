from django.core.management.base import BaseCommand
import pycountry
from babel.numbers import get_currency_symbol
from finance.models import Currency 
from loguru import logger

class Command(BaseCommand):
    help = 'Populates the database with global ISO currencies'

    def handle(self, *args, **options):
        logger.info("Populating currencies")
        for curr in pycountry.currencies:
            code = curr.alpha_3
            name = curr.name
            
            try:
                # Use 'en_US' as a common locale for currency symbols
                symbol = get_currency_symbol(code, locale='en_US')
            except Exception as e: # Catch a more specific exception if possible, or log the error
                symbol = None 
                logger.warning(f"Could not get symbol for currency {code} ({name}): {e}")
                
            Currency.objects.get_or_create(
                code=code,
                defaults={'name': name, 'symbol': symbol}
            )
            
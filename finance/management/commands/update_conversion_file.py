import urllib.request
from django.core.management.base import BaseCommand
from django.conf import settings
from loguru import logger
from pathlib import Path

class Command(BaseCommand):
    help = 'Downloads the latest daily exchange rates for the currency_converter library'

    def handle(self, *args, **options):
        url = 'https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.zip'
        save_path = Path(settings.BASE_DIR) / 'finance' / 'data' / 'exchange_rates.zip'
        logger.info(f"Downloading exchange rates from {url} to {save_path}")
        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(url, save_path)
            logger.info(f"Downloaded exchange rates to {save_path}")
        except Exception as e:
            logger.error(f"Error downloading exchange rates: {e}")
            
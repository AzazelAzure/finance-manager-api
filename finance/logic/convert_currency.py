from currency_converter import CurrencyConverter
from decimal import Decimal
from django.conf import settings
import os

def convert_currency(amount, from_currency, to_currency):
    """
    Converts an amount from one currency to base_currency.
    This is a helper for the test_bulk_transactions test.
    """
    rate = os.path.join(settings.BASE_DIR, 'finance', 'data', 'exchange_rates.zip')
    if amount is None:
        return 0
    if from_currency == to_currency:
        return Decimal(amount)
    c = CurrencyConverter(rate, decimal=True)
    amount = c.convert(amount, from_currency, to_currency)
    return Decimal(amount)
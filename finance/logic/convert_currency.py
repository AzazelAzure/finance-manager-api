from decimal import Decimal

from django.conf import settings
from loguru import logger


def convert_currency(amount, from_currency, to_currency):
    """
    Converts an amount from one currency to another using ECB rate data.
    Uses the shared CURRENCY_CONVERTER from settings (loaded from
    settings.EXCHANGE_RATES_PATH). All supported currencies come from that
    same file; conversion failures are re-raised (no silent fallback).
    """
    if amount is None:
        return Decimal(0)
    if from_currency == to_currency:
        return Decimal(amount)
    converter = getattr(settings, "CURRENCY_CONVERTER", None)
    if converter is None:
        path = getattr(settings, "EXCHANGE_RATES_PATH", None)
        if path is None or not path.exists():
            raise FileNotFoundError(
                "Exchange rates file not found at settings.EXCHANGE_RATES_PATH; "
                "cannot convert currency. Ensure finance/data/exchange_rates.zip exists "
                "(e.g. run update_conversion_file management command)."
            )
        from currency_converter import CurrencyConverter
        converter = CurrencyConverter(
            str(path),
            decimal=True,
            fallback_on_wrong_date=True,
            fallback_on_missing_rate=True,
        )
    result = converter.convert(amount, from_currency, to_currency)
    return Decimal(result)
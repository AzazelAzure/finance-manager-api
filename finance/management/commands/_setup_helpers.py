import os

from currency_converter import CurrencyConverter
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError


def ensure_conversion_setup(skip_download: bool = False, verbosity: int = 1) -> list[str]:
    """Ensure exchange rates file is present and currencies are loaded."""
    if not skip_download:
        call_command("update_conversion_file", verbosity=verbosity)

    exchange_rates_path = settings.EXCHANGE_RATES_PATH
    if not exchange_rates_path.exists():
        raise CommandError(
            f"Missing exchange-rates archive at '{exchange_rates_path}'. "
            "Run update_conversion_file before setup."
        )

    try:
        converter = CurrencyConverter(
            str(exchange_rates_path),
            decimal=True,
            fallback_on_wrong_date=True,
            fallback_on_missing_rate=True,
        )
        supported = sorted(converter.currencies)
    except Exception as exc:  # pragma: no cover - defensive conversion parse guard
        raise CommandError(
            "Failed to parse exchange rates archive. "
            "Download may be corrupt; re-run update_conversion_file."
        ) from exc

    if not supported:
        raise CommandError(
            "SUPPORTED_CURRENCIES is empty after exchange-rates load. "
            "Re-run update_conversion_file and verify archive contents."
        )

    # Keep runtime settings in sync for commands executed in the same process.
    settings.CURRENCY_CONVERTER = converter
    settings.SUPPORTED_CURRENCIES = supported
    return supported


def maybe_create_superuser(
    *,
    create_superuser: bool,
    username: str | None,
    email: str | None,
    password: str | None,
) -> tuple[bool, str]:
    """Create a superuser when requested. Safe to re-run."""
    if not create_superuser:
        return False, "Superuser creation skipped."

    username = username or os.getenv("DJANGO_SUPERUSER_USERNAME")
    email = email or os.getenv("DJANGO_SUPERUSER_EMAIL")
    password = password or os.getenv("DJANGO_SUPERUSER_PASSWORD")

    if not username or not email or not password:
        raise CommandError(
            "Superuser creation requires username/email/password. "
            "Pass --superuser-username/--superuser-email/--superuser-password "
            "or set DJANGO_SUPERUSER_USERNAME/DJANGO_SUPERUSER_EMAIL/"
            "DJANGO_SUPERUSER_PASSWORD."
        )

    user_model = get_user_model()
    if user_model.objects.filter(username=username).exists():
        return False, f"Superuser '{username}' already exists."

    user_model.objects.create_superuser(
        username=username,
        email=email,
        password=password,
    )
    return True, f"Created superuser '{username}'."

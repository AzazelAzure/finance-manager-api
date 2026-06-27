"""Shared Terms of Service acceptance helpers.

Both registration paths (the authenticated-free ``POST /finance/user/`` clickwrap
endpoint and the public ``POST /api/auth/registration/`` dj-rest-auth endpoint)
must record ToS acceptance the same way: validate the version against the allowed
set and persist a server-set timestamp. The client-supplied timestamp is treated
only as proof of intent and is never stored.
"""
from django.utils import timezone

# Allowed Terms of Service versions. Update when a new ToS version ships.
ALLOWED_TOS_VERSIONS = frozenset({"1.0"})


def is_allowed_tos_version(value):
    """Return True if ``value`` is a currently accepted ToS version."""
    return value in ALLOWED_TOS_VERSIONS


def record_tos_acceptance(profile, version):
    """Persist ToS acceptance onto an AppProfile with a server-set timestamp.

    The timestamp is always set server-side (``timezone.now()``); a client-supplied
    acceptance timestamp is never trusted or stored.
    """
    profile.tos_version = version
    profile.tos_accepted_at = timezone.now()
    profile.save(update_fields=["tos_version", "tos_accepted_at"])

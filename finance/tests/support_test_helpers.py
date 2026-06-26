"""Test helpers for Celery-backed support notify (avoid live Redis in unit tests)."""

from unittest.mock import patch

from finance.tasks.notify import notify_operator


def sync_notify_delay(**kwargs):
    notify_operator.run(**kwargs)


def patch_support_notify_delay():
    return patch(
        "finance.views.support_views.notify_operator.delay",
        side_effect=sync_notify_delay,
    )

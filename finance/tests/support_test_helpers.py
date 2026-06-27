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


def patch_support_confirmation_delay():
    return patch("finance.views.support_views.send_user_support_confirmation.delay")


def patch_all_support_delays():
    """Patch operator notify (sync) and user confirmation (no-op)."""
    from unittest.mock import Mock

    confirm = patch("finance.views.support_views.send_user_support_confirmation.delay")
    confirm_mock = confirm.start()
    notify = patch_support_notify_delay()
    notify_patcher = notify.start()
    return notify_patcher, confirm, confirm_mock

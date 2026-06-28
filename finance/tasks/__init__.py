"""Celery task package for the finance app.

Importing the task submodules here ensures Celery's ``autodiscover_tasks`` (which
imports ``finance.tasks``) registers every task with the worker. Without these
imports the package is a namespace package and beat-scheduled tasks such as
``rollup_daily_usage`` / ``send_weekly_feature_requests_email`` are never
registered, so beat would dispatch tasks the worker discards as unregistered.
"""

from finance.tasks import analytics, balance_snapshots, notify, security_alerts, support_digest, usage_rollup  # noqa: F401

__all__ = ["analytics", "balance_snapshots", "notify", "security_alerts", "support_digest", "usage_rollup"]

"""Celery tasks for F-001 day-end balance snapshots."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from celery import shared_task
from loguru import logger

from finance.logic.balance_snapshots import persist_snapshots_for_date
from finance.models import AppProfile


@shared_task
def capture_balance_snapshots() -> str:
    """Persist yesterday's closing balances for all profiles (UTC calendar day)."""
    snapshot_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()
    total_rows = 0
    profiles = 0
    for profile in AppProfile.objects.all().iterator():
        uid = str(profile.user_id)
        written = persist_snapshots_for_date(uid, snapshot_date)
        total_rows += written
        profiles += 1
    logger.info(
        "capture_balance_snapshots date={} profiles={} rows={}",
        snapshot_date,
        profiles,
        total_rows,
    )
    return f"snapshots:{snapshot_date}:{profiles}:{total_rows}"

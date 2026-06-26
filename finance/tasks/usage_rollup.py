from datetime import datetime, timedelta

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from loguru import logger

from finance.models import AppProfile, DailyUsageSnapshot, OperatorAlertState
from finance.tasks.notify import notify_operator

User = get_user_model()


def _parse_thresholds() -> list[int]:
    raw = getattr(settings, "DAU_ALERT_THRESHOLDS", "10,50,100")
    if isinstance(raw, (list, tuple)):
        return [int(t) for t in raw]
    return [int(part.strip()) for part in str(raw).split(",") if part.strip()]


def _maybe_alert_dau_thresholds(dau_count: int, snapshot_date) -> None:
    now = timezone.now()
    for threshold in sorted(_parse_thresholds()):
        if dau_count < threshold:
            continue
        alert_key = f"dau_threshold_{threshold}"
        state = OperatorAlertState.objects.filter(alert_key=alert_key).first()
        if state and (now - state.last_sent_at) < timedelta(hours=24):
            continue
        notify_operator.delay(
            event_type="DAU_THRESHOLD_CROSSED",
            severity="info",
            user_ref="system",
            file_paths=[],
            notes=f"DAU {dau_count} on {snapshot_date} crossed threshold {threshold}",
        )
        OperatorAlertState.objects.update_or_create(
            alert_key=alert_key,
            defaults={"last_sent_at": now},
        )
        logger.info("dau_threshold_alert threshold={} dau={}", threshold, dau_count)


@shared_task
def rollup_daily_usage() -> str:
    """
    Idempotent daily rollup (previous UTC calendar day).
    Scheduled via Celery beat at UTC 00:05.
    """
    today = timezone.now().date()
    snapshot_date = today - timedelta(days=1)
    day_start = timezone.make_aware(datetime.combine(snapshot_date, datetime.min.time()))
    day_end = day_start + timedelta(days=1)
    month_start = day_end - timedelta(days=30)

    dau_count = User.objects.filter(
        last_login__gte=day_start,
        last_login__lt=day_end,
        is_active=True,
    ).count()
    mau_count = User.objects.filter(
        last_login__gte=month_start,
        last_login__lt=day_end,
        is_active=True,
    ).count()
    active_accounts = AppProfile.objects.count()

    DailyUsageSnapshot.objects.update_or_create(
        date=snapshot_date,
        defaults={
            "dau_count": dau_count,
            "mau_count": mau_count,
            "active_accounts": active_accounts,
        },
    )

    _maybe_alert_dau_thresholds(dau_count, snapshot_date)

    logger.info(
        "usage_rollup_complete date={} dau={} mau={} active_accounts={}",
        snapshot_date,
        dau_count,
        mau_count,
        active_accounts,
    )
    return f"rollup:{snapshot_date}:dau={dau_count}"

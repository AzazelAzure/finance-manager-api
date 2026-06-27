"""Security probe threshold alerts (celery-observability T04)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from celery import shared_task
from django.conf import settings
from django.core.cache import cache

from finance.tasks.notify import notify_operator
from finance.utils.observability_keys import parse_metric_key, parse_security_key
from finance.utils.observability_store import redis_get_int, redis_keys

logger = logging.getLogger(__name__)


def _thresholds() -> dict[str, int]:
    return getattr(
        settings,
        "SECURITY_ALERT_THRESHOLDS",
        {
            "auth_failure": 10,
            "invalid_endpoint": 20,
            "5xx_rate_pct": 5,
        },
    )


def _dedup_ttl() -> int:
    return getattr(settings, "SECURITY_ALERT_DEDUP_TTL", 7200)


def _fire_security_alert(*, notes: str, dedup_key: str, dedup_ttl: int) -> None:
    if cache.get(dedup_key):
        return
    notify_operator.delay(
        event_type="SECURITY_PROBE_DETECTED",
        severity="high",
        user_ref="system",
        file_paths=[],
        notes=notes,
    )
    cache.set(dedup_key, True, timeout=dedup_ttl)


def _check_5xx_rate(hour_str: str, threshold_pct: int, dedup_ttl: int) -> None:
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    keys = redis_keys(f"fm_metrics:{date_str}:*")
    total = 0
    errors = 0
    for key in keys:
        parts = parse_metric_key(key)
        if parts is None:
            continue
        count = redis_get_int(key)
        total += count
        if parts.response_class == "5xx":
            errors += count

    if total <= 0:
        return

    rate_pct = (errors / total) * 100
    if rate_pct < threshold_pct:
        return

    dedup_key = f"sec_alert_sent:5xx_rate:{date_str}"
    _fire_security_alert(
        notes=(
            f"5xx error rate {rate_pct:.1f}% exceeds threshold {threshold_pct}% "
            f"({errors}/{total} requests today)"
        ),
        dedup_key=dedup_key,
        dedup_ttl=min(dedup_ttl, 3600),
    )
    logger.warning(
        "Security alert fired: 5xx_rate rate=%.1f%% threshold=%d",
        rate_pct,
        threshold_pct,
    )


@shared_task
def check_security_thresholds() -> str:
    """Check fm_security:* counters and notify operator when thresholds are crossed."""
    thresholds = _thresholds()
    dedup_ttl = _dedup_ttl()
    hour_str = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H")
    alerts_fired = 0

    for event_type, threshold in (
        ("auth_failure", thresholds["auth_failure"]),
        ("invalid_endpoint", thresholds["invalid_endpoint"]),
    ):
        pattern = f"fm_security:{hour_str}:*:{event_type}"
        for key in redis_keys(pattern):
            count = redis_get_int(key)
            if count < threshold:
                continue
            parts = parse_security_key(key)
            if parts is None:
                continue
            dedup_key = f"sec_alert_sent:{event_type}:{parts.ip_hash}"
            if cache.get(dedup_key):
                continue
            _fire_security_alert(
                notes=(
                    f"{event_type} threshold crossed: {count} events from "
                    f"ip_hash={parts.ip_hash} in current hour"
                ),
                dedup_key=dedup_key,
                dedup_ttl=dedup_ttl,
            )
            alerts_fired += 1
            logger.warning(
                "Security alert fired: %s ip_hash=%s count=%d",
                event_type,
                parts.ip_hash,
                count,
            )

    _check_5xx_rate(hour_str, thresholds["5xx_rate_pct"], dedup_ttl)
    return f"checked:{hour_str}:alerts={alerts_fired}"

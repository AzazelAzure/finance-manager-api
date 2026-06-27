"""Celery analytics aggregation tasks (celery-observability T03)."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone

from celery import shared_task
from django.conf import settings

from finance.models import DailyUsageSnapshot
from finance.utils.observability_keys import parse_metric_key
from finance.utils.observability_store import (
    redis_delete,
    redis_get_int,
    redis_keys,
)

logger = logging.getLogger(__name__)


def _analytics_dir() -> str:
    return getattr(settings, "ANALYTICS_LOG_DIR", "/var/log/fm_api/analytics")


@shared_task
def rollup_metrics_hourly() -> str:
    """Read fm_metrics:* Redis keys, append to daily JSONL, consume keys."""
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    hour_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:00:00Z")
    pattern = f"fm_metrics:{date_str}:*"
    keys = redis_keys(pattern)
    if not keys:
        logger.info("rollup_metrics_hourly: no keys for %s", date_str)
        return f"noop:{date_str}"

    output_dir = _analytics_dir()
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"metrics_{date_str}.jsonl")

    lines_written = 0
    with open(output_path, "a", encoding="utf-8") as handle:
        for key in keys:
            parts = parse_metric_key(key)
            if parts is None:
                continue
            count = redis_get_int(key)
            if count <= 0:
                redis_delete(key)
                continue
            line = json.dumps(
                {
                    "ts": hour_str,
                    "endpoint": parts.endpoint,
                    "method": parts.method,
                    "response_class": parts.response_class,
                    "ua_class": parts.ua_class,
                    "count": count,
                }
            )
            handle.write(line + "\n")
            lines_written += 1
            redis_delete(key)

    logger.info("rollup_metrics_hourly: wrote %d lines to %s", lines_written, output_path)
    return f"rollup:{date_str}:{lines_written}"


@shared_task
def rollup_daily() -> str:
    """Aggregate yesterday's JSONL into daily summary JSON with F-014 DAU/MAU."""
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    metrics_path = os.path.join(_analytics_dir(), f"metrics_{yesterday}.jsonl")
    daily_path = os.path.join(_analytics_dir(), f"daily_{yesterday}.json")

    if os.path.exists(daily_path):
        logger.info("rollup_daily: %s already exists, skipping", daily_path)
        return f"skip:{yesterday}"

    totals = {
        "total_requests": 0,
        "by_ua_class": {},
        "by_response_class": {},
        "top_endpoints": {},
    }

    if os.path.exists(metrics_path):
        with open(metrics_path, encoding="utf-8") as handle:
            for line in handle:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                count = row.get("count", 0)
                totals["total_requests"] += count
                ua_class = row.get("ua_class", "unknown")
                totals["by_ua_class"][ua_class] = totals["by_ua_class"].get(ua_class, 0) + count
                response_class = row.get("response_class", "unknown")
                totals["by_response_class"][response_class] = (
                    totals["by_response_class"].get(response_class, 0) + count
                )
                endpoint = row.get("endpoint", "unknown")
                totals["top_endpoints"][endpoint] = (
                    totals["top_endpoints"].get(endpoint, 0) + count
                )

    top_endpoints = sorted(
        totals["top_endpoints"].items(),
        key=lambda item: item[1],
        reverse=True,
    )[:10]

    try:
        snapshot = DailyUsageSnapshot.objects.get(date=yesterday)
        dau, mau = snapshot.dau_count, snapshot.mau_count
    except DailyUsageSnapshot.DoesNotExist:
        dau, mau = 0, 0

    os.makedirs(_analytics_dir(), exist_ok=True)
    summary = {
        "date": yesterday,
        "total_requests": totals["total_requests"],
        "by_ua_class": totals["by_ua_class"],
        "by_response_class": totals["by_response_class"],
        "top_endpoints": [{"endpoint": endpoint, "count": count} for endpoint, count in top_endpoints],
        "dau": dau,
        "mau": mau,
    }

    with open(daily_path, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    logger.info("rollup_daily: wrote %s", daily_path)
    return f"daily:{yesterday}"


@shared_task
def rollup_weekly() -> str:
    """Aggregate the past 7 daily summaries into weekly JSON (Monday 00:10 UTC)."""
    today = datetime.now(timezone.utc).date()
    week_str = today.strftime("%Y-W%W")
    weekly_path = os.path.join(_analytics_dir(), f"weekly_{week_str}.json")

    if os.path.exists(weekly_path):
        logger.info("rollup_weekly: %s already exists, skipping", weekly_path)
        return f"skip:{week_str}"

    days = [(today - timedelta(days=offset)).strftime("%Y-%m-%d") for offset in range(1, 8)]
    daily_summaries = []
    for day in days:
        path = os.path.join(_analytics_dir(), f"daily_{day}.json")
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as handle:
            try:
                daily_summaries.append(json.load(handle))
            except json.JSONDecodeError:
                continue

    if not daily_summaries:
        logger.warning("rollup_weekly: no daily files found for week %s", week_str)
        return f"noop:{week_str}"

    total_requests = sum(item.get("total_requests", 0) for item in daily_summaries)
    avg_dau = sum(item.get("dau", 0) for item in daily_summaries) // len(daily_summaries)
    peak_dau = max(item.get("dau", 0) for item in daily_summaries)

    os.makedirs(_analytics_dir(), exist_ok=True)
    weekly = {
        "week": week_str,
        "days_covered": [item["date"] for item in daily_summaries],
        "total_requests": total_requests,
        "avg_dau": avg_dau,
        "peak_dau": peak_dau,
        "daily_summaries": daily_summaries,
    }

    with open(weekly_path, "w", encoding="utf-8") as handle:
        json.dump(weekly, handle, indent=2)

    logger.info("rollup_weekly: wrote %s", weekly_path)
    return f"weekly:{week_str}"

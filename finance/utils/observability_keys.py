"""Parse observability Redis keys (celery-observability T03/T04)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MetricKeyParts:
    date: str
    endpoint: str
    method: str
    response_class: str
    ua_class: str


@dataclass(frozen=True)
class SecurityKeyParts:
    hour: str
    ip_hash: str
    event_type: str


def parse_metric_key(key: str) -> MetricKeyParts | None:
    if not key.startswith("fm_metrics:"):
        return None
    remainder = key[len("fm_metrics:") :]
    date, _, tail = remainder.partition(":")
    if len(date) != 10 or not tail:
        return None
    parts = tail.rsplit(":", 3)
    if len(parts) != 4:
        return None
    endpoint, method, response_class, ua_class = parts
    return MetricKeyParts(
        date=date,
        endpoint=endpoint,
        method=method,
        response_class=response_class,
        ua_class=ua_class,
    )


def parse_security_key(key: str) -> SecurityKeyParts | None:
    if not key.startswith("fm_security:"):
        return None
    parts = key.split(":")
    if len(parts) != 4:
        return None
    _, hour, ip_hash, event_type = parts
    return SecurityKeyParts(hour=hour, ip_hash=ip_hash, event_type=event_type)

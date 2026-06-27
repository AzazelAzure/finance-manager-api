"""PII-safe helpers for request observability (celery-observability T02)."""

from __future__ import annotations

import hashlib
import re

from django.conf import settings

_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)


def normalize_endpoint(path: str) -> str:
    """Strip IDs from paths for metric key families."""
    normalized = _UUID_RE.sub("{uuid}", path or "")
    normalized = re.sub(r"/\d+(?=/|$)", "/{id}", normalized)
    if not normalized.endswith("/"):
        normalized = normalized.rstrip("/") + "/"
    return normalized


def hash_ip(ip: str) -> str:
    """Salted one-way IP hash for security correlation keys (16 hex chars)."""
    salt = getattr(settings, "LOG_IP_HASH_SALT", "") or "changeme"
    digest = hashlib.sha256(f"{salt}{ip or ''}".encode()).hexdigest()
    return digest[:16]


def classify_ua(ua: str) -> str:
    """Classify user agent at request time; raw string is never stored."""
    ua_lower = (ua or "").lower()
    if any(
        token in ua_lower
        for token in (
            "googlebot",
            "bingbot",
            "twitterbot",
            "facebookexternalhit",
            "applebot",
        )
    ):
        return "crawler"
    if any(
        token in ua_lower
        for token in (
            "curl",
            "python-requests",
            "go-http",
            "semrush",
            "ahrefs",
            "scrapy",
            "wget",
        )
    ):
        return "bot"
    if any(token in ua_lower for token in ("mozilla", "chrome", "safari", "firefox", "edge")):
        return "user"
    return "unknown"


def client_ip_from_request(request) -> str:
    """Prefer Cloudflare client IP when present."""
    return (
        request.META.get("HTTP_CF_CONNECTING_IP")
        or request.META.get("REMOTE_ADDR")
        or ""
    )


def response_class_for_status(status_code: int) -> str:
    return f"{max(status_code, 0) // 100}xx"

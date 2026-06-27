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
    """Resolve client IP for per-IP security correlation keys.

    Spoofable forwarded headers (``CF-Connecting-IP`` / ``X-Forwarded-For``) are
    only honored when ``OBSERVABILITY_TRUST_PROXY_IP`` is enabled, i.e. the API
    sits behind a trusted Cloudflare/Nginx proxy that overwrites them. Otherwise
    they are ignored and ``REMOTE_ADDR`` is used, so an attacker cannot rotate
    forged client IPs to keep auth-failure/probe counters below threshold.
    """
    remote_addr = request.META.get("REMOTE_ADDR") or ""
    if not getattr(settings, "OBSERVABILITY_TRUST_PROXY_IP", False):
        return remote_addr
    forwarded = request.META.get("HTTP_CF_CONNECTING_IP")
    if not forwarded:
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        forwarded = xff.split(",")[0].strip() if xff else ""
    return forwarded or remote_addr


def response_class_for_status(status_code: int) -> str:
    return f"{max(status_code, 0) // 100}xx"

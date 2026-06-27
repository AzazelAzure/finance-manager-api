"""PII-safe request observability middleware (celery-observability T02)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from django.urls import Resolver404, resolve

from finance.utils.observability_helpers import (
    classify_ua,
    client_ip_from_request,
    hash_ip,
    normalize_endpoint,
    response_class_for_status,
)
from finance.utils.observability_store import incr_with_expire

logger = logging.getLogger(__name__)

_METRICS_TTL = 172800  # 48h
_SECURITY_TTL = 7200  # 2h


class ObservabilityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            self._record(request, response)
        except Exception as exc:
            logger.error("ObservabilityMiddleware error: %s", exc)
        return response

    def _record(self, request, response) -> None:
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d")
        hour_str = now.strftime("%Y-%m-%d-%H")

        # Key metrics on the resolved URL *route pattern* (e.g.
        # "/finance/transactions/<str:tx_id>/") rather than the request path, and
        # collapse unresolved paths into a single "{unmatched}" bucket. This
        # bounds the fm_metrics:* keyspace to the number of routes so a caller
        # cannot spray unique path/param values (numeric, uuid, or arbitrary
        # strings on <str:...> routes) to grow the keyspace the rollup/alert jobs
        # enumerate with Redis KEYS.
        match = self._resolve(request)
        endpoint = self._endpoint_label(request, match)
        method = request.method or "UNKNOWN"
        response_class = response_class_for_status(response.status_code)
        ua_class = classify_ua(request.META.get("HTTP_USER_AGENT", ""))
        ip_hash = hash_ip(client_ip_from_request(request))

        metric_key = f"fm_metrics:{date_str}:{endpoint}:{method}:{response_class}:{ua_class}"
        incr_with_expire(metric_key, _METRICS_TTL)

        is_auth_failure = response.status_code in (401, 403)
        is_invalid_endpoint = response.status_code == 404 and match is None

        if is_auth_failure:
            sec_key = f"fm_security:{hour_str}:{ip_hash}:auth_failure"
            incr_with_expire(sec_key, _SECURITY_TTL)

        if is_invalid_endpoint:
            sec_key = f"fm_security:{hour_str}:{ip_hash}:invalid_endpoint"
            incr_with_expire(sec_key, _SECURITY_TTL)

    @staticmethod
    def _resolve(request):
        try:
            return resolve(request.path)
        except Resolver404:
            return None

    @staticmethod
    def _endpoint_label(request, match) -> str:
        if match is None:
            return "{unmatched}"
        route = (match.route or "").strip()
        if not route:
            return normalize_endpoint(request.path)
        return route if route.startswith("/") else "/" + route

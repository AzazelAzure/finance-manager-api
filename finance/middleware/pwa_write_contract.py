"""
D2 PWA contract: mutating /finance/* writes get optional Idempotency-Key replay,
Idempotency-Key is rejected off-allowlist paths, X-Client-Build is enforced when
CLIENT_BUILD_MIN_WRITE is set, and DELETE on missing transactions can return an
idempotent success shape when Idempotency-Key is present.

Allowlisted mutators include transactions, upcoming expenses, and lookup
endpoints (categories, tags, sources) used by the web offline outbox.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import timedelta
from typing import Callable

from django.conf import settings
from django.db import IntegrityError
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils import timezone
from rest_framework_simplejwt.authentication import JWTAuthentication

from finance.models import IdempotencyRecord

_MAX_IDEMPOTENCY_BODY = 32_768
_TX_DETAIL_PATH = re.compile(r"^/finance/transactions/[^/]+/?$")
_UPCOMING_DETAIL_PATH = re.compile(r"^/finance/upcoming_expenses/[^/]+/?$")
_CAT_DETAIL_PATH = re.compile(r"^/finance/categories/[^/]+/?$")
_TAG_ENDPOINT_PATH = re.compile(r"^/finance/tags/?$")
_SRC_DETAIL_PATH = re.compile(r"^/finance/sources/[^/]+/?$")


def _normalize_path(path: str) -> str:
    p = path.split("?", 1)[0]
    if not p.endswith("/"):
        p = f"{p}/"
    return p


def _is_finance_mutation(method: str, path: str) -> bool:
    if method.upper() not in ("POST", "PUT", "PATCH", "DELETE"):
        return False
    return path.startswith("/finance/")


def _method_path_allowlisted(method: str, path: str) -> bool:
    path_n = _normalize_path(path)
    m = method.upper()
    if m == "POST" and path_n == "/finance/transactions/":
        return True
    if m == "POST" and path_n == "/finance/upcoming_expenses/":
        return True
    if m in ("PATCH", "DELETE") and _TX_DETAIL_PATH.match(path_n):
        return True
    if m in ("PATCH", "PUT", "DELETE") and _UPCOMING_DETAIL_PATH.match(path_n):
        return True
    if m == "POST" and path_n == "/finance/categories/":
        return True
    if m in ("PATCH", "DELETE") and _CAT_DETAIL_PATH.match(path_n):
        return True
    if m in ("POST", "PATCH", "DELETE") and _TAG_ENDPOINT_PATH.match(path_n):
        return True
    if m == "POST" and path_n == "/finance/sources/":
        return True
    if m in ("PATCH", "DELETE") and _SRC_DETAIL_PATH.match(path_n):
        return True
    return False


def _hash_idempotency_key(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _parse_semverish_segments(value: str) -> tuple[int, ...]:
    """Best-effort semver tuple (1.2.3) for monotonic compare; non-digits end each segment."""
    parts: list[int] = []
    for segment in value.strip().split(".")[:6]:
        num = ""
        for ch in segment:
            if ch.isdigit():
                num += ch
            else:
                break
        parts.append(int(num) if num else 0)
    return tuple(parts) if parts else (0,)


def _client_build_at_or_above(client: str | None, minimum: str | None) -> bool:
    if not minimum:
        return True
    if client is None or not str(client).strip():
        return False
    c = str(client).strip()
    m = str(minimum).strip()
    if not m:
        return True
    tc = _parse_semverish_segments(c)
    tm = _parse_semverish_segments(m)
    if tc != (0,) or tm != (0,):
        return tc >= tm
    return c >= m


def _force_upgrade_response() -> JsonResponse:
    min_b = getattr(settings, "CLIENT_BUILD_MIN_WRITE", None)
    doc_url = getattr(settings, "CLIENT_UPGRADE_DOCUMENTATION_URL", "https://thehivemanager.com")
    payload = {
        "code": "CLIENT_BUILD_UNSUPPORTED",
        "message": "This app version is too old to sync. Please update.",
        "min_supported_build": min_b or "",
        "documentation_url": doc_url,
    }
    return JsonResponse(payload, status=409)


def _authenticate_user(request: HttpRequest):
    try:
        auth = JWTAuthentication().authenticate(request)
    except Exception:
        auth = None
    if auth:
        user, _token = auth
        return user
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        return user
    return None


def _capture_response_body(response: HttpResponse) -> tuple[int, str]:
    status = response.status_code
    body_bytes: bytes
    if hasattr(response, "data") and response.data is not None:
        from rest_framework.renderers import JSONRenderer

        body_bytes = JSONRenderer().render(response.data)
    else:
        if not response.get("Content-Type", "").startswith("application/json"):
            if hasattr(response, "render") and callable(response.render):
                response.render()
        body_bytes = response.content or b""
    text = body_bytes.decode("utf-8", errors="replace")
    if len(text) > _MAX_IDEMPOTENCY_BODY:
        return status, json.dumps(
            {"_truncated": True, "original_length": len(text)},
            separators=(",", ":"),
        )
    return status, text


def _replay_from_row(row: IdempotencyRecord) -> HttpResponse:
    return HttpResponse(
        row.response_body,
        status=row.status_code,
        content_type="application/json",
    )


class PwaWriteContractMiddleware:
    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        block = self._maybe_short_circuit_request(request)
        if block is not None:
            return block
        response = self.get_response(request)
        return self._post_process_response(request, response)

    def _maybe_short_circuit_request(self, request: HttpRequest) -> HttpResponse | None:
        if not _is_finance_mutation(request.method, request.path):
            return None

        user = _authenticate_user(request)
        if user is None or not getattr(user, "is_authenticated", False):
            request._pwa_idempotency_capture = None
            return None

        profile = getattr(user, "appprofile", None)
        if profile is None:
            request._pwa_idempotency_capture = None
            return None

        uid = str(profile.user_id)
        path_n = _normalize_path(request.path)

        min_build = getattr(settings, "CLIENT_BUILD_MIN_WRITE", None)
        if min_build:
            client_build = request.headers.get("X-Client-Build") or request.META.get("HTTP_X_CLIENT_BUILD")
            if not _client_build_at_or_above(client_build, min_build):
                return _force_upgrade_response()

        raw_key = (request.headers.get("Idempotency-Key") or request.META.get("HTTP_IDEMPOTENCY_KEY") or "").strip()
        if raw_key:
            if len(raw_key) > 128:
                return JsonResponse(
                    {"detail": "Idempotency-Key must be at most 128 characters."},
                    status=400,
                )
            if not _method_path_allowlisted(request.method, request.path):
                return JsonResponse(
                    {
                        "detail": "Idempotency-Key is not supported for this endpoint.",
                        "code": "IDEMPOTENCY_SCOPE",
                    },
                    status=400,
                )

            key_hash = _hash_idempotency_key(raw_key)
            window_days = int(getattr(settings, "IDEMPOTENCY_RETENTION_DAYS", 7) or 7)
            cutoff = timezone.now() - timedelta(days=window_days)
            row = (
                IdempotencyRecord.objects.filter(uid=uid, key_hash=key_hash, created_at__gte=cutoff)
                .order_by("-created_at")
                .first()
            )
            if row is not None:
                request._pwa_idempotency_capture = None
                return _replay_from_row(row)

            request._pwa_idempotency_capture = {
                "uid": uid,
                "key_hash": key_hash,
                "method": request.method.upper(),
                "path": path_n,
            }
        else:
            request._pwa_idempotency_capture = None

        return None

    def _post_process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        response = self._maybe_soft_delete_transaction(request, response)

        cap = getattr(request, "_pwa_idempotency_capture", None)
        if not cap:
            return response

        if not (200 <= response.status_code < 300):
            return response

        try:
            status_code, body_text = _capture_response_body(response)
        except Exception:
            return response

        try:
            IdempotencyRecord.objects.create(
                uid=cap["uid"],
                key_hash=cap["key_hash"],
                method=cap["method"],
                path=cap["path"],
                status_code=status_code,
                response_body=body_text,
            )
        except IntegrityError:
            row = IdempotencyRecord.objects.filter(uid=cap["uid"], key_hash=cap["key_hash"]).first()
            if row is not None:
                return _replay_from_row(row)

        return response

    def _maybe_soft_delete_transaction(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        if request.method.upper() != "DELETE":
            return response
        path_n = _normalize_path(request.path)
        if not _TX_DETAIL_PATH.match(path_n):
            return response
        raw_key = (request.headers.get("Idempotency-Key") or request.META.get("HTTP_IDEMPOTENCY_KEY") or "").strip()
        if not raw_key:
            return response
        if response.status_code != 400:
            return response

        blob = ""
        if hasattr(response, "data") and response.data is not None:
            try:
                from rest_framework.renderers import JSONRenderer

                blob = JSONRenderer().render(response.data).decode("utf-8", errors="replace")
            except Exception:
                blob = str(response.data)
        else:
            blob = (response.content or b"").decode("utf-8", errors="replace")
        if "does not exist" not in blob.lower():
            return response

        parts = [p for p in path_n.strip("/").split("/") if p]
        tx_id = parts[-1] if len(parts) >= 3 else ""
        payload = {"idempotent": True, "tx_id": tx_id}
        return JsonResponse(payload, status=200)

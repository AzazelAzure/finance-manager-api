"""Helpers for logging without exposing raw finance payloads or PII."""

from __future__ import annotations

from typing import Any


def payload_keys_preview(data: Any, *, max_keys: int = 24) -> str:
    """Return top-level keys for dict/list payloads; safe for warning logs."""
    if data is None:
        return "none"
    if isinstance(data, dict):
        keys = list(data.keys())[:max_keys]
        extra = len(data) - len(keys)
        suffix = f",...(+{extra})" if extra > 0 else ""
        return ",".join(str(k) for k in keys) + suffix
    if isinstance(data, list):
        return f"list(len={len(data)})"
    return type(data).__name__

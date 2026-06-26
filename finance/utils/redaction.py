"""Redact likely secrets from support intake free-text fields."""

from __future__ import annotations

import re

_BEARER = re.compile(r"Bearer\s+\S+", re.IGNORECASE)
_ASSIGNMENT = re.compile(
    r"(api[_-]?key|token|password|secret|authorization)\s*[:=]\s*\S+",
    re.IGNORECASE,
)


def redact_support_text(text: str) -> str:
    if not text:
        return text
    redacted = _BEARER.sub("Bearer [REDACTED]", text)
    return _ASSIGNMENT.sub(r"\1=[REDACTED]", redacted)

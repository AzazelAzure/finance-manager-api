"""[FM-NOTIFY] email envelope for operator notifications (F-014)."""

from __future__ import annotations

from datetime import datetime, timezone


def _iso_timestamp(when: datetime | None = None) -> str:
    ts = when or datetime.now(timezone.utc)
    return ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_notify_subject(event_type: str, severity: str, when: datetime | None = None) -> str:
    return f"[FM-NOTIFY] {event_type} | SEV:{severity} | {_iso_timestamp(when)}"


def build_notify_body(
    *,
    event_type: str,
    severity: str,
    user_ref: str,
    file_paths: list[str] | None = None,
    notes: str = "",
    when: datetime | None = None,
) -> str:
    paths = file_paths or []
    path_lines = "\n".join(f"  - {path}" for path in paths) if paths else "  - (none)"
    return (
        f"Event: {event_type}\n"
        f"Severity: {severity}\n"
        f"Timestamp: {_iso_timestamp(when)}\n"
        f"User-Ref: {user_ref}\n"
        f"Relevant-Files:\n{path_lines}\n"
        f"Notes: {notes or '(none)'}\n"
        "---\n"
        "Sent by finance_manager_api Celery notify worker.\n"
        "No PII. User-Ref is pseudonymous UUID only.\n"
    )

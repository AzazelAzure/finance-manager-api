from __future__ import annotations

import os

from django.conf import settings
from finance.utils.incident_extractor import extract_incident_logs


def diagnostic_log_candidates(user_id: str) -> list[str]:
    return [
        os.path.join(settings.BASE_DIR, "logs", "diagnostic", f"{user_id}.log"),
        os.path.join(settings.BASE_DIR, "finance", "logs", "diagnostic", f"{user_id}.log"),
    ]


def incident_log_locations() -> list[str]:
    return [
        os.path.join(settings.BASE_DIR, "logs", "incidents"),
        os.path.join(settings.BASE_DIR, "finance", "logs", "incidents"),
    ]


def bug_severity_label(severity: str | None) -> str:
    mapping = {"HIGH": "high", "MEDIUM": "medium", "LOW": "low"}
    return mapping.get(severity or "", "medium")


def dump_bug_incident(ticket, user_id: str) -> str | None:
    """
    Write incident_{ticket.id}.log with a 10-minute diagnostic window.
    Returns relative diagnostic_log_key or None.
    """
    log_path = next((path for path in diagnostic_log_candidates(user_id) if os.path.exists(path)), None)
    extracted_logs = extract_incident_logs(log_path, ticket.created_at) if log_path else []

    report_content = (
        f"Ticket ID: {ticket.id}\n"
        f"User ID: {ticket.uid}\n"
        f"Nature: {ticket.nature}\n"
        f"Severity: {ticket.severity}\n"
        f"Comment: {ticket.comment}\n"
        f"Created At: {ticket.created_at}\n\n"
        f"=== EXTRACTED 10-MINUTE LOG WINDOW ===\n"
    )
    if extracted_logs:
        report_content += "".join(extracted_logs)
    else:
        report_content += "[No logs found in the preceding 10-minute window]\n"

    incident_filename = f"incident_{ticket.id}.log"
    for loc in incident_log_locations():
        try:
            os.makedirs(loc, exist_ok=True)
            with open(os.path.join(loc, incident_filename), "w", encoding="utf-8") as handle:
                handle.write(report_content)
        except OSError:
            pass

    return f"logs/incidents/{incident_filename}"

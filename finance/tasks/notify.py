from __future__ import annotations

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from loguru import logger

from finance.utils.notify_format import (
    build_notify_body,
    build_notify_subject,
    get_notify_from_address,
)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def notify_operator(
    self,
    event_type: str,
    severity: str,
    user_ref: str,
    file_paths: list[str] | None = None,
    notes: str = "",
) -> str:
    """
    Async operator notification — UUID-only body, [FM-NOTIFY] subject prefix.
    Failures are logged; callers must not rely on this for request success.
    """
    recipient = getattr(settings, "OPERATOR_NOTIFY_EMAIL", "") or getattr(
        settings, "BUG_REPORT_TO_EMAIL", ""
    )
    if not recipient:
        logger.warning("notify_operator_skipped reason=no_recipient event_type={}", event_type)
        return "skipped:no_recipient"

    when = timezone.now()
    subject = build_notify_subject(event_type, severity, when)
    body = build_notify_body(
        event_type=event_type,
        severity=severity,
        user_ref=user_ref,
        file_paths=file_paths,
        notes=notes,
        when=when,
    )
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=get_notify_from_address(event_type),
            recipient_list=[recipient],
            fail_silently=False,
        )
    except Exception as exc:
        logger.exception(
            "notify_operator_failed event_type={} severity={} user_ref={}",
            event_type,
            severity,
            user_ref,
        )
        raise self.retry(exc=exc)

    logger.info(
        "notify_operator_sent event_type={} severity={} user_ref={}",
        event_type,
        severity,
        user_ref,
    )
    return f"sent:{event_type}"

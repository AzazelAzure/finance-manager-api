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


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def send_user_support_confirmation(self, user_id: int, ticket_type: str, nature: str) -> str:
    """Send a confirmation email to the user after a support ticket is created."""
    from django.contrib.auth import get_user_model
    from django.template.loader import render_to_string

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return "skipped:no_user"

    if not user.email:
        return "skipped:no_email"

    template_prefix = "bug_report_received" if ticket_type == "BUG" else "feature_request_received"
    context = {"username": user.username, "nature": nature}
    subject = render_to_string(f"email/{template_prefix}_subject.txt", context).strip()
    body = render_to_string(f"email/{template_prefix}_body.txt", context)

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email="support@thehivemanager.com",
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.exception(
            "send_user_support_confirmation_failed user_id={} ticket_type={}",
            user_id,
            ticket_type,
        )
        raise self.retry(exc=exc)

    logger.info(
        "send_user_support_confirmation_sent user_id={} ticket_type={}",
        user_id,
        ticket_type,
    )
    return f"sent:{ticket_type}"


def should_send_support_confirmation(user_uuid: str, ticket_type: str) -> bool:
    """Return True if no other ticket of this type exists in the last 5 minutes."""
    from datetime import timedelta

    from finance.models import SupportTicket

    cutoff = timezone.now() - timedelta(minutes=5)
    recent_count = SupportTicket.objects.filter(
        uid=user_uuid,
        report_type=ticket_type,
        created_at__gte=cutoff,
    ).count()
    return recent_count <= 1

from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from loguru import logger
from finance.models import SupportTicket

@shared_task
def send_weekly_feature_requests_email():
    """
    Weekly Celery task to gather all feature requests that have not been emailed yet,
    send a digest email, and mark them as emailed atomically.
    """
    recipient = getattr(settings, "SUPPORT_DIGEST_TO_EMAIL", None) or getattr(settings, "BUG_REPORT_TO_EMAIL", None) or ""
    if not recipient:
        logger.warning("support_digest_config_missing recipient email is not configured")
        return "No recipient email configured. Skipping digest email."

    cutoff = timezone.now() - timedelta(days=7)
    tickets_qs = SupportTicket.objects.filter(
        report_type=SupportTicket.ReportType.FEATURE,
        emailed=False,
        created_at__gte=cutoff,
    ).order_by("created_at")[:100]

    ticket_list = list(tickets_qs)
    ticket_count = len(ticket_list)

    subject = "[Finance Manager] Weekly Feature Requests Digest"
    
    if not ticket_list:
        text_content = "No feature requests were submitted in the last week."
        html_content = "<p>No feature requests were submitted in the last week.</p>"
    else:
        text_lines = ["Here is the summary of feature requests submitted:\n"]
        html_lines = [
            "<p>Here is the summary of feature requests submitted:</p>",
            "<table border='1' cellpadding='5' style='border-collapse: collapse;'>",
            "<thead><tr><th>Date</th><th>User ID</th><th>Subject</th><th>Description</th></tr></thead>",
            "<tbody>"
        ]

        for ticket in ticket_list:
            formatted_date = ticket.created_at.strftime("%Y-%m-%d %H:%M:%S")
            text_lines.append(
                f"- Date: {formatted_date}\n"
                f"  User ID: {ticket.uid}\n"
                f"  Subject: {ticket.nature}\n"
                f"  Description: {ticket.comment}\n"
            )
            html_lines.append(
                f"<tr>"
                f"<td>{formatted_date}</td>"
                f"<td>{ticket.uid}</td>"
                f"<td>{ticket.nature}</td>"
                f"<td>{ticket.comment}</td>"
                f"</tr>"
            )

        text_content = "\n".join(text_lines)
        html_lines.append("</tbody></table>")
        html_content = "\n".join(html_lines)

    # Send the email
    send_mail(
        subject=subject,
        message=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient],
        html_message=html_content,
        fail_silently=False,
    )
    
    if ticket_list:
        with transaction.atomic():
            ticket_ids = [ticket.id for ticket in ticket_list]
            SupportTicket.objects.filter(id__in=ticket_ids).update(emailed=True)
    
    logger.info(
        "support_digest_sent count={} recipient={}",
        ticket_count,
        recipient
    )
    return f"Digest email sent to {recipient} with {ticket_count} feature requests."
